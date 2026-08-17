<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { usePortfolioStore } from "../stores/portfolio";
import {
  loadDailyHoldings,
  type DailyHoldingsData,
  type DailyDay,
} from "../lib/portfolioData";
import EChart from "../components/EChart.vue";
import ChapterHero from "../components/ChapterHero.vue";
import { chapters } from "../lib/chapters";

const store = usePortfolioStore();
const me = chapters[3];

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

/** 读取当前主题下的 CSS 变量色值（canvas 渲染不支持 var()） */
function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#16324a";
}

/* ============ 每日持仓演进 ============ */
const daily = ref<DailyHoldingsData | null>(null);
const selectedDate = ref("");

onMounted(async () => {
  await store.load();
  daily.value = await loadDailyHoldings();
  const days = daily.value?.days ?? [];
  if (days.length) selectedDate.value = days[days.length - 1].date;
});

const days = computed(() => daily.value?.days ?? []);
const firstDay = computed<DailyDay | null>(() => days.value[0] ?? null);
const lastDay = computed<DailyDay | null>(() => days.value[days.value.length - 1] ?? null);

const stats = computed(() => {
  const first = firstDay.value;
  const last = lastDay.value;
  if (!first || !last) return { delta: 0, pct: 0, eventCount: 0, dayCount: 0 };
  const delta = last.totalAssets - first.totalAssets;
  const pct = first.totalAssets ? (delta / first.totalAssets) * 100 : 0;
  const eventCount = days.value.reduce((n, d) => n + d.events.length, 0);
  return { delta, pct, eventCount, dayCount: days.value.length };
});

const assetOption = computed(() => ({
  tooltip: {
    trigger: "axis",
    formatter: (items: any[]) => {
      const it = items[0];
      const day = days.value[it.dataIndex];
      const ev = day?.events?.length ? `<br/><span style="color:var(--ink-faint)">${day.events.join("；")}</span>` : "";
      return `${it.axisValue}<br/>总资产：<b>${compactMoney(it.value)}</b>${ev}`;
    },
  },
  grid: { left: 8, right: 20, top: 24, bottom: 4, containLabel: true },
  xAxis: {
    type: "category",
    boundaryGap: false,
    data: days.value.map((d) => d.date.slice(5)),
    axisLabel: { fontSize: 11, color: cssVar("--ink-faint") },
    axisLine: { lineStyle: { color: cssVar("--line") } },
  },
  yAxis: {
    type: "value",
    axisLabel: { fontSize: 11, color: cssVar("--ink-faint"), formatter: (v: number) => compactMoney(v) },
    splitLine: { lineStyle: { color: cssVar("--line-soft") } },
  },
  series: [
    {
      name: "总资产",
      type: "line",
      smooth: true,
      symbol: "circle",
      symbolSize: 4,
      lineStyle: { color: cssVar("--navy"), width: 2 },
      itemStyle: { color: cssVar("--navy") },
      areaStyle: { color: cssVar("--navy"), opacity: 0.08 },
      data: days.value.map((d) => d.totalAssets),
    },
  ],
}));

const SERIES_COLORS = ["--c1", "--c2", "--c3", "--c4", "--c5", "--c6", "--c7", "--c8", "--c9", "--c10"];

const stackSeries = computed(() => {
  const codeSet = new Set<string>();
  days.value.forEach((d) => Object.keys(d.holdings).forEach((c) => codeSet.add(c)));
  const codes = [...codeSet].sort(
    (a, b) => (lastDay.value?.holdings[b]?.mv ?? 0) - (lastDay.value?.holdings[a]?.mv ?? 0),
  );
  return codes.map((code, i) => ({
    name: code,
    type: "line",
    stack: "total",
    smooth: true,
    symbol: "none",
    lineStyle: { width: 1, color: cssVar(SERIES_COLORS[i % SERIES_COLORS.length]) },
    itemStyle: { color: cssVar(SERIES_COLORS[i % SERIES_COLORS.length]) },
    areaStyle: { opacity: 0.7, color: cssVar(SERIES_COLORS[i % SERIES_COLORS.length]) },
    emphasis: { focus: "series" },
    data: days.value.map((d) => d.holdings[code]?.mv ?? 0),
  }));
});

const stackOption = computed(() => ({
  tooltip: {
    trigger: "axis",
    formatter: (items: any[]) => {
      const date = days.value[items[0]?.dataIndex ?? 0]?.date ?? "";
      const rows = items
        .filter((it: any) => it.value > 0)
        .map((it: any) => `${it.marker}${it.seriesName}：${compactMoney(it.value)}`)
        .join("<br/>");
      const total = items.reduce((s: number, it: any) => s + (it.value || 0), 0);
      return `${date}<br/>${rows}<br/><b>合计：${compactMoney(total)}</b>`;
    },
  },
  legend: {
    top: 0,
    type: "scroll",
    textStyle: { fontSize: 11, color: cssVar("--ink-faint") },
  },
  grid: { left: 8, right: 20, top: 36, bottom: 4, containLabel: true },
  xAxis: {
    type: "category",
    boundaryGap: false,
    data: days.value.map((d) => d.date.slice(5)),
    axisLabel: { fontSize: 11, color: cssVar("--ink-faint") },
    axisLine: { lineStyle: { color: cssVar("--line") } },
  },
  yAxis: {
    type: "value",
    axisLabel: { fontSize: 11, color: cssVar("--ink-faint"), formatter: (v: number) => compactMoney(v) },
    splitLine: { lineStyle: { color: cssVar("--line-soft") } },
  },
  series: stackSeries.value,
}));

const selectedDay = computed<DailyDay | undefined>(() =>
  days.value.find((d) => d.date === selectedDate.value),
);

const selectedRows = computed(() => {
  const day = selectedDay.value;
  if (!day) return [];
  return Object.entries(day.holdings)
    .map(([code, h]) => ({ code, ...h }))
    .sort((a, b) => b.mv - a.mv);
});

function onChartClick(params: any) {
  const day = days.value[params.dataIndex];
  if (day) selectedDate.value = day.date;
}

const eventList = computed(() => {
  const list: { date: string; text: string }[] = [];
  days.value.forEach((d) => d.events.forEach((e) => list.push({ date: d.date, text: e })));
  return list;
});

/* ============ 每日持仓提炼：结构调整 / 月度轨迹 ============ */
const structureChange = computed(() => {
  const first = firstDay.value;
  const last = lastDay.value;
  if (!first || !last) return [];
  const codes = new Set([...Object.keys(first.holdings), ...Object.keys(last.holdings)]);
  return [...codes]
    .map((code) => {
      const start = first.holdings[code]?.shares ?? 0;
      const end = last.holdings[code]?.shares ?? 0;
      const delta = end - start;
      const trades = eventList.value.filter((e) => e.text.startsWith(code)).length;
      return { code, start, end, delta, trades };
    })
    .sort((x, y) => (y.delta !== x.delta ? y.delta - x.delta : y.end - x.end));
});

function changeLabel(row: { start: number; end: number; delta: number }) {
  if (row.start === 0 && row.end > 0) return { text: "新增", cls: "chip-live" };
  if (row.start > 0 && row.end === 0) return { text: "清仓", cls: "chip-out" };
  if (row.delta > 0) return { text: "加仓", cls: "chip-live" };
  if (row.delta < 0) return { text: "减仓", cls: "chip-out" };
  return { text: "不变", cls: "chip-hold" };
}

const monthlyTrajectory = computed(() => {
  const groups = new Map<string, DailyDay[]>();
  days.value.forEach((d) => {
    const key = d.date.slice(0, 7);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(d);
  });
  const months: { month: string; endAssets: number; delta: number; pct: number; events: number; days: number }[] = [];
  let prevAssets: number | null = null;
  for (const [month, list] of [...groups.entries()].sort()) {
    const endAssets = list[list.length - 1].totalAssets;
    const delta = prevAssets === null ? 0 : endAssets - prevAssets;
    const pct = prevAssets ? (delta / prevAssets) * 100 : 0;
    months.push({
      month,
      endAssets,
      delta,
      pct,
      events: list.reduce((n, d) => n + d.events.length, 0),
      days: list.length,
    });
    prevAssets = endAssets;
  }
  return months;
});

/* ============ 历史快照（归档，已停用） ============ */
</script>

<template>
  <div class="history-page">
    <ChapterHero :no="me.no" :label="me.label" :intro="me.intro" />

    <!-- ============ 每日持仓演进 ============ -->
    <template v-if="daily && days.length && firstDay && lastDay">
      <section class="compare-row">
        <div class="card card-pad compare-card">
          <p class="kpi-label">年初总资产（{{ firstDay.date }}）</p>
          <p class="compare-value serif-title num">{{ compactMoney(firstDay.totalAssets) }}</p>
          <p class="kpi-hint">{{ Object.keys(firstDay.holdings).length }} 个持仓标的</p>
        </div>
        <div class="card card-pad compare-card">
          <p class="kpi-label">当前总资产（{{ lastDay.date }}）</p>
          <p class="compare-value serif-title num">{{ compactMoney(lastDay.totalAssets) }}</p>
          <p class="kpi-hint">{{ Object.keys(lastDay.holdings).length }} 个持仓标的</p>
        </div>
        <div class="card card-pad compare-card">
          <p class="kpi-label">区间总资产变动</p>
          <p class="compare-value serif-title num">{{ formatMoney(stats.delta) }}</p>
          <p class="kpi-hint" :class="stats.delta >= 0 ? 'up' : 'down'">
            幅度 {{ formatPercent(Math.abs(stats.pct)) }}
          </p>
        </div>
        <div class="card card-pad compare-card">
          <p class="kpi-label">全年交易事件</p>
          <p class="compare-value serif-title">{{ stats.eventCount }} 笔</p>
          <p class="kpi-hint">{{ stats.dayCount }} 天 · 数据截至 {{ daily.endDate }}</p>
        </div>
      </section>

      <section class="card card-pad">
        <h3 class="section-title serif-title">总资产每日曲线</h3>
        <p class="section-hint">
          按交易记录重建每日持仓 × 当日收盘价 × 汇率（非交易日照用最近收盘价）
        </p>
        <EChart :option="assetOption" height="300px" :events="{ click: onChartClick }" />
      </section>

      <section class="card card-pad">
        <h3 class="section-title serif-title">各标的市值堆叠演进</h3>
        <p class="section-hint">点击图表任意日期，下方同步展示当日持仓明细</p>
        <EChart :option="stackOption" height="400px" :events="{ click: onChartClick }" />
      </section>

      <section class="card card-pad">
        <div class="day-head">
          <h3 class="section-title serif-title">当日持仓明细</h3>
          <span class="chip chip-gold">{{ selectedDate }}</span>
        </div>
        <p class="section-hint" v-if="selectedDay?.events?.length">
          当日交易：{{ selectedDay.events.join("；") }}
        </p>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>标的代码</th>
                <th class="num">持仓头寸</th>
                <th class="num">当日收盘价</th>
                <th class="num">汇率</th>
                <th class="num">折合人民币市值</th>
                <th class="num">占比</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in selectedRows" :key="row.code">
                <td>{{ row.code }}</td>
                <td class="num">{{ row.shares }} 股</td>
                <td class="num">{{ row.price }}</td>
                <td class="num">{{ row.fx }}</td>
                <td class="num">{{ compactMoney(row.mv) }}</td>
                <td class="num">{{ formatPercent((row.mv / (selectedDay?.totalAssets || 1)) * 100) }}</td>
              </tr>
            </tbody>
            <tfoot v-if="selectedDay">
              <tr>
                <td>合计</td>
                <td colspan="4" class="num">{{ compactMoney(selectedDay.totalAssets) }}</td>
                <td class="num">100.00%</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      <section class="card card-pad">
        <h3 class="section-title serif-title">2026 年持仓结构调整</h3>
        <p class="section-hint">年初（2026-01-01）与当前持仓头寸对比，基于每日持仓数据</p>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>标的代码</th>
                <th class="num">年初头寸</th>
                <th class="num">当前头寸</th>
                <th class="num">净变动</th>
                <th class="num">交易笔数</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in structureChange" :key="row.code">
                <td>{{ row.code }}</td>
                <td class="num">{{ row.start }} 股</td>
                <td class="num">{{ row.end }} 股</td>
                <td class="num" :class="row.delta > 0 ? 'up' : row.delta < 0 ? 'down' : ''">
                  {{ row.delta > 0 ? "+" : "" }}{{ row.delta }} 股
                </td>
                <td class="num">{{ row.trades }}</td>
                <td>
                  <span class="chip" :class="changeLabel(row).cls">{{ changeLabel(row).text }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card card-pad">
        <h3 class="section-title serif-title">月度轨迹</h3>
        <p class="section-hint">每月末总资产与环比变动</p>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>月份</th>
                <th class="num">月末总资产</th>
                <th class="num">环比变动</th>
                <th class="num">幅度</th>
                <th class="num">当月交易</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in monthlyTrajectory" :key="m.month">
                <td>{{ m.month }}</td>
                <td class="num">{{ compactMoney(m.endAssets) }}</td>
                <td class="num" :class="m.delta >= 0 ? 'up' : 'down'">
                  {{ m.delta >= 0 ? "+" : "" }}{{ compactMoney(m.delta) }}
                </td>
                <td class="num" :class="m.delta >= 0 ? 'up' : 'down'">
                  {{ m.delta >= 0 ? "+" : "" }}{{ formatPercent(Math.abs(m.pct)) }}
                </td>
                <td class="num">{{ m.events }} 笔</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card card-pad">
        <h3 class="section-title serif-title">2026 年交易事件</h3>
        <p class="section-hint">按交易记录逐笔还原（{{ eventList.length }} 笔）</p>
        <div class="event-list">
          <div v-for="(e, i) in eventList" :key="i" class="event-item">
            <span class="event-date">{{ e.date }}</span>
            <span class="event-text">{{ e.text }}</span>
          </div>
        </div>
      </section>
    </template>

    <div v-else class="card card-pad">
      <p class="kpi-label">每日持仓数据</p>
      <p class="compare-value serif-title">daily-holdings.json 不可用</p>
      <p class="kpi-hint">请先运行数据生成脚本</p>
    </div>

  </div>
</template>

<style scoped>
.history-page {
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

.compare-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}

.compare-value {
  font-size: 19px;
  color: var(--ink);
  margin: 4px 0;
}

.kpi-hint {
  font-size: 12px;
  color: var(--ink-faint);
  margin: 0;
}

.day-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 2px;
}

.table-wrap {
  overflow-x: auto;
}

.chip-live {
  color: var(--down);
  border-color: var(--down);
}

.chip-out {
  color: var(--up);
  border-color: var(--up);
}

.chip-hold {
  color: var(--ink-faint);
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 420px;
  overflow-y: auto;
  padding-right: 4px;
}

.event-item {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 5px 8px;
  border-radius: var(--radius-sm);
  background: var(--surface-tint);
  font-size: 13px;
}

.event-date {
  flex-shrink: 0;
  font-family: var(--font-serif);
  font-size: 12px;
  color: var(--gold-deep);
  font-variant-numeric: tabular-nums;
}

.event-text {
  color: var(--ink-soft);
}
</style>
