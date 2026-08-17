export type PortfolioRow = {
  sequence: string;
  code: string;
  name: string;
  position: string;
  marketValue: number;
  weight: number;
  dividendPerShare: string;
  taxRate: number;
  grossDividend: number;
  dividendTax: number;
  netDividend: number;
  dividendContribution: number;
  source: string;
  category: string;
};

// GitHub Pages 等子路径部署时，数据请求需跟随 Vite base 路径
const DATA_BASE = import.meta.env.BASE_URL;

export type PortfolioData = {
  holdings: PortfolioRow[];
  total: PortfolioRow | null;
  snapshotDate?: string;
  recordedAt?: string;
};

/* ============ 每日持仓（daily-holdings.json） ============ */

export type DailyHoldingEntry = {
  shares: number;
  price: number;
  fx: number;
  mv: number;
};

export type DailyDay = {
  date: string;
  totalAssets: number;
  holdings: Record<string, DailyHoldingEntry>;
  events: string[];
};

export type DailyHoldingsData = {
  generatedAt: string;
  startDate: string;
  endDate: string;
  fx: Record<string, Record<string, number>>;
  prices: Record<string, Record<string, number>>;
  days: DailyDay[];
};

export async function loadDailyHoldings(): Promise<DailyHoldingsData | null> {
  const response = await fetchIfExists(DATA_BASE + "data/daily-holdings.json");
  if (!response) return null;
  return (await response.json()) as DailyHoldingsData;
}

export const FIELD_MAP: Record<string, string> = {
  sequence: "序号",
  code: "标的代码",
  name: "标的全称",
  position: "持仓头寸",
  marketValue: "折合人民币市值",
  weight: "仓位占比",
  dividendPerShare: "过去12个月每股已派发股息（原生币种）",
  taxRate: "适用股息税率",
  grossDividend: "税前总股息（人民币）",
  dividendTax: "应缴股息税（人民币）",
  netDividend: "税后到手股息（人民币）",
  dividendContribution: "税后股息贡献占比",
  source: "官方数据来源",
};

export const TABLE_HEADERS = [
  { key: "code", label: "标的代码" },
  { key: "name", label: "标的全称" },
  { key: "category", label: "资产类别" },
  { key: "position", label: "持仓头寸" },
  { key: "marketValue", label: "折合人民币市值" },
  { key: "weight", label: "仓位占比" },
  { key: "dividendPerShare", label: "过去12个月每股已派发股息" },
  { key: "taxRate", label: "适用股息税率" },
  { key: "grossDividend", label: "税前总股息" },
  { key: "dividendTax", label: "应缴股息税" },
  { key: "netDividend", label: "税后到手股息" },
  { key: "dividendContribution", label: "税后股息贡献占比" },
  { key: "source", label: "官方数据来源" },
] as const;

export function parseMoney(value: unknown): number {
  if (value === null || value === undefined) return 0;
  const normalized = String(value).replace(/,/g, "").replace(/"/g, "").trim();
  const num = Number(normalized);
  return Number.isFinite(num) ? num : 0;
}

export function parsePercent(value: unknown): number {
  if (value === null || value === undefined) return 0;
  const normalized = String(value).replace("%", "").trim();
  const num = Number(normalized);
  return Number.isFinite(num) ? num : 0;
}

export function getCategory(code: string): string {
  if (["QQQM", "VOO", "QNDX", "IYW", "BITB", "CGDV", "SMH"].includes(code)) return "美股 ETF";
  if (["0883.HK", "0700.HK", "883", "700"].includes(code)) return "港股";
  if (code === "690D.DE") return "D 股";
  if (code === "000660.KS") return "韩股";
  if (code === "BYTE") return "内部期权";
  return "其他";
}

export function normalizeRow(row: Record<string, unknown>): PortfolioRow {
  const code = String(row[FIELD_MAP.code] ?? "").trim();
  return {
    sequence: String(row[FIELD_MAP.sequence] ?? "").trim(),
    code,
    name: String(row[FIELD_MAP.name] ?? "").trim(),
    position: String(row[FIELD_MAP.position] ?? "").trim(),
    marketValue: parseMoney(row[FIELD_MAP.marketValue]),
    weight: parsePercent(row[FIELD_MAP.weight]),
    dividendPerShare: String(row[FIELD_MAP.dividendPerShare] ?? "").trim(),
    taxRate: parsePercent(row[FIELD_MAP.taxRate]),
    grossDividend: parseMoney(row[FIELD_MAP.grossDividend]),
    dividendTax: parseMoney(row[FIELD_MAP.dividendTax]),
    netDividend: parseMoney(row[FIELD_MAP.netDividend]),
    dividendContribution: parsePercent(row[FIELD_MAP.dividendContribution]),
    source: String(row[FIELD_MAP.source] ?? "").trim(),
    category: getCategory(code),
  };
}

export function splitRows(rows: PortfolioRow[]): { holdings: PortfolioRow[]; total: PortfolioRow | null } {
  const total = rows.find((row) => row.sequence === "合计") ?? null;
  const holdings = rows.filter((row) => row.sequence !== "合计" && row.code);
  return { holdings, total };
}

function getRowsFromJson(json: unknown): Record<string, unknown>[] {
  if (Array.isArray(json)) return json as Record<string, unknown>[];
  if (json && typeof json === "object" && Array.isArray((json as { rows?: unknown }).rows)) {
    return (json as { rows: Record<string, unknown>[] }).rows;
  }
  return [];
}

async function fetchIfExists(path: string): Promise<Response | null> {
  try {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) return null;
    return response;
  } catch {
    return null;
  }
}

export async function loadPortfolioData(): Promise<PortfolioData> {
  const jsonResponse = await fetchIfExists(DATA_BASE + "data/portfolio.json");
  if (jsonResponse) {
    const json = await jsonResponse.json();
    const rows = getRowsFromJson(json).map(normalizeRow);
    return { ...splitRows(rows), snapshotDate: json.date, recordedAt: json.recordedAt };
  }

  const csvResponse = await fetchIfExists(DATA_BASE + "data/portfolio.csv");
  if (csvResponse) {
    const csvText = await csvResponse.text();
    const lines = csvText.split(/\r?\n/).filter((line) => line.trim().length > 0);
    const header = lines[0].split(",").map((h) => h.replace(/"/g, "").trim());
    const rows = lines.slice(1).map((line) => {
      const cells = line.split(",").map((c) => c.replace(/^"|"$/g, ""));
      const record: Record<string, unknown> = {};
      header.forEach((h, i) => (record[h] = cells[i] ?? ""));
      return normalizeRow(record);
    });
    return { ...splitRows(rows), snapshotDate: undefined };
  }

  throw new Error("未找到 data/portfolio.json 或 data/portfolio.csv");
}

export function summarizeByCategory(rows: PortfolioRow[]) {
  const grouped = rows.reduce<Record<string, { category: string; marketValue: number; netDividend: number }>>(
    (acc, row) => {
      acc[row.category] ??= { category: row.category, marketValue: 0, netDividend: 0 };
      acc[row.category].marketValue += row.marketValue;
      acc[row.category].netDividend += row.netDividend;
      return acc;
    },
    {},
  );
  return Object.values(grouped).sort((a, b) => b.marketValue - a.marketValue);
}
