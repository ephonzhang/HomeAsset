import json, subprocess, sys, time

PROXY = "http://127.0.0.1:7890"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

SYMS = ["QQQM","VOO","QNDX","BITB","IYW","CGDV","SMH","0883.HK","0700.HK","000660.KS","690D.DE",
        "USDCNY=X","HKDCNY=X","EURCNY=X","KRWCNY=X"]

def get(url):
    for attempt in range(3):
        p = subprocess.run(["curl","-s","--max-time","30","-x",PROXY,"-H",f"User-Agent: {UA}",url],
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip().startswith("{"):
            return p.stdout
        time.sleep(1.5)
    return None

out = {}
for s in SYMS:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=3mo&interval=1d"
    raw = get(url)
    if not raw:
        print("FAIL", s); continue
    try:
        j = json.loads(raw)
        r = j["chart"]["result"][0]
        ts = r["timestamp"]; cl = r["indicators"]["quote"][0]["close"]
        import datetime as dt
        rows = []
        for t, c in zip(ts, cl):
            if c is None: continue
            d = dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
            rows.append((d, round(float(c), 6)))
        out[s] = rows
        print(f"{s:12s} n={len(rows):4d} {rows[0][0]} ~ {rows[-1][0]}  last={rows[-1][1]}")
    except Exception as e:
        print("PARSE FAIL", s, e)

json.dump(out, open("/tmp/mkt2/raw.json","w"))
print("saved", len(out))
