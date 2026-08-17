<script setup lang="ts">
import { computed, onMounted } from "vue";
import { usePortfolioStore } from "../stores/portfolio";
import ChapterHero from "../components/ChapterHero.vue";
import { chapters } from "../lib/chapters";

const store = usePortfolioStore();
const me = chapters[4];

onMounted(async () => {
  await store.load();
});

const summary = computed(() => [
  { label: "数据日期", value: store.dataDate ?? "最新" },
  { label: "持仓标的", value: `${store.rows.length} 个` },
]);

const fxInfo = [
  { pair: "USD/CNY", desc: "美股 + BYTE 估值口径" },
  { pair: "HKD/CNY", desc: "港股估值口径" },
  { pair: "EUR/CNY", desc: "690D.DE 估值口径" },
  { pair: "KRW/CNY", desc: "000660.KS 估值口径" },
];

const dataSources = [
  { name: "Yahoo Finance", desc: "美股、港股、韩股、D 股行情与股息" },
  { name: "Deutsche Börse Live", desc: "690D.DE 首选官方行情（XETR）" },
  { name: "中国货币网 / CFETS", desc: "人民币中间价汇率" },
  { name: "用户固定口径", desc: "BYTE 229.5 USD/股，无分红" },
];

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

function exportJson() {
  const blob = new Blob([JSON.stringify(
    {
      date: store.dataDate,
      rows: store.holdingRows.map((r) => ({
        序号: r.sequence || String(store.holdingRows.indexOf(r) + 1),
        标的代码: r.code,
        标的全称: r.name,
        持仓头寸: r.position,
        折合人民币市值: r.marketValue.toFixed(2),
        仓位占比: `${r.weight.toFixed(2)}%`,
        "过去12个月每股已派发股息（原生币种）": r.dividendPerShare,
        适用股息税率: `${r.taxRate}%`,
        "税前总股息（人民币）": r.grossDividend.toFixed(2),
        "应缴股息税（人民币）": r.dividendTax.toFixed(2),
        "税后到手股息（人民币）": r.netDividend.toFixed(2),
        "税后股息贡献占比": `${r.dividendContribution.toFixed(2)}%`,
        "官方数据来源": r.source,
      })),
    },
    null,
    2,
  )], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `portfolio-${store.dataDate ?? "latest"}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <div class="archive-page">
    <ChapterHero :no="me.no" :label="me.label" :intro="me.intro" />

    <section class="card card-pad">
      <h3 class="section-title serif-title">汇率口径</h3>
      <p class="section-hint">不同币种资产使用对应的汇率换算人民币</p>
      <div class="info-grid">
        <div v-for="fx in fxInfo" :key="fx.pair" class="info-item">
          <span class="info-key">{{ fx.pair }}</span>
          <span class="info-desc">{{ fx.desc }}</span>
        </div>
      </div>
    </section>

    <section class="card card-pad">
      <h3 class="section-title serif-title">数据来源</h3>
      <p class="section-hint">行情与股息均来自已核实的官方 / 权威渠道</p>
      <div class="info-grid">
        <div v-for="src in dataSources" :key="src.name" class="info-item">
          <span class="info-key">{{ src.name }}</span>
          <span class="info-desc">{{ src.desc }}</span>
        </div>
      </div>
    </section>

    <section class="card card-pad">
      <h3 class="section-title serif-title">导出数据</h3>
      <p class="section-hint">导出当前持仓快照，便于留存或导入其他工具</p>
      <div class="btn-row">
        <button class="btn btn-navy" @click="exportCsv">导出 CSV</button>
        <button class="btn" @click="exportJson">导出 JSON</button>
        <button class="btn" @click="store.load()">刷新行情</button>
      </div>
    </section>

    <section class="card card-pad">
      <h3 class="section-title serif-title">系统信息</h3>
      <div class="info-grid">
        <div v-for="item in summary" :key="item.label" class="info-item">
          <span class="info-key">{{ item.label }}</span>
          <span class="info-desc">{{ item.value }}</span>
        </div>
      </div>
    </section>

    <section class="card card-pad">
      <h3 class="section-title serif-title">数据维护说明</h3>
      <p class="section-hint">
        持仓变动一律以用户提供的交易记录文档为准（提供新文档后重新生成每日持仓）；
        市值 / 股价 / 汇率在刷新时从网上获取。已取消历史快照归档与定时回溯。
      </p>
    </section>
  </div>
</template>

<style scoped>
.archive-page {
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

.section-title {
  margin-bottom: 4px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 14px;
  border: 0.5px solid var(--line-soft);
  border-radius: var(--radius-md);
  background: var(--surface-tint);
}

.info-key {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink);
}

.info-desc {
  font-size: 12px;
  color: var(--ink-faint);
}

.btn-row {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  flex-wrap: wrap;
}
</style>
