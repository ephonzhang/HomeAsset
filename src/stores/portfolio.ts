import { defineStore } from "pinia";
import { computed, ref } from "vue";
import {
  loadPortfolioData,
  loadDailyHoldings,
  type DailyHoldingsData,
  type PortfolioRow,
  summarizeByCategory,
} from "../lib/portfolioData";

/**
 * 纯静态数据源（public/data 由 CI 抓行情后重建并提交）。
 * 页面不再支持浏览器端 CSV 导入，因此这里没有本地存档 / 覆盖逻辑：
 * 每次加载都直接以静态数据文件为准。
 */
export const usePortfolioStore = defineStore("portfolio", () => {
  const rows = ref<PortfolioRow[]>([]);
  const total = ref<PortfolioRow | null>(null);
  const dataDate = ref<string | undefined>(undefined);
  const daily = ref<DailyHoldingsData | null>(null);

  const isLoading = ref(true);
  const error = ref<string | null>(null);

  async function load() {
    isLoading.value = true;
    error.value = null;
    try {
      const [pf, dh] = await Promise.all([loadPortfolioData(), loadDailyHoldings()]);
      rows.value = pf.holdings;
      total.value = pf.total;
      dataDate.value = pf.snapshotDate;
      daily.value = dh;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "数据读取失败";
    } finally {
      isLoading.value = false;
    }
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
    load,
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
