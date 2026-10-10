import {
  getCategory,
  type DailyDay,
  type DailyHoldingEntry,
  type DailyHoldingsData,
  type PortfolioData,
  type PortfolioRow,
} from "./portfolioData";

/**
 * CSV → 家庭财产统计数据的纯前端导入引擎。
 * 复刻 build_daily.py 的业务规则，但完全在浏览器内运行：
 *  - 行情/汇率直接复用 daily-holdings.json 内嵌的 prices / fx 序列（nearest 取值）
 *  - 股息口径（每股股息、税率、名称、来源）合并静态 portfolio.json 的快照
 * 因此导入过程不依赖任何网络请求。
 */

const BASELINE_CUTOFF = "2025-12-31"; // 基线：截至该日的累计交易
const FIXED_BYTE_SHARES = 171; // BYTE 为固定手动持仓
const BYTE_PRICE = 229.5; // BYTE 固定单价（USD/份）

export type ImportMeta = {
  fileName: string;
  importedAt: string;
  priceAsOf: string; // 内嵌行情序列的最后日期
  tradeCount: number;
  firstTradeDate: string;
  lastTradeDate: string;
  baselineCount: number;
  holdingCount: number;
  warningCodes: string[]; // 无价而跳过估值的标的
};

export type ImportedResult = {
  daily: DailyHoldingsData;
  portfolio: PortfolioData;
  meta: ImportMeta;
};

type Trade = { date: string; ticker: string; qty: number; currency: string };

/* ---------------- 工具 ---------------- */

function normalizeTicker(t: string): string {
  return t === "000660.KR" ? "000660.KS" : t;
}

/** 解析 "1.26925 USD" → { amount, currency } */
function parseDps(raw: string): { amount: number; currency: string } {
  const m = String(raw || "")
    .trim()
    .match(/^([\d.]+)\s*([A-Za-z]{3})$/);
  if (!m) return { amount: 0, currency: "" };
  const amount = parseFloat(m[1]);
  return { amount: Number.isFinite(amount) ? amount : 0, currency: m[2].toUpperCase() };
}

function bisectLeft(keys: string[], ds: string): number {
  let lo = 0;
  let hi = keys.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (keys[mid] < ds) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

/** 用一次排序的 key 数组做 nearest（≤ ds 的最大日期，否则最早） */
function makeSeries(series: Record<string, number> | undefined) {
  const map = series ?? {};
  const keys = Object.keys(map).sort();
  return {
    has: keys.length > 0,
    get(ds: string): number {
      if (map[ds] !== undefined) return map[ds];
      if (!keys.length) return 0;
      const idx = bisectLeft(keys, ds) - 1;
      return idx >= 0 ? map[keys[idx]] : map[keys[0]];
    },
  };
}

function ymd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/* ---------------- CSV 解析 ---------------- */

function parseCsv(text: string): Trade[] {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
  if (lines.length < 2) return [];

  const header = lines[0].split(",").map((h) => h.trim());
  const i = {
    ticker: header.indexOf("Ticker"),
    qty: header.indexOf("Quantity (Adjusted)"),
    qtyLegacy: header.indexOf("Quantity"),
    currency: header.indexOf("Currency"),
    date: header.indexOf("Date"),
  };
  const qtyIdx = i.qty >= 0 ? i.qty : i.qtyLegacy;
  if (i.ticker < 0 || qtyIdx < 0 || i.date < 0) return [];

  const trades: Trade[] = [];
  for (let n = 1; n < lines.length; n++) {
    const cells = lines[n].split(",");
    const qtyS = (cells[qtyIdx] ?? "").trim();
    if (qtyS === "") continue; // 空量行跳过（如成本调整 0 量行）
    const qty = parseFloat(qtyS);
    if (!Number.isFinite(qty)) continue;
    const ticker = normalizeTicker((cells[i.ticker] ?? "").trim());
    const currency = (cells[i.currency] ?? "").trim().toUpperCase() || "USD";
    const date = (cells[i.date] ?? "").trim();
    if (!date) continue;
    trades.push({ date, ticker, qty, currency });
  }
  return trades;
}

/* ---------------- 主流程 ---------------- */

export function buildFromCsv(
  csvText: string,
  template: DailyHoldingsData | null,
  dividendRows: PortfolioRow[],
  fileName = "import.csv",
): ImportedResult {
  const trades = parseCsv(csvText);

  // 股息口径（来自静态 portfolio.json 快照）
  const dividendMeta: Record<
    string,
    { name: string; dpsString: string; dpsAmount: number; dpsCurrency: string; taxRatePct: number; source: string }
  > = {};
  for (const r of dividendRows) {
    const dps = parseDps(r.dividendPerShare);
    dividendMeta[r.code] = {
      name: r.name || r.code,
      dpsString: r.dividendPerShare || "0",
      dpsAmount: dps.amount,
      dpsCurrency: dps.currency,
      taxRatePct: Number.isFinite(r.taxRate) ? r.taxRate : 0,
      source: r.source || "",
    };
  }

  // 每个标的的原生币种（取自交易记录；BYTE 固定 USD）
  const codeCurrency: Record<string, string> = { BYTE: "USD" };
  for (const t of trades) codeCurrency[t.ticker] = t.currency;

  // 基线（截至 2025-12-31 累计 + BYTE 固定）
  const baseline: Record<string, number> = { BYTE: FIXED_BYTE_SHARES };
  for (const t of trades) {
    if (t.date <= BASELINE_CUTOFF) baseline[t.ticker] = (baseline[t.ticker] ?? 0) + t.qty;
  }
  for (const k of Object.keys(baseline)) {
    if (Math.abs(baseline[k]) < 1e-9) delete baseline[k];
  }

  // 2026 年逐日事件
  const eventsByDate: Record<string, { ticker: string; qty: number }[]> = {};
  let firstTrade = trades.length ? trades[0].date : "";
  let lastTrade = trades.length ? trades[0].date : "";
  for (const t of trades) {
    if (t.date < firstTrade) firstTrade = t.date;
    if (t.date > lastTrade) lastTrade = t.date;
    if (t.date > BASELINE_CUTOFF && Math.abs(t.qty) > 1e-9) {
      (eventsByDate[t.date] ??= []).push({ ticker: t.ticker, qty: t.qty });
    }
  }

  const pricesRaw = template?.prices ?? {};
  const fxRaw = template?.fx ?? {};
  const priceSeries: Record<string, ReturnType<typeof makeSeries>> = {};
  for (const code of Object.keys(pricesRaw)) priceSeries[code] = makeSeries(pricesRaw[code]);
  const fxSeries: Record<string, ReturnType<typeof makeSeries>> = {};
  for (const cur of Object.keys(fxRaw)) fxSeries[cur] = makeSeries(fxRaw[cur]);

  const start = template?.startDate || "2026-01-01";
  const end = ymd(new Date());
  const priceAsOf = template?.endDate || end;

  // 逐日演进
  const holdings: Record<string, number> = { ...baseline };
  const days: DailyDay[] = [];
  const warningCodes = new Set<string>();
  let cur = start;
  let guard = 0;
  while (cur <= end && guard < 20000) {
    guard++;
    const evs = eventsByDate[cur] ?? [];
    for (const e of evs) {
      holdings[e.ticker] = (holdings[e.ticker] ?? 0) + e.qty;
      if (Math.abs(holdings[e.ticker]) < 1e-9) holdings[e.ticker] = 0;
    }

    const dayHoldings: Record<string, DailyHoldingEntry> = {};
    let total = 0;
    const codes = Object.keys(holdings)
      .filter((c) => holdings[c] > 0)
      .sort();
    for (const code of codes) {
      const sh = holdings[code];
      const cur0 = codeCurrency[code] || "USD";
      const fxObj = fxSeries[cur0];
      const fx = fxObj && fxObj.has ? fxObj.get(cur) : 1.0;
      let px: number;
      if (code === "BYTE") {
        px = BYTE_PRICE;
      } else if (priceSeries[code] && priceSeries[code].has) {
        px = priceSeries[code].get(cur);
      } else {
        px = 0;
        warningCodes.add(code);
      }
      const mv = sh * px * fx;
      dayHoldings[code] = {
        shares: Math.round(sh * 1e4) / 1e4,
        price: Math.round(px * 1e4) / 1e4,
        fx: Math.round(fx * 1e6) / 1e6,
        mv: Math.round(mv * 100) / 100,
      };
      total += mv;
    }

    days.push({
      date: cur,
      totalAssets: Math.round(total * 100) / 100,
      holdings: dayHoldings,
      events: evs.map((e) => `${e.ticker} ${e.qty > 0 ? "买入 +" : "卖出 "}${Math.abs(e.qty)} 股`),
    });

    // 下一个自然日
    const [y, m, d] = cur.split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    dt.setDate(dt.getDate() + 1);
    cur = ymd(dt);
  }

  const lastDay = days[days.length - 1];

  // 由最后一日持仓 + 股息口径重建 PortfolioRow 快照
  const builtRows: PortfolioRow[] = [];
  const holdingsList = lastDay
    ? Object.entries(lastDay.holdings)
        .map(([code, h]) => ({ code, ...h }))
        .sort((a, b) => b.mv - a.mv)
    : [];

  let totalMv = 0;
  const dividendCalc: { row: PortfolioRow; net: number; gross: number; tax: number }[] = [];
  for (const h of holdingsList) {
    const meta = dividendMeta[h.code];
    const name = meta?.name || h.code;
    const dpsString = meta?.dpsString || "0";
    const dpsAmount = meta?.dpsAmount ?? 0;
    const dpsCurrency = meta?.dpsCurrency || "";
    const taxRatePct = meta?.taxRatePct ?? 0;
    const source = meta?.source || "";

    const fxDps = dpsCurrency && fxSeries[dpsCurrency]?.has ? fxSeries[dpsCurrency]!.get(end) : 1.0;
    const gross = h.shares * dpsAmount * fxDps;
    const net = gross * (1 - taxRatePct / 100);
    const tax = gross - net;
    totalMv += h.mv;

    const row: PortfolioRow = {
      sequence: String(builtRows.length + 1),
      code: h.code,
      name,
      position: `${h.shares}股`,
      marketValue: Math.round(h.mv * 100) / 100,
      weight: 0,
      dividendPerShare: dpsString,
      taxRate: taxRatePct,
      grossDividend: Math.round(gross * 100) / 100,
      dividendTax: Math.round(tax * 100) / 100,
      netDividend: Math.round(net * 100) / 100,
      dividendContribution: 0,
      source,
      category: getCategory(h.code),
    };
    dividendCalc.push({ row, net, gross, tax });
    builtRows.push(row);
  }

  const totalNet = dividendCalc.reduce((s, x) => s + x.net, 0);
  const totalGross = dividendCalc.reduce((s, x) => s + x.gross, 0);
  const totalTax = dividendCalc.reduce((s, x) => s + x.tax, 0);
  for (const x of dividendCalc) {
    x.row.weight = totalMv ? Math.round((x.row.marketValue / totalMv) * 10000) / 100 : 0;
    x.row.dividendContribution = totalNet ? Math.round((x.net / totalNet) * 10000) / 100 : 0;
  }

  const totalRow: PortfolioRow = {
    sequence: "合计",
    code: "",
    name: "",
    position: "",
    marketValue: Math.round(totalMv * 100) / 100,
    weight: 100,
    dividendPerShare: "",
    taxRate: 0,
    grossDividend: Math.round(totalGross * 100) / 100,
    dividendTax: Math.round(totalTax * 100) / 100,
    netDividend: Math.round(totalNet * 100) / 100,
    dividendContribution: 100,
    source: "",
    category: "",
  };

  const portfolio: PortfolioData = {
    holdings: builtRows,
    total: totalRow,
    snapshotDate: end,
    recordedAt: new Date().toISOString(),
  };

  const daily: DailyHoldingsData = {
    generatedAt: new Date().toISOString(),
    startDate: start,
    endDate: end,
    fx: template?.fx ?? {},
    prices: template?.prices ?? {},
    days,
  };
  // 附带行情截至信息，便于前端提示
  (daily as DailyHoldingsData & { priceAsOf?: string }).priceAsOf = priceAsOf;

  const meta: ImportMeta = {
    fileName,
    importedAt: new Date().toISOString(),
    priceAsOf,
    tradeCount: trades.length,
    firstTradeDate: firstTrade,
    lastTradeDate: lastTrade,
    baselineCount: Object.keys(baseline).length,
    holdingCount: holdingsList.length,
    warningCodes: [...warningCodes],
  };

  return { daily, portfolio, meta };
}
