"""Actions 环境抓行情（GitHub runner 在境外，直连即可，无需代理）。

输出 parsed.json：{symbol: [[date, close], ...]}，键名与 rebuild_from_csv.py 的
PRICE_MAP / FX_MAP 对齐（Yahoo 的 "USDCNY=X" 转成 "USDCNY_X"）。

690D.DE：Yahoo 的 .DE 行情通常滞后 1–3 个交易日，用德交所 XETR 官方
price_information/single 接口补最新一日收盘（仅覆盖/追加最新一日，
不触碰更早的历史序列，与「行情只追加不覆盖」规则一致）。
"""
import datetime as dt
import json
import os
import subprocess
import time

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")
OUT = os.environ.get("MARKET_CACHE", "/tmp/mkt/parsed.json")
XETR_URL = ("https://api.live.deutsche-boerse.com/v1/data/price_information/single"
            "?isin=CNE1000031C1&mic=XETR")

SYMS = [
    "QQQM", "VOO", "QNDX", "BITB", "IYW", "CGDV", "SMH",
    "0883.HK", "0700.HK", "000660.KS", "690D.DE",
    "USDCNY=X", "HKDCNY=X", "EURCNY=X", "KRWCNY=X",
]


def get(url):
    for _ in range(3):
        p = subprocess.run(["curl", "-s", "--max-time", "30", "-H", f"User-Agent: {UA}", url],
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip().startswith("{"):
            return p.stdout
        time.sleep(1.5)
    return None


def xetr_last_price():
    """德交所 XETR 官方最新价；字段结构宽松解析，取不到返回 None（回退 Yahoo）。"""
    raw = get(XETR_URL)
    if not raw:
        return None
    try:
        j = json.loads(raw)
    except ValueError:
        return None

    def find(obj, keys):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in keys and isinstance(v, (int, float)) and v > 0:
                    return float(v)
            for v in obj.values():
                r = find(v, keys)
                if r is not None:
                    return r
        elif isinstance(obj, list):
            for v in obj:
                r = find(v, keys)
                if r is not None:
                    return r
        return None

    return find(j, {"last_price", "price", "last", "close"})


def main():
    out = {}
    for s in SYMS:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=3mo&interval=1d"
        raw = get(url)
        if not raw:
            print("FAIL", s)
            continue
        try:
            r = json.loads(raw)["chart"]["result"][0]
            ts = r["timestamp"]
            cl = r["indicators"]["quote"][0]["close"]
            rows = []
            for t, c in zip(ts, cl):
                if c is None:
                    continue
                d = dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
                rows.append([d, round(float(c), 6)])
            key = s.replace("=", "_")
            out[key] = rows
            print(f"{s:12s} n={len(rows):4d} {rows[0][0]} ~ {rows[-1][0]}  last={rows[-1][1]}")
        except Exception as e:  # noqa: BLE001
            print("PARSE FAIL", s, e)

    # 690D.DE：XETR 官方价补最新一日（仅当 Yahoo 序列落后于今天时）
    xetr = xetr_last_price()
    if xetr:
        today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
        base = out.setdefault("690D.DE", [])
        hit = [r for r in base if r[0] == today]
        if hit:
            hit[0][1] = round(xetr, 6)
            print(f"690D.DE XETR 官方价覆盖 Yahoo {today} = {xetr:.4f} EUR")
        elif not base or base[-1][0] < today:
            base.append([today, round(xetr, 6)])
            base.sort()
            print(f"690D.DE XETR 官方价追加 {today} = {xetr:.4f} EUR")
        else:
            print("690D.DE Yahoo 序列已含最新日，XETR 价未使用")
    else:
        print("690D.DE XETR 官方价不可用，沿用 Yahoo 序列（可能滞后 1–3 交易日）")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"))
    print("saved", len(out), "->", OUT)


if __name__ == "__main__":
    main()
