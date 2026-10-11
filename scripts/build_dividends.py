#!/usr/bin/env python3
"""由真实派息记录生成派息日历，并可同步刷新总表的股息口径。

输入
----
1. data/dividend-events.json   各标的真实分红派息原始记录（除息日/到账日/每股金额，原生币种）
2. public/data/portfolio.json  持仓头寸、适用股息税率、官方数据来源
3. public/data/daily-holdings.json  汇率序列（取快照日当日值）

输出
----
1. public/data/dividends.json  派息日历数据（近 12 个月、按除息月份归集、人民币口径）
2. （--write-portfolio 时）就地更新 portfolio.json 的股息各列与合计行

窗口口径
--------
以快照日 asOf 为终点，向前取 12 个月：ex-date ∈ (asOf - 1 年, asOf]。
与「过去 12 个月每股已派发股息」列完全同口径 —— 因此日历 12 个月合计
必然等于总表的「税后到手股息（人民币）」。

金额口径
--------
股数 × 每股金额 × 快照日汇率 × (1 − 股息税率)，
汇率统一用快照日（而非各除息日当日）汇率，保证与总表逐分对上。

用法
----
    python3 scripts/build_dividends.py            # 只生成 dividends.json
    python3 scripts/build_dividends.py --write-portfolio   # 同时刷新 portfolio.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS = os.path.join(ROOT, "data", "dividend-events.json")
PORTFOLIO = os.path.join(ROOT, "public", "data", "portfolio.json")
DAILY = os.path.join(ROOT, "public", "data", "daily-holdings.json")
OUT = os.path.join(ROOT, "public", "data", "dividends.json")

CCY_LABEL = {"USD": "美元", "HKD": "港元", "EUR": "欧元", "KRW": "韩元"}


def shift_year(d: str, years: int = -1) -> str:
    """ISO 日期按年平移；2/29 落到 2/28。"""
    y, m, day = (int(x) for x in d.split("-"))
    try:
        return dt.date(y + years, m, day).isoformat()
    except ValueError:
        return dt.date(y + years, m, 28).isoformat()


def fmt_money(v: float) -> str:
    return f"{v:,.2f}"


def fmt_dps(v: float) -> str:
    """每股股息文本：整数不带小数，其余至少两位、去掉多余的 0。"""
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    s = f"{v:.6f}".rstrip("0")
    intpart, _, dec = s.partition(".")
    while len(dec) < 2:
        dec += "0"
    return f"{intpart}.{dec}"


def parse_shares(position: str) -> float:
    m = re.search(r"([\d,]+(?:\.\d+)?)", position or "")
    return float(m.group(1).replace(",", "")) if m else 0.0


def fx_on(series: dict[str, float], as_of: str) -> float:
    """取 asOf 当日汇率；无当日则取最近的不晚于 asOf 的交易日。"""
    if as_of in series:
        return series[as_of]
    earlier = [d for d in series if d <= as_of]
    if not earlier:
        raise SystemExit(f"汇率序列里没有 <= {as_of} 的取值")
    return series[max(earlier)]


def alloc_cents(values: list[float], total_cents: int) -> list[int]:
    """最大余数法把 total_cents 分到各项（单位：分），保证求和精确等于 total_cents。"""
    s = sum(values)
    if s <= 0 or total_cents <= 0:
        return [0] * len(values)
    raw = [v / s * total_cents for v in values]
    base = [int(r) for r in raw]
    diff = int(total_cents) - sum(base)
    if diff:
        order = sorted(range(len(raw)), key=lambda i: raw[i] - base[i], reverse=True)
        for i in order[:diff]:
            base[i] += 1
    return base


def largest_remainder(values: list[float], total_pct: float = 100.0) -> list[float]:
    """最大余数法：把合计百分比分摊到各项，保证求和精确等于 total_pct（保留两位）。"""
    s = sum(values)
    if s <= 0:
        return [0.0] * len(values)
    raw = [v / s * total_pct for v in values]
    scaled = [round(r * 100) for r in raw]
    diff = round(total_pct * 100) - sum(scaled)
    if diff:
        order = sorted(range(len(raw)), key=lambda i: (raw[i] * 100 - scaled[i]), reverse=diff > 0)
        for i in order[: abs(diff)]:
            scaled[i] += 1 if diff > 0 else -1
    return [x / 100 for x in scaled]


def write_csv(rows: list[dict]) -> None:
    """把 portfolio.json 的行写回 portfolio.csv（前端缺 JSON 时的兜底数据源），保持两者一致。"""
    import csv

    path = os.path.join(ROOT, "public", "data", "portfolio.csv")
    cols = list(rows[0].keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-portfolio", action="store_true", help="同时就地刷新 portfolio.json 的股息列")
    args = ap.parse_args()

    events = json.load(open(EVENTS, encoding="utf-8"))
    pf = json.load(open(PORTFOLIO, encoding="utf-8"))
    daily = json.load(open(DAILY, encoding="utf-8"))

    as_of = pf["date"]
    window_start = shift_year(as_of, -1)
    fx_series = daily["fx"]
    fx = {c: fx_on(series, as_of) for c, series in fx_series.items()}

    rows = dict(pf["rows"][0].items())  # 仅用于保留列顺序
    del rows
    order = [r["标的代码"] for r in pf["rows"]]

    # ---------- 第一遍：按未舍入的精确值累计（标的级 + 月份级） ----------
    entries: list[dict] = []
    for row in pf["rows"]:
        if row.get("序号") == "合计":
            continue
        code = row["标的代码"]
        meta = events["instruments"].get(code)
        shares = parse_shares(row["持仓头寸"])
        tax_rate = float(str(row["适用股息税率"]).replace("%", "") or 0) / 100.0
        ccy = (meta or {}).get("currency", "USD")
        rate = fx.get(ccy, 1.0)
        for rec in (meta or {}).get("records", []):
            if not (window_start < rec["exDate"] <= as_of):
                continue
            gross = shares * rec["amount"] * rate
            entries.append(
                {
                    "code": code,
                    "exDate": rec["exDate"],
                    "payDate": rec["payDate"],
                    "perShare": rec["amount"],
                    "currency": ccy,
                    "month": int(rec["exDate"][5:7]),
                    "grossExact": gross,
                    "taxExact": gross * tax_rate,
                }
            )
    entries.sort(key=lambda e: (e["exDate"], e["code"]))

    total_gross = round(sum(e["grossExact"] for e in entries), 2)
    total_tax = round(sum(e["taxExact"] for e in entries), 2)
    total_net = round(total_gross - total_tax, 2)

    # ---------- 第二遍：用最大余数法把「分」分摊下去，保证各级求和精确等于合计 ----------
    codes: list[str] = []
    gross_by_code: dict[str, float] = {}
    tax_by_code: dict[str, float] = {}
    for e in entries:
        if e["code"] not in gross_by_code:
            codes.append(e["code"])
            gross_by_code[e["code"]] = 0.0
            tax_by_code[e["code"]] = 0.0
        gross_by_code[e["code"]] += e["grossExact"]
        tax_by_code[e["code"]] += e["taxExact"]

    gross_cents = alloc_cents([gross_by_code[c] for c in codes], round(total_gross * 100))
    tax_cents = alloc_cents([tax_by_code[c] for c in codes], round(total_tax * 100))
    inst_gross = {c: gross_cents[i] / 100 for i, c in enumerate(codes)}
    inst_tax = {c: tax_cents[i] / 100 for i, c in enumerate(codes)}

    month_gross_exact = {m: sum(e["grossExact"] for e in entries if e["month"] == m) for m in range(1, 13)}
    month_tax_exact = {m: sum(e["taxExact"] for e in entries if e["month"] == m) for m in range(1, 13)}
    mg_cents = alloc_cents([month_gross_exact[m] for m in range(1, 13)], round(total_gross * 100))
    mt_cents = alloc_cents([month_tax_exact[m] for m in range(1, 13)], round(total_tax * 100))

    # ---------- 组装 ----------
    row_by_code = {r["标的代码"]: r for r in pf["rows"] if r.get("序号") != "合计"}
    end_year, end_month = int(as_of[:4]), int(as_of[5:7])
    month_year = {m: (end_year if m <= end_month else end_year - 1) for m in range(1, 13)}

    instruments = []
    for code in codes:
        row = row_by_code[code]
        meta = events["instruments"].get(code, {})
        ev = [e for e in entries if e["code"] == code]
        rate = fx.get(meta.get("currency", "USD"), 1.0)
        tax_rate = float(str(row["适用股息税率"]).replace("%", "") or 0) / 100.0
        dps = sum(e["perShare"] for e in ev)
        instruments.append(
            {
                "code": code,
                "currency": meta.get("currency", "USD"),
                "shares": parse_shares(row["持仓头寸"]),
                "taxRate": tax_rate,
                "periods": len(ev),
                "perShareTotal": round(dps, 8),
                "gross": inst_gross[code],
                "tax": inst_tax[code],
                "net": round(inst_gross[code] - inst_tax[code], 2),
                "source": meta.get("source", ""),
                "events": [
                    {
                        "code": code,
                        "exDate": e["exDate"],
                        "payDate": e["payDate"],
                        "perShare": e["perShare"],
                        "currency": e["currency"],
                        "gross": round(e["grossExact"], 2),
                        "tax": round(e["taxExact"], 2),
                        "net": round(e["grossExact"] - e["taxExact"], 2),
                    }
                    for e in ev
                ],
            }
        )
    # 无派息标的也要出现在标的清单里（前端可能用到）
    for row in pf["rows"]:
        if row.get("序号") == "合计" or row["标的代码"] in codes:
            continue
        instruments.append(
            {
                "code": row["标的代码"],
                "currency": events["instruments"].get(row["标的代码"], {}).get("currency", "USD"),
                "shares": parse_shares(row["持仓头寸"]),
                "taxRate": float(str(row["适用股息税率"]).replace("%", "") or 0) / 100.0,
                "periods": 0,
                "perShareTotal": 0,
                "gross": 0.0,
                "tax": 0.0,
                "net": 0.0,
                "source": events["instruments"].get(row["标的代码"], {}).get("source", ""),
                "events": [],
            }
        )

    months = [
        {
            "month": m,
            "year": str(month_year[m]),
            "gross": mg_cents[m - 1] / 100,
            "tax": mt_cents[m - 1] / 100,
            "net": round((mg_cents[m - 1] - mt_cents[m - 1]) / 100, 2),
            "items": [
                {
                    "code": e["code"],
                    "exDate": e["exDate"],
                    "payDate": e["payDate"],
                    "perShare": e["perShare"],
                    "currency": e["currency"],
                    "gross": round(e["grossExact"], 2),
                    "tax": round(e["taxExact"], 2),
                    "net": round(e["grossExact"] - e["taxExact"], 2),
                }
                for e in entries
                if e["month"] == m
            ],
        }
        for m in range(1, 13)
    ]

    payload = {
        "generatedAt": dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "asOf": as_of,
        "window": {"startExclusive": window_start, "endInclusive": as_of},
        "basis": "按除息日归月（现金到账日见明细）；金额 = 股数 × 每股分红 × 快照日汇率 × (1 − 股息税率)",
        "fx": fx,
        "totals": {"gross": total_gross, "tax": total_tax, "net": total_net},
        "instruments": instruments,
        "months": months,
    }
    json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"asOf={as_of}  窗口=({window_start}, {as_of}]  汇率={fx}")
    print(f"{'标的':<11}{'期数':>4}{'每股合计':>12}{'税前':>14}{'税后':>14}")
    for i in instruments:
        print(f"{i['code']:<11}{i['periods']:>4}{fmt_dps(i['perShareTotal']):>12}{fmt_money(i['gross']):>14}{fmt_money(i['net']):>14}")
    print(f"{'合计':<11}{'':>4}{'':>12}{fmt_money(total_gross):>14}{fmt_money(total_net):>14}")
    nonzero = [m for m in months if m["net"] > 0]
    print("有派息月份:", ", ".join(f"{m['month']}月({m['year']})" for m in nonzero))
    print("零派息月份:", ", ".join(f"{m['month']}月" for m in months if m["net"] <= 0) or "无")

    if args.write_portfolio:
        net_pct = largest_remainder([i["net"] for i in instruments])
        by_code = {i["code"]: i for i in instruments}
        pct_by_code = {i["code"]: net_pct[k] for k, i in enumerate(instruments)}
        idx = 0
        idx = 0
        for row in pf["rows"]:
            if row.get("序号") == "合计":
                row["税前总股息（人民币）"] = fmt_money(total_gross)
                row["应缴股息税（人民币）"] = fmt_money(total_tax)
                row["税后到手股息（人民币）"] = fmt_money(total_net)
                row["税后股息贡献占比"] = "100.00%"
                continue
            it = by_code[row["标的代码"]]
            ccy = it["currency"]
            row["过去12个月每股已派发股息（原生币种）"] = (
                f"0 {ccy}" if it["periods"] == 0 else f"{fmt_dps(it['perShareTotal'])} {ccy}"
            )
            row["税前总股息（人民币）"] = fmt_money(it["gross"])
            row["应缴股息税（人民币）"] = fmt_money(it["tax"])
            row["税后到手股息（人民币）"] = fmt_money(it["net"])
            row["税后股息贡献占比"] = f"{pct_by_code[row['标的代码']]:.2f}%"
            idx += 1
            if row["标的代码"] in ("BITB", "BYTE"):
                pass  # 无分红标的的来源说明保持原样
            else:
                prefix = (row.get("官方数据来源") or "").split(" / ")[0].strip()
                desc = (
                    "近12个月无派息记录"
                    if it["periods"] == 0
                    else f"近12个月实际派息 {it['periods']} 期（除息 {it['events'][0]['exDate']} ~ {it['events'][-1]['exDate']}）"
                )
                row["官方数据来源"] = f"{prefix} / {desc}"
        pf["recordedAt"] = dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
        json.dump(pf, open(PORTFOLIO, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        write_csv(pf["rows"])
        print("已刷新 portfolio.json / portfolio.csv 股息列")


if __name__ == "__main__":
    main()
