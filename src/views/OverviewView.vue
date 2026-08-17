<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { usePortfolioStore } from "../stores/portfolio";
import { loadDailyHoldings, type DailyHoldingsData } from "../lib/portfolioData";
import EChart from "../components/EChart.vue";
import ChapterHero from "../components/ChapterHero.vue";
import { chapters } from "../lib/chapters";

const store = usePortfolioStore();
const daily = ref<DailyHoldingsData | null>(null);
const me = chapters[0];

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

const chartSeries = ["#16324a", "#c9a96a", "#8c94a0", "#b8914e", "#4a6b8a", "#a8574c", "#5e7d6e", "#7a6a4f", "#6b5b8e", "#7b8894"];

onMounted(async () => {
  await store.load();
  daily.value = await loadDailyHoldings();
});

/** 基于每日持仓：较上一交易日涨跌（无每日数据时回退为空） */
const assetDelta = computed(() => {
  const days = daily.value?.days ?? [];
  if (days.length < 2) return null;
  const cur = days[days.length - 1].totalAssets;
  const prev = days[days.length - 2].totalAssets;
  if (!prev) return null;
  return { delta: cur - prev, pct: ((cur - prev) / prev) * 100 };
});

/** 净值迷你曲线：最近 90 天总资产 */
const sparkOption = computed(() => {
  const days = daily.value?.days ?? [];
  const slice = days.slice(-90);
  const dates = slice.map((d) => d.date.slice(5));
  const values = slice.map((d) => d.totalAssets);
  if (!dates.length) {
    dates.push(store.dataDate?.slice(5) ?? "今日");
    values.push(store.totalAssets);
  }
  return {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "line" },
      formatter: (items: any[]) =>
        items.length ? `${items[0].name}<br/>总资产：${compactMoney(items[0].value)}` : "",
    },
    grid: { left: 4, right: 4, top: 14, bottom: 4, containLabel: false },
    xAxis: { type: "category", boundaryGap: false, show: false, data: dates },
    yAxis: { type: "value", show: false },
    series: [
      {
        name: "总资产",
        type: "line",
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#c9a96a", width: 2 },
        areaStyle: { color: "rgba(201, 169, 106, 0.14)" },
        data: values,
      },
    ],
  };
});

const pieOption = computed(() => ({
  tooltip: {
    trigger: "item",
    formatter: (p: any) => `${p.name}<br/>市值：${formatMoney(p.value)}<br/>占比：${p.percent}%`,
  },
  legend: {
    orient: "vertical",
    right: 6,
    top: "middle",
    itemWidth: 10,
    itemHeight: 10,
    textStyle: { fontSize: 11, color: "var(--ink-faint)" },
  },
  series: [
    {
      name: "配置占比",
      type: "pie",
      radius: ["58%", "80%"],
      center: ["34%", "50%"],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: "var(--surface)", borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 13, fontWeight: 500, formatter: "{b}\n{d}%" } },
      data: store.categoryRows.map((c, i) => ({
        name: c.category,
        value: c.marketValue,
        itemStyle: { color: chartSeries[i % chartSeries.length] },
      })),
    },
  ],
}));

function exportCsv() {
  const header = "序号,标的代码,标的全称,持仓头寸,折合人民币市值,仓位占比,股息,税率,税前总股息,应缴股息税,税后到手股息,贡献占比,来源";
  const lines = store.holdingRows.map((r, i) =>
    [i + 1, r.code, r.name, r.position, r.marketValue.toFixed(2), `${r.weight.toFixed(2)}%`, r.dividendPerShare, `${r.taxRate}%`, r.grossDividend.toFixed(2), r.dividendTax.toFixed(2), r.netDividend.toFixed(2), `${r.dividendContribution.toFixed(2)}%`, `"${r.source}"`].join(","),
  );
  const blob = new Blob([`\uFEFF${[header, ...lines].join("\n")}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `portfolio-${store.dataDate ?? "latest"}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <div class="cover-page">
    <ChapterHero :no="me.no" :label="me.label" :intro="me.intro">
      <template #actions>
        <span class="cover-date">{{ store.dataDate ? `数据日期 ${store.dataDate}` : "最新数据" }}</span>
        <button class="btn btn-navy" @click="exportCsv">导出 CSV</button>
      </template>
    </ChapterHero>

    <div v-if="store.isLoading" class="state-card">正在翻阅档案...</div>
    <div v-else-if="store.error" class="state-card state-error">{{ store.error }}</div>

    <template v-else>
      <section class="cover-hero">
        <div class="hero-copy">
          <p class="hero-eyebrow">总资产 · 折合人民币</p>
          <p class="hero-number serif-title">{{ compactMoney(store.totalAssets) }}</p>
          <div class="hero-meta">
            <span v-if="assetDelta" class="hero-badge" :class="assetDelta.pct >= 0 ? 'badge-up' : 'badge-down'">
              {{ assetDelta.pct >= 0 ? "较上日 +" : "较上日 " }}{{ formatPercent(Math.abs(assetDelta.pct)) }}
            </span>
            <span class="hero-meta-text">组合税后股息率 {{ formatPercent(store.dividendYield) }}</span>
          </div>
        </div>
        <div class="hero-chart">
          <EChart :option="sparkOption" height="110px" />
        </div>
      </section>

      <section class="cover-summary">
        <p class="summary-eyebrow">本期摘要</p>
        <p class="summary-quote serif-title">
          「你的资产{{ assetDelta && assetDelta.pct >= 0 ? "稳步增长" : "略有波动" }}，股息仍以美股与港股为支柱。」
        </p>
        <p class="summary-meta">
          税后到手股息 {{ compactMoney(store.totalNetDividend) }} · 覆盖 {{ store.rows.filter((r) => r.netDividend > 0).length }} 个派息标的 ·
          第一大重仓 {{ store.largestHolding?.code ?? "-" }} 占 {{ store.largestHolding ? formatPercent(store.largestHolding.weight) : "-" }}
        </p>
      </section>

      <section class="gain-cards">
        <div class="card card-pad gain-card">
          <p class="kpi-label">税前总股息</p>
          <p class="gain-value num">{{ compactMoney(store.totalGrossDividend) }}</p>
          <p class="kpi-hint">{{ formatMoney(store.totalGrossDividend) }}</p>
        </div>
        <div class="card card-pad gain-card">
          <p class="kpi-label">应缴股息税</p>
          <p class="gain-value num">{{ compactMoney(store.totalDividendTax) }}</p>
          <p class="kpi-hint">有效税负率 {{ store.totalGrossDividend ? formatPercent((store.totalDividendTax / store.totalGrossDividend) * 100) : "0.00%" }}</p>
        </div>
        <div class="card card-pad gain-card">
          <p class="kpi-label">税后到手股息</p>
          <p class="gain-value num up">{{ compactMoney(store.totalNetDividend) }}</p>
          <p class="kpi-hint">组合税后股息率 {{ formatPercent(store.dividendYield) }}</p>
        </div>
      </section>

      <section class="cover-bottom">
        <div class="card card-pad alloc-card">
          <h3 class="section-title serif-title">资产配置</h3>
          <p class="section-hint">按资产类别汇总市值</p>
          <EChart :option="pieOption" height="260px" />
        </div>
        <div class="card card-pad holdings-card">
          <div class="holdings-head">
            <div>
              <h3 class="section-title serif-title">持仓速览</h3>
              <p class="section-hint">按市值降序 Top 标的</p>
            </div>
            <router-link to="/holdings" class="link-gold">查看完整持仓 →</router-link>
          </div>
          <div class="mini-table">
            <div class="mini-row mini-head">
              <span>代码</span><span>名称</span><span class="right">市值</span><span class="right">仓位</span><span class="right">税后股息</span>
            </div>
            <div v-for="row in store.holdingRows.slice(0, 6)" :key="row.code" class="mini-row">
              <span class="code-cell">{{ row.code }}</span>
              <span class="name-cell">{{ row.name }}</span>
              <span class="right num">{{ compactMoney(row.marketValue) }}</span>
              <span class="right num">{{ formatPercent(row.weight) }}</span>
              <span class="right num" :class="row.netDividend > 0 ? 'up' : ''">{{ compactMoney(row.netDividend) }}</span>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.cover-page {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.cover-date {
  font-size: 12px;
  color: var(--ink-faint);
}

.cover-hero {
  background: var(--navy);
  border-radius: var(--radius-xl);
  padding: 28px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.hero-eyebrow {
  font-size: 12px;
  color: #9fb3c8;
  margin: 0 0 8px;
}

.hero-number {
  font-size: 52px;
  color: #f3ebdd;
  margin: 0 0 12px;
  letter-spacing: 0.01em;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.hero-badge {
  padding: 3px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

.badge-up {
  background: #c0392b;
  color: #fff;
}

.badge-down {
  background: #1f7a5c;
  color: #fff;
}

.hero-meta-text {
  font-size: 12px;
  color: #9fb3c8;
}

.hero-chart {
  flex: 1;
  min-width: 240px;
  max-width: 440px;
}

.cover-summary {
  border-left: 2px solid var(--gold);
  padding: 2px 0 2px 18px;
}

.summary-eyebrow {
  font-size: 11px;
  font-weight: 500;
  color: var(--gold-deeper);
  margin: 0 0 4px;
  letter-spacing: 0.06em;
}

.summary-quote {
  font-size: 17px;
  color: var(--ink);
  margin: 0 0 4px;
}

.summary-meta {
  font-size: 12px;
  color: var(--ink-faint);
  margin: 0;
}

.gain-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}

.gain-value {
  font-size: 26px;
  font-weight: 500;
  color: var(--ink);
  margin: 2px 0;
}

.kpi-hint {
  font-size: 12px;
  color: var(--ink-faint);
  margin: 0;
}

.cover-bottom {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 16px;
}

.holdings-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.link-gold {
  font-size: 12px;
  color: var(--gold-deep);
  text-decoration: none;
  white-space: nowrap;
}

.link-gold:hover {
  color: var(--gold-deeper);
}

.mini-table {
  margin-top: 14px;
}

.mini-row {
  display: grid;
  grid-template-columns: 70px 1fr 90px 64px 90px;
  gap: 8px;
  align-items: center;
  padding: 9px 4px;
  border-bottom: 0.5px solid var(--line-soft);
  font-size: 12.5px;
  color: var(--ink-soft);
}

.mini-head {
  font-size: 11px;
  color: var(--ink-faint);
  border-bottom: 0.5px solid var(--line);
}

.mini-row:last-child {
  border-bottom: none;
}

.code-cell {
  font-weight: 500;
  color: var(--ink);
}

.name-cell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.right {
  text-align: right;
}

.state-card {
  background: var(--surface);
  border: 0.5px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 24px;
  text-align: center;
  color: var(--ink-faint);
}

.state-error {
  color: var(--up);
  border-color: var(--up);
}

@media (max-width: 900px) {
  .cover-bottom {
    grid-template-columns: 1fr;
  }

  .hero-number {
    font-size: 40px;
  }
}
</style>
