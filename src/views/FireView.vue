<script setup lang="ts">
import { computed, onMounted } from "vue";
import { usePortfolioStore } from "../stores/portfolio";
import EChart from "../components/EChart.vue";
import ChapterHero from "../components/ChapterHero.vue";
import { chapters } from "../lib/chapters";

const store = usePortfolioStore();
const me = chapters[4]; // 05 生活方案

onMounted(async () => {
  await store.load();
});

/* ============ 家况前提 ============ */
const premise = [
  { text: "坐标 · 天津", gold: true },
  { text: "住房 · 无房，长租" },
  { text: "用车 · 2 万/年" },
  { text: "孩子 · 6 岁" },
  { text: "口径 · 收入全部用于生活，无储蓄", gold: true },
];

/* ============ 三档预算数据（元/月） ============ */
type BudgetRow = {
  item: string;
  sub: string;
  values: [number, number, number]; // 40万 / 60万 / 100万
};

const budgetRows: BudgetRow[] = [
  { item: "住房（长租）", sub: "精装三居 → 品质三居 → 大平层", values: [6000, 10000, 18000] },
  { item: "日常开销", sub: "吃穿用 + 养车 2万/年 + 人情", values: [15000, 18000, 24000] },
  { item: "孩子教育", sub: "公立 → 民办 → 国际学校", values: [5000, 9000, 18000] },
  { item: "保险医疗", sub: "百万医疗 → 中端 → 高端直付", values: [3000, 5000, 12000] },
  { item: "旅游娱乐", sub: "国内长线 → 出境 → 年 3–4 次", values: [4300, 8000, 11300] },
];

const tiers = [
  { label: "40 万 / 年", monthly: 33300, color: "#4a6b8a" },
  { label: "60 万 / 年", monthly: 50000, color: "#c9a96a" },
  { label: "100 万 / 年", monthly: 83300, color: "#c0392b" },
];

const numberFormatter = new Intl.NumberFormat("zh-CN");

function fmt(value: number) {
  return numberFormatter.format(value);
}

function fmtWan(value: number) {
  return `${numberFormatter.format(Math.round(value / 10000))} 万`;
}

/* ============ 月度结构（ECharts 堆叠条形图） ============ */
const segColors = ["#8fa9bf", "#c3d2de", "#4a6b8a", "#c9a96a", "#e3d5b8"];
const segLabelDark = ["#16324a", "#16324a", "#f3ebdd", "#ffffff", "#16324a"];

/* 档位月总额：bar 系列 tooltip 不自带 percent，需按档位合计实时计算 */
const tierTotalByName: Record<string, number> = {
  "40 万 / 年": tiers[0].monthly,
  "60 万 / 年": tiers[1].monthly,
  "100 万 / 年": tiers[2].monthly,
};

const barsOption = computed(() => ({
  tooltip: {
    trigger: "item",
    formatter: (p: any) => {
      const total = tierTotalByName[p.name] ?? 0;
      const pct = total ? ((p.value / total) * 100).toFixed(1) : "0.0";
      return `${p.seriesName} · ${p.name}<br/>${fmt(p.value)} 元/月（${pct}%）`;
    },
  },
  legend: {
    bottom: 0,
    itemWidth: 10,
    itemHeight: 10,
    itemGap: 14,
    textStyle: { fontSize: 11, color: "#8c94a0" },
  },
  grid: { left: 8, right: 30, top: 10, bottom: 34, containLabel: true },
  xAxis: { type: "value", show: false, max: 86000 },
  yAxis: {
    type: "category",
    data: ["100 万 / 年", "60 万 / 年", "40 万 / 年"],
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: "#5c6570", fontSize: 12 },
  },
  series: budgetRows.map((row, i) => ({
    name: row.item,
    type: "bar",
    stack: "budget",
    barWidth: 22,
    itemStyle: { color: segColors[i] },
    label: {
      show: true,
      position: "inside",
      fontSize: 10,
      color: segLabelDark[i],
      formatter: (p: any) => (p.value >= 4000 ? `${(p.value / 1000).toFixed(1)}k` : ""),
    },
    data: [
      row.values[2],
      row.values[1],
      row.values[0],
    ],
  })),
}));

/* ============ 三档生活画面 ============ */
const scenes = [
  {
    tag: "TIER 40",
    cls: "",
    title: "从容但需选择",
    kw: "关键词 · 公立路线 / 精致克制",
    text: "好地段精装三居，下馆子不看价，换设备不纠结。公立学校 + 3–4 个兴趣班，年 2 次国内长线游。",
    points: ["够不着：国际化教育、高端医疗", "分水岭：学区房租金 vs 旅游预算"],
  },
  {
    tag: "TIER 60",
    cls: "g2",
    title: "宽裕自由线",
    kw: "关键词 · 不再做选择题",
    text: "和平 / 水上 / 梅江品质三居，民办双语可选，年 2–3 次出行含一次出境。多数日常决定不再权衡。",
    points: ["边际改善最大的一档（推荐）", "用车完全无压力，可规划换车"],
  },
  {
    tag: "TIER 100",
    cls: "g3",
    title: "服务体系化",
    kw: "关键词 · 买回时间与省心",
    text: "200㎡+ 大平层、国际学校全覆盖、高端医疗直付、阿姨与说走就走。钱花不完的边际是买「时间」。",
    points: ["≈ 北上深 200 万+ 的生活水准", "隐性圈层消费成本上升"],
  },
];

/* ============ FIRE 本金刻度 ============ */
/* 目标本金 = 年支出 ÷ 支取率：4% 法则（25 倍）与 3% 保守（33.3 倍）；进度按 3% 口径 */
const fireTargets = [
  { label: "40 万档", income: 40, rule4: 10_000_000, rule3: 13_330_000, color: "#4a6b8a" },
  { label: "60 万档", income: 60, rule4: 15_000_000, rule3: 20_000_000, color: "#c9a96a" },
  { label: "100 万档", income: 100, rule4: 25_000_000, rule3: 33_330_000, color: "#c0392b" },
];

/** 进度 = 当前组合市值 ÷ 3% 口径目标本金（随每日快照更新） */
const progress = computed(() => {
  const total = store.totalAssets;
  return fireTargets.map((t) => ({
    ...t,
    pct: total > 0 ? Math.min((total / t.rule3) * 100, 100) : 0,
    total,
  }));
});

const hasPortfolio = computed(() => store.totalAssets > 0);

const decisions = [
  {
    title: "住房",
    vs: "长租 vs 购置",
    text: "天津改善三居约 300–500 万，房租回报率仅 1.5–2%。纯财务角度长租优于购房；若未来购房，目标本金需整体上移一档（本金被切走 1/3）。",
  },
  {
    title: "教育路线",
    vs: "公立 → 民办 → 国际",
    text: "三档之间最大的分水岭。孩子 6 岁是决策窗口：40 万锚定公立，60 万解锁民办可选，100 万国际路线自由选择。此项权重建议置于住房之上。",
  },
];
</script>

<template>
  <div class="fire-page">
    <ChapterHero :no="me.no" :label="me.label" :intro="me.intro">
      <template #actions>
        <span class="fire-date">{{ store.dataDate ? `数据日期 ${store.dataDate}` : "最新数据" }}</span>
      </template>
    </ChapterHero>

    <!-- 家况前提 -->
    <div class="premise">
      <span v-for="p in premise" :key="p.text" class="chip" :class="{ 'chip-gold': p.gold }">{{ p.text }}</span>
    </div>

    <!-- 三档预算对照 -->
    <section class="section">
      <div class="section-hd">
        <h3 class="section-title serif-title">三档月度预算对照</h3>
        <p class="section-hint">单位：元 / 月 · 全部收入转为生活支出</p>
      </div>
      <div class="card">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 24%">项目</th>
              <th v-for="t in tiers" :key="t.label">
                <span class="tier-head">
                  <span class="tier-dot" :style="{ background: t.color }" />
                  <span>{{ t.label }}<span class="tier-sub">月均 {{ fmt(t.monthly) }}</span></span>
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in budgetRows" :key="row.item">
              <td class="item-name">{{ row.item }}<span class="item-sub">{{ row.sub }}</span></td>
              <td v-for="(v, i) in row.values" :key="i" class="num">{{ fmt(v) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td>合计</td>
              <td v-for="t in tiers" :key="t.label" class="num">{{ fmt(t.monthly) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>

    <!-- 月度结构 -->
    <section class="section">
      <div class="section-hd">
        <h3 class="section-title serif-title">月度结构对比</h3>
        <p class="section-hint">各档内部支出构成（元 / 月）</p>
      </div>
      <div class="card card-pad">
        <EChart :option="barsOption" height="280px" />
      </div>
    </section>

    <!-- 三档生活画面 -->
    <section class="section">
      <div class="section-hd">
        <h3 class="section-title serif-title">三档生活画面</h3>
        <p class="section-hint">每一档的关键词与它真正买到的体验</p>
      </div>
      <div class="scenes">
        <div v-for="s in scenes" :key="s.tag" class="scene card card-pad" :class="s.cls">
          <span class="scene-tag">{{ s.tag }}</span>
          <h4 class="serif-title">{{ s.title }}</h4>
          <p class="scene-kw">{{ s.kw }}</p>
          <p class="scene-text">{{ s.text }}</p>
          <ul>
            <li v-for="pt in s.points" :key="pt">{{ pt }}</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- FIRE 本金刻度 -->
    <section class="section">
      <div class="section-hd">
        <h3 class="section-title serif-title">FIRE 本金刻度</h3>
        <p class="section-hint">左侧为三档所需本金，右侧为组合市值进度（按 3% 保守口径，随每日快照自动更新）</p>
      </div>
      <div class="fire-grid">
        <div class="card">
          <table class="table">
            <thead>
              <tr><th>年支出档位</th><th>4% 法则</th><th>3% 保守</th></tr>
            </thead>
            <tbody>
              <tr v-for="t in fireTargets" :key="t.label">
                <td>{{ t.label }}</td>
                <td class="num">{{ fmtWan(t.rule4) }}</td>
                <td class="num">{{ fmtWan(t.rule3) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="card card-pad">
          <div v-for="p in progress" :key="p.label" class="progress-item">
            <div class="progress-hd">
              <span>{{ p.label }} · {{ fmtWan(p.rule3) }}</span>
              <span class="progress-pct num" :style="{ color: p.color }">{{ hasPortfolio ? p.pct.toFixed(1) + "%" : "—" }}</span>
            </div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: `${p.pct}%`, background: p.color }" />
            </div>
          </div>
          <p class="progress-note">
            {{ hasPortfolio
              ? `按当前组合市值 ${fmtWan(store.totalAssets)} 计算`
              : "等待持仓数据加载..." }}
          </p>
        </div>
      </div>
    </section>

    <!-- 决策变量 -->
    <section class="section">
      <div class="section-hd">
        <h3 class="section-title serif-title">两个决策变量</h3>
        <p class="section-hint">影响刻度换算的两个前置选择</p>
      </div>
      <div class="decisions">
        <div v-for="d in decisions" :key="d.title" class="card card-pad">
          <h4>{{ d.title }} <span class="vs">{{ d.vs }}</span></h4>
          <p class="decision-text">{{ d.text }}</p>
        </div>
      </div>
    </section>

    <div class="footnote">
      口径说明：预算为纯消费口径（无储蓄），车险、学费、旅游等年度大项按月摊入；三档数据与 2026-08-30 生活方案结论一致，参数可在档案页调整。
    </div>
  </div>
</template>

<style scoped>
.fire-page {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.fire-date {
  font-size: 12px;
  color: var(--ink-faint);
}

/* ---- 家况前提 ---- */
.premise {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

/* ---- 区块 ---- */
.section-hd {
  margin-bottom: 12px;
}

/* ---- 预算表 ---- */
.tier-head {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.tier-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  display: inline-block;
  flex-shrink: 0;
}

.tier-sub {
  display: block;
  font-size: 11px;
  font-weight: 400;
  color: var(--ink-faint);
}

th .tier-sub {
  color: inherit;
  opacity: 0.75;
}

.item-name {
  color: var(--ink);
}

.item-sub {
  display: block;
  font-size: 11px;
  color: var(--ink-faint);
  white-space: normal;
}

/* ---- 生活画面 ---- */
.scenes {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.scene {
  position: relative;
  margin-top: 10px;
}

.scene-tag {
  position: absolute;
  top: 0;
  left: 1.25rem;
  transform: translateY(-50%);
  font-size: 11px;
  letter-spacing: 0.08em;
  padding: 2px 10px;
  border-radius: 4px;
  background: var(--navy);
  color: #f3ebdd;
}

.scene.g2 .scene-tag {
  background: var(--gold-deep);
  color: #fff;
}

.scene.g3 .scene-tag {
  background: var(--up);
  color: #fff;
}

.scene h4 {
  margin: 6px 0 2px;
  font-size: 16px;
}

.scene-kw {
  font-size: 12px;
  color: var(--gold-deeper);
  margin: 0 0 10px;
}

.scene-text {
  font-size: 13px;
  color: var(--ink-soft);
  margin: 0 0 12px;
}

.scene ul {
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 0.5px solid var(--line-soft);
  padding-top: 10px;
}

.scene li {
  font-size: 12px;
  color: var(--ink-soft);
  padding: 3px 0;
  display: flex;
  gap: 8px;
}

.scene li::before {
  content: "—";
  color: var(--gold);
  flex-shrink: 0;
}

/* ---- FIRE 刻度 ---- */
.fire-grid {
  display: grid;
  grid-template-columns: 1.25fr 1fr;
  gap: 14px;
}

.progress-item {
  margin-bottom: 14px;
}

.progress-item:last-of-type {
  margin-bottom: 0;
}

.progress-hd {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 13px;
  margin-bottom: 6px;
}

.progress-pct {
  font-size: 12px;
  font-weight: 500;
}

.progress-track {
  height: 8px;
  background: var(--surface-tint);
  border-radius: 999px;
  overflow: hidden;
  border: 0.5px solid var(--line-soft);
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.progress-note {
  font-size: 11px;
  color: var(--ink-faint);
  margin: 12px 0 0;
}

/* ---- 决策变量 ---- */
.decisions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.decisions h4 {
  margin: 0 0 6px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.vs {
  font-size: 11px;
  color: var(--ink-faint);
  border: 0.5px dashed var(--gold);
  border-radius: 4px;
  padding: 1px 6px;
  font-weight: 400;
}

.decision-text {
  font-size: 13px;
  color: var(--ink-soft);
  margin: 0;
}

.footnote {
  font-size: 12px;
  color: var(--ink-faint);
  border-top: 0.5px solid var(--line);
  padding-top: 14px;
  margin-top: 6px;
}

/* ---- 响应式 ---- */
@media (max-width: 900px) {
  .scenes {
    grid-template-columns: 1fr;
  }

  .fire-grid,
  .decisions {
    grid-template-columns: 1fr;
  }
}
</style>
