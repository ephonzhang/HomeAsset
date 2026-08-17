import { defineStore } from "pinia";
import { computed, ref } from "vue";
import {
  loadPortfolioData,
  type PortfolioRow,
  summarizeByCategory,
} from "../lib/portfolioData";

export const usePortfolioStore = defineStore("portfolio", () => {
  const rows = ref<PortfolioRow[]>([]);
  const total = ref<PortfolioRow | null>(null);
  const isLoading = ref(true);
  const error = ref<string | null>(null);
  const dataDate = ref<string | undefined>(undefined);

  async function load() {
    isLoading.value = true;
    error.value = null;
    try {
      const result = await loadPortfolioData();
      rows.value = result.holdings;
      total.value = result.total;
      dataDate.value = result.snapshotDate;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "数据读取失败";
    } finally {
      isLoading.value = false;
    }
  }

  const totalAssets = computed(() =>
    rows.value.reduce((sum, row) => sum + row.marketValue, 0),
  );
  const totalNetDividend = computed(() =>
    rows.value.reduce((sum, row) => sum + row.netDividend, 0),
  );
  const totalGrossDividend = computed(() =>
    rows.value.reduce((sum, row) => sum + row.grossDividend, 0),
  );
  const totalDividendTax = computed(() =>
    rows.value.reduce((sum, row) => sum + row.dividendTax, 0),
  );
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
  const categoryRows = computed(() =>
    summarizeByCategory(rows.value).sort((a, b) => b.marketValue - a.marketValue),
  );
  const holdingRows = computed(() =>
    [...rows.value].sort((a, b) => b.marketValue - a.marketValue),
  );
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
