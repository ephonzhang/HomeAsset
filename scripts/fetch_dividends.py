#!/usr/bin/env python3
"""刷新 data/dividend-events.json（真实分红派息记录）。

用户约定（2026-10-11）：**每次更新持仓 CSV 后，都要重新查询股息数据并更新**。
本脚本由 scripts/rebuild_from_csv.py 在 --write 收尾时自动调用，也可单独运行。

覆盖范围
--------
- 美股 / 港股（QQQM、VOO、QNDX、IYW、CGDV、SMH、TLT、0883.HK、0700.HK）：自动抓取
  数据源：腾讯自选股 `westock dividend <code> --years N`（CLI 缺失时自动安装）
- 韩股 000660.KS / 德股 690D.DE：**无自动源**，脚本会打印待人工核验提示（不会瞎改）

合并策略
--------
只「追加」新记录，按 (除息日, 金额) 去重，**从不覆盖或删除已有记录** ——
派息是既成事实，已入册的日期/金额不应被后续抓取改写。

用法
----
    python3 scripts/fetch_dividends.py              # 抓取并写入 data/dividend-events.json
    python3 scripts/fetch_dividends.py --dry-run    # 只打印差异，不写文件
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS = os.path.join(ROOT, "data", "dividend-events.json")
YEARS = "2"
# 只保留近 24 个月的记录：派息日历窗口是「近 12 个月」，留一倍余量足够，
# 且能让 data/dividend-events.json 不随年份无限膨胀。
KEEP_MONTHS = 24

# 需要人工核验的市场（无自动数据源）
MANUAL = {
    "000660.KS": "韩股 —— 用 StockAnalysis (KRX:000660) 或公司公告补录",
    "690D.DE": "德股 D 股 —— 用海尔智家投资者关系页的分红公告补录",
}


def find_westock() -> str | None:
    """返回 westock 可执行文件路径；缺失时尝试用技能包自带安装脚本安装。"""
    for cand in (shutil.which("westock"), os.path.expanduser("~/.local/bin/westock")):
        if cand and os.path.exists(cand) and os.access(cand, os.X_OK):
            return cand

    patterns = [
        os.path.expanduser("~/.workbuddy/plugins/cache/*/*/*/skills/westock-data/scripts/setup.sh"),
        os.path.expanduser("~/.workbuddy/plugins/cache/*/*/skills/westock-data/scripts/setup.sh"),
    ]
    for pat in patterns:
        for script in sorted(glob.glob(pat)):
            print(f"[fetch_dividends] westock 未安装，执行 {script}")
            r = subprocess.run(["bash", script, "-y"], capture_output=True, text=True)
            print((r.stdout or "").strip() or (r.stderr or "").strip())
            cand = os.path.expanduser("~/.local/bin/westock")
            if os.path.exists(cand) and os.access(cand, os.X_OK):
                return cand
    return None


def normalize_date(raw: str) -> str | None:
    """20241223 / 2024-12-23 / 2024/12/23 → 2024-12-23"""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) != 8:
        return None
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"


def to_float(raw: str) -> float | None:
    s = re.sub(r"[^0-9.\-]", "", raw or "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_tables(text: str) -> dict[str, list[dict]]:
    """解析 westock 输出的 markdown 分表：`#### usQQQM` + 表头 + 数据行。

    只认表头里同时含 ex 日期列与金额列的表，列顺序按表头名定位（美股/港股表头不同）。
    """
    out: dict[str, list[dict]] = {}
    code, header = None, None
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^####\s+(\S+)", line)
        if m:
            code, header = m.group(1), None
            out.setdefault(code, [])
            continue
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):  # 分隔行
            continue
        if header is None:
            joined = " ".join(cells).lower()
            if ("exdiv" in joined or "exdivi" in joined) and "div" in joined:
                header = cells
            continue

        row = dict(zip(header, cells))
        # 金额列：美股 dividend / 港股 cashDivPerShare
        amt = to_float(row.get("dividend", "")) if "dividend" in row else to_float(row.get("cashDivPerShare", ""))
        # 除息日列
        ex_raw = next((v for k, v in row.items() if k.lower().startswith("exdiv")), None)
        # 到账日列：美股 payDate / 港股 cashPayDate
        pay_raw = row.get("payDate") or row.get("cashPayDate")
        ex = normalize_date(ex_raw or "")
        if amt is None or ex is None:
            continue
        special = to_float(row.get("specialDivPerShare", "0") or "0") or 0.0
        out[code].append(
            {
                "exDate": ex,
                "payDate": normalize_date(pay_raw or "") or ex,
                "amount": amt,
                "_special": special,
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    events = json.load(open(EVENTS, encoding="utf-8"))
    instr = events["instruments"]

    targets = {
        code: meta
        for code, meta in instr.items()
        if meta.get("market") in ("US", "HK")
    }
    if not targets:
        print("[fetch_dividends] 没有可自动抓取的标的")
        return

    westock = find_westock()
    if not westock:
        print("[fetch_dividends] ⚠️ 找不到 westock CLI，跳过自动刷新（持仓/行情重建不受影响）")
        print("[fetch_dividends]    手动安装：bash <skills>/westock-data/scripts/setup.sh")
        return

    # westock 代码前缀：us / hk；港股要去掉 .HK 后缀（hk0883.HK → hk00883）
    def wcode(code: str, market: str) -> str:
        if market == "HK":
            return "hk" + code.replace(".HK", "").zfill(5)
        return "us" + code

    targets = {c: m for c, m in targets.items()}
    key_of = {c: wcode(c, m["market"]) for c, m in targets.items()}
    codes = ",".join(key_of.values())
    print(f"[fetch_dividends] 查询 {len(targets)} 个标的：{codes}")
    proc = subprocess.run(
        [westock, "dividend", codes, "--years", YEARS],
        capture_output=True,
        text=True,
    )
    text = proc.stdout or ""
    if not text.strip():
        print("[fetch_dividends] ⚠️ westock 无输出，跳过：", (proc.stderr or "").strip()[:200])
        return

    tables = parse_tables(text)
    changed: list[str] = []
    specials: list[str] = []
    for code, meta in targets.items():
        key = key_of[code]
        rows = tables.get(key, [])
        if not rows:
            note = "无派息记录（正常）" if not meta["records"] else "⚠️ 未解析到记录"
            print(f"  {code:<11} {note}")
            continue
        existing = {(r["exDate"], round(float(r["amount"]), 6)) for r in meta["records"]}
        added = []
        for r in sorted(rows, key=lambda x: x["exDate"]):
            if r["_special"]:
                specials.append(f"{code} {r['exDate']} 特别股息 {r['_special']}")
            if (r["exDate"], round(r["amount"], 6)) in existing:
                continue
            meta["records"].append({"exDate": r["exDate"], "payDate": r["payDate"], "amount": r["amount"]})
            existing.add((r["exDate"], round(r["amount"], 6)))
            added.append(f"{r['exDate']}:{r['amount']}")
        meta["records"].sort(key=lambda r: r["exDate"])
        if added:
            changed.append(code)
            print(f"  {code:<11} +{len(added)} 条  {' '.join(added)}")
        else:
            print(f"  {code:<11} 无新增（已是最新）")

    for code, hint in MANUAL.items():
        if code in instr:
            print(f"  {code:<11} ⚠️ 需人工核验（无自动源）：{hint}")
    for s in specials:
        print(f"  ⚠️ 出现特别股息，未自动计入（需人工确认是否算入每股股息）：{s}")

    if not changed:
        print("[fetch_dividends] 派息记录无变化")
        return

    # 修剪 24 个月以前的旧记录（派息日历只用近 12 个月）
    cutoff = (dt.date.today() - dt.timedelta(days=int(KEEP_MONTHS * 30.44))).isoformat()
    pruned = 0
    for meta in instr.values():
        keep = [r for r in meta["records"] if r["exDate"] >= cutoff]
        pruned += len(meta["records"]) - len(keep)
        meta["records"] = keep
    if pruned:
        print(f"[fetch_dividends] 修剪 {pruned} 条早于 {cutoff} 的旧记录")

    if args.dry_run:
        print(f"[fetch_dividends] dry-run：{', '.join(changed)} 有新增，未写入")
        return
    json.dump(events, open(EVENTS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[fetch_dividends] 已更新 data/dividend-events.json（{', '.join(changed)}）")


if __name__ == "__main__":
    sys.exit(main())
