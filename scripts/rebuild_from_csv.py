"""用 DivTracker 交易 CSV 重算 daily-holdings.json 与 portfolio.json。

规则与前端 src/lib/importEngine.ts 完全一致：
  - 基线 = 截至 2025-12-31 的累计交易 + BYTE 171（固定）
  - 按自然日演进，市值 = 头寸 × 收盘价(nearest) × 汇率(nearest)
  - 股息口径（每股股息、税率、名称、来源）沿用现有 portfolio.json
"""
import argparse, csv, json, datetime as dt, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

_ap = argparse.ArgumentParser(description="用 DivTracker 交易 CSV 重算持仓数据文件")
_ap.add_argument("csv_path", help="DivTracker 导出的 adjusted CSV 路径")
_ap.add_argument("--end", required=True, help="快照日 YYYY-MM-DD（应为最后一个全部市场已收盘的交易日）")
_ap.add_argument("--market-cache", default="/tmp/mkt2/parsed.json",
                 help="行情增量 JSON（{symbol: [[date, close], ...]}），默认 /tmp/mkt2/parsed.json")
_ap.add_argument("--write", action="store_true", help="写入 public/data；不加则 dry-run")
_args = _ap.parse_args()

CSV_PATH = _args.csv_path
END = _args.end
MARKET_CACHE = _args.market_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = "2026-01-01"
BASELINE_CUTOFF = "2025-12-31"
BYTE_SHARES, BYTE_PRICE = 171, 229.5

# ---------- 读交易 ----------
def norm(t):
    return "000660.KS" if t == "000660.KR" else t

trades = []
with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        q = (row.get("Quantity (Adjusted)") or row.get("Quantity") or "").strip()
        if not q:
            continue
        try:
            qty = float(q)
        except ValueError:
            continue
        d = (row.get("Date") or "").strip()
        if not d:
            continue
        trades.append({
            "date": d,
            "ticker": norm((row.get("Ticker") or "").strip()),
            "qty": qty,
            "ccy": (row.get("Currency") or "USD").strip().upper(),
        })
trades.sort(key=lambda x: (x["date"], x["ticker"]))
print(f"交易笔数 {len(trades)}，区间 {trades[0]['date']} ~ {trades[-1]['date']}")

# ---------- 序列工具 ----------

def r2(v):
    """金额两位小数，四舍五入（与 validate_portfolio_csv.py 的 ROUND_HALF_UP 一致）"""
    return float(Decimal(repr(float(v))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def make_series(series):
    ks = sorted(series.keys())
    def get(d):
        if d in series:
            return series[d]
        prev = [k for k in ks if k <= d]
        return series[prev[-1]] if prev else (series[ks[0]] if ks else 0.0)
    return {"has": bool(ks), "get": get}

def ymd(d):
    return d.strftime("%Y-%m-%d")

# ---------- 载入现有 daily-holdings ----------
dh = json.load(open(os.path.join(ROOT, "public/data/daily-holdings.json")))
prices = {k: dict(v) for k, v in dh["prices"].items()}
fx = {k: dict(v) for k, v in dh["fx"].items()}
print("原 prices 末日:", {k: max(v) for k, v in prices.items()})
print("原 fx 末日:    ", {k: max(v) for k, v in fx.items()})

# ---------- 合并新抓取的行情 ----------
new = json.load(open(MARKET_CACHE))
PRICE_MAP = {k: k for k in ["QQQM","VOO","QNDX","BITB","IYW","CGDV","SMH","0883.HK","0700.HK","000660.KS","690D.DE"]}
FX_MAP = {"USDCNY_X": "USD", "HKDCNY_X": "HKD", "EURCNY_X": "EUR", "KRWCNY_X": "KRW"}

# 只补充「原来没有的新日期」，绝不覆盖已有日期的值
# （原序列的汇率是人民币中间价口径，与 Yahoo 市场价有约 0.2% 差异，覆盖会篡改历史）
added_p, added_f = 0, 0
for sym in PRICE_MAP:
    base = prices.setdefault(sym, {})
    cutoff = max(base) if base else ""      # 只在原序列末日之后追加
    for d, c in new.get(sym, []):
        if d > END or d <= cutoff:
            continue
        base[d] = round(float(c), 6)
        added_p += 1

for key, cur in FX_MAP.items():
    base = fx.setdefault(cur, {})
    cutoff = max(base) if base else ""
    for d, c in new.get(key, []):
        if d > END or d <= cutoff:
            continue
        base[d] = round(float(c), 8)
        added_f += 1
print(f"新增价格点 {added_p} 个、汇率点 {added_f} 个（未覆盖任何已有日期）")

# 690D.DE：德交所 XETR 官方 8/31 收盘（Yahoo .DE 有滞后）——仅该日为快照日时生效，
# 云端跑其他日期时由 cloud_fetch.py 的 XETR 接口负责补充，不得覆盖其他日期。
if END == "2026-08-31":
    prices.setdefault("690D.DE", {})["2026-08-31"] = 1.80
    print("官方补充 690D.DE 2026-08-31 = 1.80 EUR (德交所 XETR)")

print("新 prices 末日:", {k: max(v) for k, v in prices.items() if k in PRICE_MAP})
print("新 fx 末日:    ", {k: max(v) for k, v in fx.items()})

pser = {k: make_series(v) for k, v in prices.items()}
fser = {k: make_series(v) for k, v in fx.items()}

# ---------- 基线 ----------
baseline = {"BYTE": float(BYTE_SHARES)}
ccy = {"BYTE": "USD"}
for t in trades:
    ccy[t["ticker"]] = t["ccy"]
    if t["date"] <= BASELINE_CUTOFF:
        baseline[t["ticker"]] = baseline.get(t["ticker"], 0.0) + t["qty"]
baseline = {k: v for k, v in baseline.items() if abs(v) > 1e-9}
print("基线（2025-12-31）:", {k: round(v, 4) for k, v in sorted(baseline.items())})

# ---------- 逐日演进 ----------
events = {}
for t in trades:
    if t["date"] > BASELINE_CUTOFF and abs(t["qty"]) > 1e-9:
        events.setdefault(t["date"], []).append(t)

hold = dict(baseline)
days, warn = [], set()
cur = dt.date.fromisoformat(START)
end = dt.date.fromisoformat(END)
missing_days = []
while cur <= end:
    ds = ymd(cur)
    evs = events.get(ds, [])
    for e in evs:
        hold[e["ticker"]] = hold.get(e["ticker"], 0.0) + e["qty"]
        if abs(hold[e["ticker"]]) < 1e-9:
            hold[e["ticker"]] = 0.0
    day_h, total = {}, 0.0
    day_missing = False
    for code in sorted(k for k, v in hold.items() if v > 0):
        sh = hold[code]
        c0 = ccy.get(code, "USD")
        f = fser[c0]["get"](ds) if fser.get(c0) and fser[c0]["has"] else 1.0
        if code == "BYTE":
            px = BYTE_PRICE
        elif pser.get(code) and pser[code]["has"]:
            px = pser[code]["get"](ds)
        else:
            px = 0.0
            warn.add(code)
            day_missing = True
        mv = sh * px * f
        day_h[code] = {
            "shares": round(sh, 4),
            "price": round(px, 4),
            "fx": round(f, 6),
            "mv": r2(mv),
        }
        total += mv
    if day_missing:
        missing_days.append(ds)
    days.append({
        "date": ds,
        "totalAssets": r2(total),
        "holdings": day_h,
        "events": [f"{e['ticker']} {'买入 +' if e['qty'] > 0 else '卖出 '}{abs(e['qty']):g} 股" for e in evs],
    })
    cur += dt.timedelta(days=1)

print(f"生成 {len(days)} 天（{days[0]['date']} ~ {days[-1]['date']}）")
print("缺行情代码:", sorted(warn) or "无")
print("缺行情日期:", missing_days[:10], "共", len(missing_days), "天")

# 自检：每日 sum(mv) == totalAssets
bad = [d["date"] for d in days if abs(sum(h["mv"] for h in d["holdings"].values()) - d["totalAssets"]) > 0.05]
print("市值自检不一致天数:", len(bad), bad[:5])

# ---------- 股息口径（沿用现有 portfolio.json） ----------
old = json.load(open(os.path.join(ROOT, "public/data/portfolio.json")))

def refresh_source(s: str, code: str) -> str:
    """股息数字不变，只把来源里的行情日期更新到本次快照日。"""
    if code == "690D.DE" and END == "2026-08-31":
        return "德交所 XETR 2026-08-31 收盘 / StockAnalysis distributions"
    return re.sub(r"2026-\d{2}-\d{2}", END, s)

div_meta = {}
for r in old["rows"]:
    code = (r.get("标的代码") or "").strip()
    if not code or code == "合计":
        continue
    m = re.match(r"^([\d.]+)\s*([A-Za-z]{3})$", (r.get("过去12个月每股已派发股息（原生币种）") or "").strip())
    div_meta[code] = {
        "name": r.get("标的全称", ""),
        "dps": r.get("过去12个月每股已派发股息（原生币种）", "0"),
        "amount": float(m.group(1)) if m else 0.0,
        "ccy": m.group(2).upper() if m else "",
        "tax": float(str(r.get("适用股息税率", "0")).replace("%", "") or 0),
        "source": refresh_source(r.get("官方数据来源", ""), code),
    }

# ---------- 重建 portfolio 行 ----------
last = days[-1]
items = sorted(last["holdings"].items(), key=lambda kv: -kv[1]["mv"])
rows, calc = [], []
for code, h in items:
    meta = div_meta.get(code, {})
    fx_dps = fser[meta.get("ccy", "")]["get"](END) if meta.get("ccy") and fser.get(meta["ccy"]) and fser[meta["ccy"]]["has"] else 1.0
    gross = r2(h["shares"] * meta.get("amount", 0.0) * fx_dps)
    tax = gross * meta.get("tax", 0.0) / 100
    calc.append({"code": code, "mv": h["mv"], "gross": r2(gross), "tax": r2(tax), "net": r2(gross - tax),
                 "meta": meta, "shares": h["shares"]})

tot_mv = r2(sum(c["mv"] for c in calc))
tot_net = r2(sum(c["net"] for c in calc))
tot_gross = r2(sum(c["gross"] for c in calc))
tot_tax = r2(sum(c["tax"] for c in calc))

def fmt(v, p=2):
    return f"{v:,.{p}f}"

def pct_lr(values, total):
    """最大余数法分配百分比，保证四舍五入后合计恰为 100.00%"""
    if not total:
        return ["0.00%" for _ in values]
    exact = [v / total * 100 for v in values]
    floors = [int(v * 100) for v in exact]           # 以 0.01% 为单位
    short = 10000 - sum(floors)
    order = sorted(range(len(values)), key=lambda i: -(exact[i] * 100 - floors[i]))
    for k in range(short):
        floors[order[k % len(order)]] += 1
    return [f"{f / 100:.2f}%" for f in floors]

wmap = pct_lr([c["mv"] for c in calc], tot_mv)
nmap = pct_lr([c["net"] for c in calc], tot_net)


for i, c in enumerate(calc, 1):
    meta = c["meta"]
    rows.append({
        "序号": str(i),
        "标的代码": c["code"],
        "标的全称": meta.get("name", c["code"]),
        "持仓头寸": f"{c['shares']:g}股",
        "折合人民币市值": fmt(c["mv"]),
        "仓位占比": wmap[i - 1],
        "过去12个月每股已派发股息（原生币种）": meta.get("dps", "0"),
        "适用股息税率": f"{meta.get('tax', 0):.1f}%",
        "税前总股息（人民币）": fmt(c["gross"]),
        "应缴股息税（人民币）": fmt(c["tax"]),
        "税后到手股息（人民币）": fmt(c["net"]),
        "税后股息贡献占比": nmap[i - 1],
        "官方数据来源": meta.get("source", ""),
    })

rows.append({
    "序号": "合计",
    "标的代码": "",
    "标的全称": "",
    "持仓头寸": "",
    "折合人民币市值": fmt(tot_mv),
    "仓位占比": "100.00%",
    "过去12个月每股已派发股息（原生币种）": "",
    "适用股息税率": "",
    "税前总股息（人民币）": fmt(tot_gross),
    "应缴股息税（人民币）": fmt(tot_tax),
    "税后到手股息（人民币）": fmt(tot_net),
    "税后股息贡献占比": "100.00%",
    "官方数据来源": "",
})

now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).replace(microsecond=0).isoformat()
portfolio = {"rows": rows, "date": END, "recordedAt": now}

daily_out = {
    "generatedAt": now,
    "startDate": START,
    "endDate": END,
    "fx": fx,
    "prices": prices,
    "days": days,
}

print(f"\n=== {END} 快照 ===")
print(f"总资产 ¥{fmt(tot_mv)}   税后股息 ¥{fmt(tot_net)}")
for c in calc:
    print(f"  {c['code']:10s} {c['shares']:>10g} 股  ¥{fmt(c['mv']):>14s}  {(c['mv']/tot_mv*100):5.2f}%")

if _args.write:
    json.dump(daily_out, open(os.path.join(ROOT, "public/data/daily-holdings.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    json.dump(portfolio, open(os.path.join(ROOT, "public/data/portfolio.json"), "w"), ensure_ascii=False, indent=2)
    # 同步 CSV 副本
    cols = list(rows[0].keys())
    with open(os.path.join(ROOT, "public/data/portfolio.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print("\n已写入 public/data/{daily-holdings.json, portfolio.json, portfolio.csv}")
else:
    print("\n（dry-run，未写入）")
