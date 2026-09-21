"""云端重建入口（Actions 内运行）。

1. 取 data/inbox/ 下文件名排序最大的 CSV（DivTracker adjusted 全量导出，
   文件名带时间戳，最新即最新一次导入）。
2. 快照日 END = 所有必需标的在行情缓存中「都有已核实收盘价」的最新公共日期，
   且必须不早于 CSV 最新交易日——否则按「缺已核实收盘价不归档」规则直接报错退出。
3. 调用 rebuild_from_csv.py --write 完成重建（市值自检、最大余数法等全部沿用）。
"""
import csv
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.environ.get("MARKET_CACHE", "/tmp/mkt/parsed.json")
NEEDED = ["QQQM", "VOO", "QNDX", "BITB", "IYW", "CGDV", "SMH",
          "0883.HK", "0700.HK", "000660.KS", "690D.DE"]


def main():
    inbox = sorted(glob.glob(os.path.join(ROOT, "data", "inbox", "*.csv")))
    if not inbox:
        sys.exit("data/inbox 下没有 CSV，无法重建")
    csv_path = inbox[-1]
    print("使用 CSV:", os.path.relpath(csv_path, ROOT))

    last_trade = ""
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            d = (row.get("Date") or "").strip()
            if d > last_trade:
                last_trade = d
    if not last_trade:
        sys.exit("CSV 中没有可识别的 Date 列")

    data = json.load(open(CACHE))
    common = None
    for s in NEEDED:
        days = {d for d, _ in data.get(s, [])}
        if not days:
            sys.exit(f"{s} 无行情数据，终止（缺已核实收盘价不得归档）")
        common = days if common is None else (common & days)
    end = max(common) if common else None

    if end is None or end < last_trade:
        sys.exit(f"快照日 {end} 早于最新交易日 {last_trade}：存在标的当日尚无已核实收盘价，"
                 f"按规则不归档。请等该日全市场收盘后再同步。")

    print(f"快照日 END = {end}（最新交易日 {last_trade}）")
    subprocess.run([
        sys.executable,
        os.path.join(ROOT, "scripts", "rebuild_from_csv.py"),
        csv_path,
        "--end", end,
        "--market-cache", CACHE,
        "--write",
    ], check=True)


if __name__ == "__main__":
    main()
