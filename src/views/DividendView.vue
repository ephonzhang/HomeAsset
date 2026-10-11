<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { usePortfolioStore } from "../stores/portfolio";
import EChart from "../components/EChart.vue";
import ChapterHero from "../components/ChapterHero.vue";
import { chapters } from "../lib/chapters";
import {
  loadDividends,
  type DividendCalendar,
  type DividendMonth,
} from "../lib/portfolioData";

const store = usePortfolioStore();
const me = chapters[2];

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

function compactMoney(value: number) {
  if (Math.abs(value) >= 100_000_000) return `￥${numberFormatter.format(value / 100_000_000)}亿`;
  if (Math.abs(value) >= 10_000) return `￥${numberFormatter.format(value / 10_000)}万`;
  return formatMoney(value);
}

onMounted(async () => {
  if (!store.rows.length) await store.load();
  calendar.value = await loadDividends();
});

const contributionOption = computed(() => ({
  tooltip: {
    trigger: "axis",
    axisPointer: { type: "shadow" },
    formatter: (items: any[]) =>
      items.map((item) => `${item.name}<br/>税后到手股息：${formatMoney(item.value)}`).join("<br/>"),
  },
  grid: { left: 8, right: 30, top: 8, bottom: 4, containLabel: true },
  xAxis: {
    type: "value",
    axisLabel: { fontSize: 11, color: "var(--ink-faint)", formatter: (v: number) => compactMoney(v) },
    splitLine: { lineStyle: { color: "var(--line-soft)" } },
  },
  yAxis: {
    type: "category",
    inverse: true,
    data: [...store.rows]
      .sort((a, b) => b.netDividend - a.netDividend)
      .slice(0, 10)
      .map((r) => r.code),
    axisLabel: { fontSize: 11, color: "var(--ink-faint)" },
    axisLine: { lineStyle: { color: "var(--line)" } },
  },
  series: [
    {
      name: "税后到手股息",
      type: "bar",
      data: [...store.rows]
        .sort((a, b) => b.netDividend - a.netDividend)
        .slice(0, 10)
        .map((r) => r.netDividend),
      itemStyle: { borderRadius: [0, 6, 6, 0], color: "var(--navy)" },
      barWidth: 18,
    },
  ],
}));

const compareOption = computed(() => ({
  tooltip: {
    trigger: "axis",
    axisPointer: { type: "shadow" },
    formatter: (items: any[]) =>
      items.map((item) => `${item.name}<br/>${item.seriesName}：${formatMoney(item.value)}`).join("<br/>"),
  },
  legend: { top: 0, textStyle: { fontSize: 11, color: "var(--ink-faint)" } },
  grid: { left: 8, right: 24, top: 30, bottom: 4, containLabel: true },
  xAxis: {
    type: "category",
    data: store.dividendComparisonRows.slice(0, 10).map((r) => r.code),
    axisLabel: { fontSize: 11, color: "var(--ink-faint)", interval: 0, rotate: -30 },
    axisLine: { lineStyle: { color: "var(--line)" } },
  },
  yAxis: {
    type: "value",
    axisLabel: { fontSize: 11, color: "var(--ink-faint)", formatter: (v: number) => compactMoney(v) },
    splitLine: { lineStyle: { color: "var(--line-soft)" } },
  },
  series: [
    {
      name: "税前总股息",
      type: "bar",
      data: store.dividendComparisonRows.slice(0, 10).map((r) => r.grossDividend),
      itemStyle: { color: "var(--gold)", borderRadius: [4, 4, 0, 0] },
      barWidth: 14,
    },
    {
      name: "税后到手股息",
      type: "bar",
      data: store.dividendComparisonRows.slice(0, 10).map((r) => r.netDividend),
      itemStyle: { color: "var(--navy)", borderRadius: [4, 4, 0, 0] },
      barWidth: 14,
    },
  ],
}));

const taxOption = computed(() => ({
  tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
  grid: { left: 8, right: 24, top: 8, bottom: 4, containLabel: true },
  xAxis: {
    type: "value",
    axisLabel: { fontSize: 11, color: "var(--ink-faint)", formatter: (v: number) => compactMoney(v) },
    splitLine: { lineStyle: { color: "var(--line-soft)" } },
  },
  yAxis: {
    type: "category",
    inverse: true,
    data: [...store.rows]
      .filter((r) => r.dividendTax > 0)
      .sort((a, b) => b.dividendTax - a.dividendTax)
      .map((r) => r.code),
    axisLabel: { fontSize: 11, color: "var(--ink-faint)" },
    axisLine: { lineStyle: { color: "var(--line)" } },
  },
  series: [
    {
      name: "应缴股息税",
      type: "bar",
      data: [...store.rows]
        .filter((r) => r.dividendTax > 0)
        .sort((a, b) => b.dividendTax - a.dividendTax)
        .map((r) => r.dividendTax),
      itemStyle: { borderRadius: [0, 6, 6, 0], color: "var(--gold-deep)" },
      barWidth: 16,
    },
  ],
}));

/* ============ 派息日历（真实除息记录，数据源 public/data/dividends.json） ============ */
const calendar = ref<DividendCalendar | null>(null);
const activeMonth = ref<number | null>(null);

const monthBars = computed<DividendMonth[]>(() => calendar.value?.months ?? []);
const maxMonthTotal = computed(() => Math.max(1, ...monthBars.value.map((m) => m.net)));
const calendarWindow = computed(() => {
  const w = calendar.value?.window;
  return w ? `${w.startExclusive} ~ ${w.endInclusive}` : "";
});

function monthTone(month: DividendMonth) {
  const ratio = month.net / maxMonthTotal.value;
  if (ratio <= 0.001) return { bg: "#f0efea", fg: "#8c94a0" };
  if (ratio <= 0.2) return { bg: "#e5e0d0", fg: "#5c6570" };
  if (ratio <= 0.4) return { bg: "#d3c8ae", fg: "#20262e" };
  if (ratio <= 0.6) return { bg: "#b8914e", fg: "#ffffff" };
  return { bg: "#16324a", fg: "#f3ebdd" };
}

const activeMonthDetail = computed(() =>
  activeMonth.value == null ? null : (monthBars.value[activeMonth.value - 1] ?? null),
);
</script>

<template>
  <div class="dividend-page">
    <ChapterHero :no="me.no" :label="me.label" :intro="me.intro" />

    <section class="kpi-row">
      <div class="card card-pad mini-stat">
        <p class="kpi-label">税前总股息</p>
        <p class="kpi-value num">{{ formatMoney(store.totalGrossDividend) }}</p>
      </div>
      <div class="card card-pad mini-stat">
        <p class="kpi-label">应缴股息税</p>
        <p class="kpi-value num">{{ formatMoney(store.totalDividendTax) }}</p>
      </div>
      <div class="card card-pad mini-stat">
        <p class="kpi-label">税后到手股息</p>
        <p class="kpi-value num up">{{ formatMoney(store.totalNetDividend) }}</p>
      </div>
      <div class="card card-pad mini-stat">
        <p class="kpi-label">有效税负率</p>
        <p class="kpi-value num">{{ store.totalGrossDividend ? formatPercent((store.totalDividendTax / store.totalGrossDividend) * 100) : "0.00%" }}</p>
      </div>
    </section>

    <section class="card card-pad calendar-card">
      <div class="calendar-head">
        <div>
          <h3 class="section-title serif-title">派息日历</h3>
          <p class="section-hint">
            近 12 个月真实除息记录（{{ calendarWindow }}）· 按除息月份归集 · 颜色深浅 = 当月税后到手股息 · 点击月份查看明细
          </p>
        </div>
      </div>
      <div v-if="monthBars.length" class="calendar-grid">
        <button
          v-for="m in monthBars"
          :key="m.month"
          class="month-cell"
          :class="{ active: activeMonth === m.month, empty: m.net <= 0 }"
          :style="{ background: monthTone(m).bg, color: monthTone(m).fg }"
          @click="activeMonth = activeMonth === m.month ? null : m.month"
        >
          <span class="month-no">{{ m.month }}月</span>
          <span class="month-year">{{ m.year }}</span>
          <span class="month-val num">{{ m.net > 0 ? compactMoney(m.net) : "—" }}</span>
        </button>
      </div>
      <p v-else class="section-hint">派息日历数据未加载（缺 public/data/dividends.json）。</p>
      <div v-if="activeMonthDetail" class="month-detail">
        <p class="month-detail-title">
          {{ activeMonthDetail.year }} 年 {{ activeMonthDetail.month }} 月派息明细（税后 {{ compactMoney(activeMonthDetail.net) }}）
        </p>
        <div v-if="activeMonthDetail.items.length" class="month-detail-list">
          <div v-for="h in activeMonthDetail.items" :key="h.code + h.exDate" class="month-detail-row">
            <span class="mdr-code">{{ h.code }}</span>
            <span class="num up mdr-amount">{{ formatMoney(h.net) }}</span>
            <span class="mdr-date">除息 {{ h.exDate.slice(5) }} · 到账 {{ h.payDate.slice(5) }}</span>
          </div>
        </div>
        <p v-else class="section-hint">该月没有任何标的除息。</p>
      </div>
    </section>

    <section class="charts-grid">
      <div class="card card-pad">
        <h3 class="section-title serif-title">税后股息贡献 Top 10</h3>
        <p class="section-hint">按税后到手股息排名</p>
        <EChart :option="contributionOption" height="330px" />
      </div>
      <div class="card card-pad">
        <h3 class="section-title serif-title">税前 vs 税后股息对比</h3>
        <p class="section-hint">直观呈现税务影响</p>
        <EChart :option="compareOption" height="330px" />
      </div>
      <div class="card card-pad">
        <h3 class="section-title serif-title">应缴股息税分布</h3>
        <p class="section-hint">仅展示有税务负担的标的</p>
        <EChart :option="taxOption" height="300px" />
      </div>
      <div class="card card-pad summary-card">
        <h3 class="section-title serif-title">收益结构</h3>
        <p class="section-hint">税前 → 税负 → 到手</p>
        <div class="stack-bars">
          <div class="stack-row">
            <span class="stack-label">税前总股息</span>
            <div class="stack-track"><div class="stack-fill" style="width: 100%; background: var(--gold)" /></div>
            <span class="stack-val num">{{ compactMoney(store.totalGrossDividend) }}</span>
          </div>
          <div class="stack-row">
            <span class="stack-label">应缴股息税</span>
            <div class="stack-track">
              <div class="stack-fill" :style="{ width: `${store.totalGrossDividend ? (store.totalDividendTax / store.totalGrossDividend) * 100 : 0}%`, background: 'var(--up)' }" />
            </div>
            <span class="stack-val num">{{ compactMoney(store.totalDividendTax) }}</span>
          </div>
          <div class="stack-row">
            <span class="stack-label">税后到手</span>
            <div class="stack-track">
              <div class="stack-fill" :style="{ width: `${store.totalGrossDividend ? (store.totalNetDividend / store.totalGrossDividend) * 100 : 0}%`, background: 'var(--navy)' }" />
            </div>
            <span class="stack-val num up">{{ compactMoney(store.totalNetDividend) }}</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.dividend-page {
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

.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 14px;
}

.mini-stat .kpi-value {
  margin-top: 4px;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  margin-top: 16px;
}

.month-cell {
  border: 0.5px solid var(--line);
  border-radius: var(--radius-md);
  padding: 10px 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  transition: transform 0.15s ease, border-color 0.15s ease;
  font-family: var(--font-sans);
}

.month-cell:hover {
  transform: translateY(-2px);
  border-color: var(--gold);
}

.month-cell.active {
  outline: 2px solid var(--gold);
  outline-offset: 1px;
}

.month-no {
  font-size: 11px;
  font-weight: 500;
}

.month-year {
  font-size: 10px;
  opacity: 0.72;
  letter-spacing: 0.02em;
}

.month-val {
  font-size: 12px;
  font-weight: 500;
}

.month-detail {
  margin-top: 14px;
  border-top: 0.5px solid var(--line);
  padding-top: 12px;
}

.month-detail-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink);
  margin: 0 0 8px;
}

.month-detail-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 8px;
}

.month-detail-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: baseline;
  column-gap: 12px;
  row-gap: 1px;
  font-size: 12.5px;
  color: var(--ink-soft);
  padding: 6px 10px;
  background: var(--surface-tint);
  border-radius: 6px;
}

.mdr-code {
  font-weight: 500;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mdr-amount {
  white-space: nowrap;
}

.mdr-date {
  grid-column: 1 / -1;
  font-size: 11px;
  color: var(--ink-faint);
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.stack-bars {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stack-row {
  display: grid;
  grid-template-columns: 76px 1fr 70px;
  gap: 10px;
  align-items: center;
}

.stack-label {
  font-size: 12px;
  color: var(--ink-soft);
}

.stack-track {
  height: 10px;
  border-radius: 6px;
  background: var(--surface-tint);
  overflow: hidden;
}

.stack-fill {
  height: 100%;
  border-radius: 6px;
}

.stack-val {
  font-size: 12.5px;
  text-align: right;
}

@media (max-width: 900px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }

  .calendar-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 480px) {
  .calendar-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
