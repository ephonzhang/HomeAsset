<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { usePortfolioStore } from "../stores/portfolio";
import { TABLE_HEADERS } from "../lib/portfolioData";
import type { PortfolioRow } from "../lib/portfolioData";
import ChapterHero from "../components/ChapterHero.vue";
import { chapters } from "../lib/chapters";

const store = usePortfolioStore();
const me = chapters[1];

const search = ref("");
const category = ref("全部");
const sortKey = ref<keyof PortfolioRow>("marketValue");
const sortDesc = ref(true);
const expanded = ref<string | null>(null);

const numberFormatter = new Intl.NumberFormat("zh-CN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatMoney(value: number) {
  return `￥${numberFormatter.format(value)}`;
}

function formatPercent(value: number) {
  return `${numberFormatter.format(value)}%`;
}

const filteredRows = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  return store.rows
    .filter((row) => category.value === "全部" || row.category === category.value)
    .filter((row) => {
      if (!keyword) return true;
      return `${row.code} ${row.name} ${row.source}`.toLowerCase().includes(keyword);
    })
    .sort((a, b) => {
      const av = a[sortKey.value] ?? 0;
      const bv = b[sortKey.value] ?? 0;
      if (typeof av === "number" && typeof bv === "number") {
        return sortDesc.value ? bv - av : av - bv;
      }
      return sortDesc.value
        ? String(bv).localeCompare(String(av))
        : String(av).localeCompare(String(bv));
    });
});

function toggleSort(key: keyof PortfolioRow) {
  if (sortKey.value === key) {
    sortDesc.value = !sortDesc.value;
  } else {
    sortKey.value = key;
    sortDesc.value = true;
  }
}

function sortIcon(key: keyof PortfolioRow) {
  if (sortKey.value !== key) return "⇅";
  return sortDesc.value ? "↓" : "↑";
}

function toggleExpand(code: string) {
  expanded.value = expanded.value === code ? null : code;
}

function exportCsv() {
  const header = "序号,标的代码,标的全称,持仓头寸,折合人民币市值,仓位占比,股息,税率,税前总股息,应缴股息税,税后到手股息,贡献占比,来源";
  const lines = filteredRows.value.map((r, i) =>
    [i + 1, r.code, r.name, r.position, r.marketValue.toFixed(2), `${r.weight.toFixed(2)}%`, r.dividendPerShare, `${r.taxRate}%`, r.grossDividend.toFixed(2), r.dividendTax.toFixed(2), r.netDividend.toFixed(2), `${r.dividendContribution.toFixed(2)}%`, `"${r.source}"`].join(","),
  );
  const blob = new Blob([`\uFEFF${[header, ...lines].join("\n")}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `holdings-${store.dataDate ?? "latest"}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

onMounted(async () => {
  if (!store.rows.length) await store.load();
});
</script>

<template>
  <div class="holdings-page">
    <ChapterHero :no="me.no" :label="me.label" :intro="me.intro">
      <template #actions>
        <button class="btn" @click="exportCsv">导出 CSV</button>
      </template>
    </ChapterHero>

    <div class="card card-pad">
      <div class="toolbar">
        <div class="toolbar-left">
          <label class="search-box">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="7" />
              <path d="M21 21l-4.3-4.3" />
            </svg>
            <input v-model="search" class="input search-input" placeholder="搜索代码、名称、来源" />
          </label>
          <select v-model="category" class="select">
            <option v-for="c in store.categories" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div class="toolbar-right">
          <span class="chip">显示 {{ filteredRows.length }} / {{ store.rows.length }} 个标的</span>
        </div>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th class="expand-col" />
              <th v-for="h in TABLE_HEADERS" :key="h.key" @click="toggleSort(h.key)" class="sortable">
                {{ h.label }}
                <span class="sort-icon">{{ sortIcon(h.key) }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in filteredRows" :key="row.code">
              <tr class="main-row" @click="toggleExpand(row.code)">
                <td class="expand-col">
                  <span class="expand-arrow" :class="{ open: expanded === row.code }">▸</span>
                </td>
                <td class="code-cell">{{ row.code }}</td>
                <td>{{ row.name }}</td>
                <td><span class="chip">{{ row.category }}</span></td>
                <td class="num">{{ row.position }}</td>
                <td class="num">{{ formatMoney(row.marketValue) }}</td>
                <td class="num">{{ formatPercent(row.weight) }}</td>
                <td class="num">{{ row.dividendPerShare }}</td>
                <td class="num">{{ formatPercent(row.taxRate) }}</td>
                <td class="num">{{ formatMoney(row.grossDividend) }}</td>
                <td class="num">{{ formatMoney(row.dividendTax) }}</td>
                <td class="num up">{{ formatMoney(row.netDividend) }}</td>
                <td class="num">{{ formatPercent(row.dividendContribution) }}</td>
                <td class="source-cell" :title="row.source">{{ row.source }}</td>
              </tr>
              <tr v-if="expanded === row.code" class="detail-row">
                <td colspan="14">
                  <div class="detail-panel">
                    <div class="detail-block">
                      <p class="detail-label">标的</p>
                      <p class="detail-value">{{ row.code }} · {{ row.name }}</p>
                    </div>
                    <div class="detail-block">
                      <p class="detail-label">资产类别</p>
                      <p class="detail-value">{{ row.category }}</p>
                    </div>
                    <div class="detail-block">
                      <p class="detail-label">持仓头寸</p>
                      <p class="detail-value">{{ row.position }}</p>
                    </div>
                    <div class="detail-block">
                      <p class="detail-label">市值 / 仓位</p>
                      <p class="detail-value num">{{ formatMoney(row.marketValue) }} · {{ formatPercent(row.weight) }}</p>
                    </div>
                    <div class="detail-block">
                      <p class="detail-label">过去 12 月每股股息</p>
                      <p class="detail-value">{{ row.dividendPerShare }}</p>
                    </div>
                    <div class="detail-block">
                      <p class="detail-label">税后股息 / 贡献</p>
                      <p class="detail-value num up">{{ formatMoney(row.netDividend) }} · {{ formatPercent(row.dividendContribution) }}</p>
                    </div>
                    <div class="detail-block detail-source">
                      <p class="detail-label">官方数据来源</p>
                      <p class="detail-value">{{ row.source }}</p>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
          <tfoot v-if="store.total">
            <tr>
              <td class="expand-col" />
              <td>合计</td>
              <td></td>
              <td></td>
              <td></td>
              <td class="num">{{ formatMoney(store.total.marketValue) }}</td>
              <td class="num">{{ formatPercent(store.total.weight) }}</td>
              <td></td>
              <td></td>
              <td class="num">{{ formatMoney(store.total.grossDividend) }}</td>
              <td class="num">{{ formatMoney(store.total.dividendTax) }}</td>
              <td class="num up">{{ formatMoney(store.total.netDividend) }}</td>
              <td class="num">{{ formatPercent(store.total.dividendContribution) }}</td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div v-if="!filteredRows.length" class="empty-state">没有匹配的持仓记录</div>
    </div>
  </div>
</template>

<style scoped>
.holdings-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 24px;
  color: var(--ink);
  margin: 0;
}

.page-sub {
  font-size: 12px;
  color: var(--ink-faint);
  margin: 2px 0 0;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.search-box {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 0.5px solid var(--line);
  background: var(--surface);
  border-radius: var(--radius-sm);
  padding: 0 4px 0 12px;
  color: var(--ink-faint);
}

.search-input {
  border: none;
  background: transparent;
  padding: 7px 8px 7px 0;
  width: 220px;
  color: var(--ink);
}

.search-input:focus {
  border: none;
  outline: none;
}

.table-wrap {
  overflow-x: auto;
}

.table {
  min-width: 1760px;
}

.expand-col {
  width: 34px;
  padding: 0 !important;
  text-align: center;
}

.main-row {
  cursor: pointer;
}

.expand-arrow {
  display: inline-block;
  transition: transform 0.2s ease;
  color: var(--gold-deep);
  font-size: 11px;
}

.expand-arrow.open {
  transform: rotate(90deg);
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable:hover {
  color: var(--gold-deeper);
}

.sort-icon {
  font-size: 11px;
  color: var(--ink-faint);
  margin-left: 3px;
}

.code-cell {
  font-weight: 500;
  color: var(--ink);
}

.source-cell {
  max-width: 190px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.detail-row td {
  background: var(--surface-tint) !important;
  border-bottom: 0.5px solid var(--line);
}

.detail-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  padding: 6px 8px;
}

.detail-label {
  font-size: 11px;
  color: var(--ink-faint);
  margin: 0 0 2px;
}

.detail-value {
  font-size: 13px;
  color: var(--ink);
  margin: 0;
}

.detail-source {
  grid-column: 1 / -1;
}

.empty-state {
  text-align: center;
  padding: 30px;
  color: var(--ink-faint);
}
</style>
