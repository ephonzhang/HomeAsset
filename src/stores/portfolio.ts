import { defineStore } from "pinia";
import { computed, ref } from "vue";
import {
  loadPortfolioData,
  loadDailyHoldings,
  type DailyHoldingsData,
  type PortfolioRow,
  summarizeByCategory,
} from "../lib/portfolioData";
import {
  buildFromCsv,
  type ImportedResult,
  type ImportMeta,
} from "../lib/importEngine";

/* ============ 导入数据持久化（IndexedDB 优先，localStorage 兜底） ============ */
const DB_NAME = "family-wealth-import";
const STORE_NAME = "import";
const KEY = "current";
const LS_KEY = "family-wealth-import/current";

type PersistedImport = { csvText: string; fileName: string; meta: ImportMeta };

/** 存档落地的后端：indexeddb 优先，localStorage 为兜底，none 表示两者都不可用 */
export type PersistBackend = "indexeddb" | "localStorage" | "none";
/** idle=未导入 / saved=刚写入 / restored=本次刷新从存档恢复 / failed=写入被拒绝 */
export type PersistStatus = "idle" | "saved" | "restored" | "failed";

function idbAvailable(): boolean {
  return typeof indexedDB !== "undefined";
}

function idbOpen(): Promise<IDBDatabase | null> {
  return new Promise((resolve) => {
    if (!idbAvailable()) return resolve(null);
    const openWithUpgrade = (version: number, onDone: (db: IDBDatabase | null) => void) => {
      try {
        const req = indexedDB.open(DB_NAME, version);
        req.onupgradeneeded = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains(STORE_NAME)) db.createObjectStore(STORE_NAME);
        };
        req.onsuccess = () => onDone(req.result);
        req.onerror = () => onDone(null);
        req.onblocked = () => onDone(null);
      } catch {
        onDone(null);
      }
    };
    openWithUpgrade(1, (db) => {
      if (!db) return resolve(null);
      // 兼容：库可能被外部代码以相同版本号先行创建（有库无仓），此时 upgrade 不会触发，
      // 需升一个版本补建对象仓，否则后续 transaction 会抛 NotFoundError 导致静默不持久化。
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const ver = db.version;
        db.close();
        return openWithUpgrade(ver + 1, (db2) => resolve(db2));
      }
      resolve(db);
    });
  });
}

/** 写入 IndexedDB，成功返回 true；任何失败（无痕、第三方 iframe、存储被限制）返回 false */
async function idbSave(rec: PersistedImport): Promise<boolean> {
  const db = await idbOpen();
  if (!db) return false;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, "readwrite");
      tx.objectStore(STORE_NAME).put(rec, KEY);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
      tx.onabort = () => resolve(false);
    } catch {
      resolve(false);
    }
  });
}

async function idbLoad(): Promise<PersistedImport | null> {
  const db = await idbOpen();
  if (!db) return null;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, "readonly");
      const req = tx.objectStore(STORE_NAME).get(KEY);
      req.onsuccess = () => resolve((req.result as PersistedImport) ?? null);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

async function idbClear(): Promise<void> {
  const db = await idbOpen();
  if (!db) return;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, "readwrite");
      tx.objectStore(STORE_NAME).delete(KEY);
      tx.oncomplete = () => resolve();
      tx.onerror = () => resolve();
    } catch {
      resolve();
    }
  });
}

/** 存档写入：IndexedDB 失败时回退 localStorage，两者都失败返回 false（由调用方提示用户） */
async function saveImport(rec: PersistedImport, onBackend: (b: PersistBackend) => void): Promise<boolean> {
  if (await idbSave(rec)) {
    onBackend("indexeddb");
    return true;
  }
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(rec));
    onBackend("localStorage");
    return true;
  } catch {
    onBackend("none");
    return false;
  }
}

async function loadSavedImport(onBackend: (b: PersistBackend) => void): Promise<PersistedImport | null> {
  const rec = await idbLoad();
  if (rec) {
    onBackend("indexeddb");
    return rec;
  }
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) {
      onBackend("localStorage");
      return JSON.parse(raw) as PersistedImport;
    }
  } catch {
    /* 忽略：localStorage 在受限上下文也会抛错 */
  }
  return null;
}

async function clearSavedImport(): Promise<void> {
  await idbClear();
  try {
    localStorage.removeItem(LS_KEY);
  } catch {
    /* 忽略 */
  }
}

export const usePortfolioStore = defineStore("portfolio", () => {
  // 静态模板（来自 public/data，永不被导入覆盖）
  const rowsTemplate = ref<PortfolioRow[]>([]);
  const totalTemplate = ref<PortfolioRow | null>(null);
  const dateTemplate = ref<string | undefined>(undefined);
  const dailyTemplate = ref<DailyHoldingsData | null>(null);

  // 当前生效数据（静态 或 导入覆盖）
  const rows = ref<PortfolioRow[]>([]);
  const total = ref<PortfolioRow | null>(null);
  const dataDate = ref<string | undefined>(undefined);
  const daily = ref<DailyHoldingsData | null>(null);

  const importedMeta = ref<ImportMeta | null>(null);
  const isImported = computed(() => importedMeta.value !== null);

  // 当前生效的 CSV 原文（用于导出存档）
  const currentCsvText = ref<string>("");
  // 持久化可见性：存档是否真的写进了浏览器
  const persistBackend = ref<PersistBackend>("none");
  const persistStatus = ref<PersistStatus>("idle");
  const persistMessage = ref<string | null>(null);
  const persistOk = computed(
    () => persistStatus.value === "saved" || persistStatus.value === "restored",
  );

  const isLoading = ref(true);
  const error = ref<string | null>(null);

  async function load() {
    isLoading.value = true;
    error.value = null;
    try {
      const [pf, dh] = await Promise.all([loadPortfolioData(), loadDailyHoldings()]);
      rowsTemplate.value = pf.holdings;
      totalTemplate.value = pf.total;
      dateTemplate.value = pf.snapshotDate;
      dailyTemplate.value = dh;

      // SPA 内已有生效数据（如刚应用的导入）时，只刷新模板，绝不重置当前数据，
      // 否则 load 的「静态重置 + 恢复存档」会与刚完成的导入互相覆盖（竞态）。
      if (rows.value.length) {
        return;
      }

      // 冷启动：先给静态数据，再尝试恢复已保存的导入（用当前静态数据重算，行情随之更新）
      rows.value = pf.holdings;
      total.value = pf.total;
      dataDate.value = pf.snapshotDate;
      daily.value = dh;

      const saved = await loadSavedImport((b) => (persistBackend.value = b));
      if (saved) {
        // 恢复失败时保留存档（不清除），避免误删用户的 CSV 数据；仅放弃本次恢复
        try {
          const res = buildFromCsv(saved.csvText, dh, pf.holdings, saved.fileName);
          // 恢复路径不重复写存档，仅标记来源
          await applyResult(res, saved.csvText, { persist: false });
          persistStatus.value = "restored";
          persistMessage.value = null;
        } catch (err) {
          console.warn("[portfolio] 恢复导入存档失败，已回退静态数据", err);
          persistStatus.value = "failed";
          persistMessage.value = "存档存在但重新计算失败，已回退静态数据。";
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : "数据读取失败";
    } finally {
      isLoading.value = false;
    }
  }

  /** 仅预览，不写入/不持久化 */
  function buildPreview(csvText: string, fileName = "import.csv"): ImportedResult {
    return buildFromCsv(csvText, dailyTemplate.value, rowsTemplate.value, fileName);
  }

  /**
   * 应用一份已构建好的导入结果。
   * 默认会持久化 CSV 原文（返回是否写成功，可 await 防止刷新竞态）；
   * `persist: false` 用于「从存档恢复」的场景，避免重复写入。
   */
  async function applyResult(
    res: ImportedResult,
    csvText: string,
    opts: { persist?: boolean } = {},
  ): Promise<boolean> {
    rows.value = res.portfolio.holdings;
    total.value = res.portfolio.total;
    dataDate.value = res.portfolio.snapshotDate;
    daily.value = res.daily;
    importedMeta.value = res.meta;
    currentCsvText.value = csvText;

    if (opts.persist === false) return true;

    const ok = await saveImport(
      { csvText, fileName: res.meta.fileName, meta: res.meta },
      (b) => (persistBackend.value = b),
    );
    persistStatus.value = ok ? "saved" : "failed";
    persistMessage.value = ok
      ? null
      : "浏览器拒绝写入本地存档（无痕模式 / 嵌套 iframe / 存储受限），刷新后会回到静态数据。";
    return ok;
  }

  /** 解析并应用 CSV（便捷入口） */
  async function applyCsv(csvText: string, fileName = "import.csv") {
    const res = buildPreview(csvText, fileName);
    await applyResult(res, csvText);
    return res;
  }

  /** 导出存档 JSON（含 CSV 原文，可换设备/换浏览器恢复） */
  function exportArchive(): string {
    if (!currentCsvText.value) return "";
    return JSON.stringify(
      {
        version: 1,
        exportedAt: new Date().toISOString(),
        fileName: importedMeta.value?.fileName ?? "import.csv",
        meta: importedMeta.value ?? null,
        csvText: currentCsvText.value,
      },
      null,
      2,
    );
  }

  /** 从存档 JSON 恢复 */
  async function restoreArchive(text: string): Promise<boolean> {
    let parsed: { csvText?: string; fileName?: string };
    try {
      parsed = JSON.parse(text) as { csvText?: string; fileName?: string };
    } catch {
      throw new Error("存档不是合法 JSON");
    }
    if (!parsed.csvText) throw new Error("存档缺少 csvText 字段");
    const res = buildPreview(parsed.csvText, parsed.fileName || "存档.csv");
    return applyResult(res, parsed.csvText);
  }

  /** 清除导入，恢复静态数据 */
  async function clearImport() {
    rows.value = rowsTemplate.value;
    total.value = totalTemplate.value;
    dataDate.value = dateTemplate.value;
    daily.value = dailyTemplate.value;
    importedMeta.value = null;
    currentCsvText.value = "";
    persistStatus.value = "idle";
    persistMessage.value = null;
    await clearSavedImport();
  }

  const totalAssets = computed(() => rows.value.reduce((sum, row) => sum + row.marketValue, 0));
  const totalNetDividend = computed(() => rows.value.reduce((sum, row) => sum + row.netDividend, 0));
  const totalGrossDividend = computed(() => rows.value.reduce((sum, row) => sum + row.grossDividend, 0));
  const totalDividendTax = computed(() => rows.value.reduce((sum, row) => sum + row.dividendTax, 0));
  const dividendYield = computed(() =>
    totalAssets.value ? (totalNetDividend.value / totalAssets.value) * 100 : 0,
  );
  const largestHolding = computed<PortfolioRow | undefined>(() =>
    [...rows.value].sort((a, b) => b.marketValue - a.marketValue)[0],
  );
  const topDividend = computed<PortfolioRow | undefined>(() =>
    [...rows.value].sort((a, b) => b.netDividend - a.netDividend)[0],
  );
  const categories = computed(() => [
    "全部",
    ...Array.from(new Set(rows.value.map((row) => row.category))),
  ]);
  const categoryRows = computed(() => summarizeByCategory(rows.value).sort((a, b) => b.marketValue - a.marketValue));
  const holdingRows = computed(() => [...rows.value].sort((a, b) => b.marketValue - a.marketValue));
  const dividendComparisonRows = computed(() =>
    [...rows.value].sort((a, b) => {
      const aZero = a.netDividend <= 0 && a.grossDividend <= 0;
      const bZero = b.netDividend <= 0 && b.grossDividend <= 0;
      if (aZero !== bZero) return aZero ? 1 : -1;
      if (b.netDividend !== a.netDividend) return b.netDividend - a.netDividend;
      return b.grossDividend - a.grossDividend;
    }),
  );

  return {
    rows,
    total,
    isLoading,
    error,
    dataDate,
    daily,
    dailyTemplate,
    importedMeta,
    isImported,
    currentCsvText,
    persistBackend,
    persistStatus,
    persistMessage,
    persistOk,
    load,
    buildPreview,
    applyResult,
    applyCsv,
    exportArchive,
    restoreArchive,
    clearImport,
    totalAssets,
    totalNetDividend,
    totalGrossDividend,
    totalDividendTax,
    dividendYield,
    largestHolding,
    topDividend,
    categories,
    categoryRows,
    holdingRows,
    dividendComparisonRows,
  };
});
