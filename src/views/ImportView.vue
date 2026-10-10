<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { usePortfolioStore } from "../stores/portfolio";
import type { ImportedResult } from "../lib/importEngine";

const store = usePortfolioStore();
const router = useRouter();

const csvText = ref("");
const fileName = ref("");
const preview = ref<ImportedResult | null>(null);
const parseError = ref<string | null>(null);
const dragOver = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const archiveInput = ref<HTMLInputElement | null>(null);

const persistBackendLabel = computed(() => {
  if (store.persistBackend === "indexeddb") return "IndexedDB";
  if (store.persistBackend === "localStorage") return "localStorage 兜底";
  return "未知";
});

const numberFormatter = new Intl.NumberFormat("zh-CN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
function formatMoney(v: number) {
  return `￥${numberFormatter.format(v)}`;
}
function compactMoney(v: number) {
  if (Math.abs(v) >= 100_000_000) return `￥${numberFormatter.format(v / 100_000_000)}亿`;
  if (Math.abs(v) >= 10_000) return `￥${numberFormatter.format(v / 10_000)}万`;
  return formatMoney(v);
}
function formatDateTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", { hour12: false });
}

const lastDay = computed(() => {
  const d = preview.value?.daily.days;
  if (!d || !d.length) return null;
  return d[d.length - 1];
});

const nameMap = computed(() => {
  const m: Record<string, string> = {};
  for (const r of preview.value?.portfolio.holdings ?? []) m[r.code] = r.name;
  return m;
});

const previewHoldings = computed(() => {
  const day = lastDay.value;
  if (!day) return [];
  return Object.entries(day.holdings)
    .map(([code, h]) => ({ code, name: nameMap.value[code] || code, ...h }))
    .sort((a, b) => b.mv - a.mv);
});

function pickFile() {
  fileInput.value?.click();
}
function onFile(e: Event) {
  const inp = e.target as HTMLInputElement;
  const f = inp.files?.[0];
  if (!f) return;
  fileName.value = f.name;
  const reader = new FileReader();
  reader.onload = () => {
    csvText.value = String(reader.result || "");
    parsePreview();
  };
  reader.readAsText(f);
}
function onDrop(e: DragEvent) {
  dragOver.value = false;
  const f = e.dataTransfer?.files?.[0];
  if (!f) return;
  fileName.value = f.name;
  const reader = new FileReader();
  reader.onload = () => {
    csvText.value = String(reader.result || "");
    parsePreview();
  };
  reader.readAsText(f);
}
function parsePreview() {
  parseError.value = null;
  preview.value = null;
  if (!csvText.value.trim()) {
    parseError.value = "请先选择文件或粘贴 CSV 内容";
    return;
  }
  void doParsePreview();
}

/** 解析前确保静态模板（内嵌行情）已加载，否则所有标的会被判为「缺行情」 */
async function doParsePreview() {
  if (!store.dailyTemplate) {
    await store.load();
  }
  try {
    preview.value = store.buildPreview(csvText.value, fileName.value || "粘贴内容.csv");
  } catch (err) {
    parseError.value = err instanceof Error ? err.message : "解析失败";
  }
}
async function apply() {
  if (!preview.value) return;
  // 等持久化完成再跳转，避免立即刷新时自动恢复读到旧存档
  const ok = await store.applyResult(preview.value, csvText.value);
  if (!ok) return; // 写入被拒绝时留在导入页，由告警卡片提示用户
  router.push("/");
}

function exportArchive() {
  const text = store.exportArchive();
  if (!text) return;
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `wealth-archive-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function pickArchive() {
  archiveInput.value?.click();
}

async function onArchive(e: Event) {
  const inp = e.target as HTMLInputElement;
  const f = inp.files?.[0];
  if (!f) return;
  parseError.value = null;
  try {
    const text = await f.text();
    const ok = await store.restoreArchive(text);
    if (ok) router.push("/");
  } catch (err) {
    parseError.value = err instanceof Error ? err.message : "存档恢复失败";
  } finally {
    inp.value = "";
  }
}
function clearImport() {
  store.clearImport();
  preview.value = null;
}

/* ============ 云端同步（Git 仓库当数据库） ============ */
const SYNC_EP_KEY = "family-wealth-sync/endpoint";
const SYNC_TK_KEY = "family-wealth-sync/token";

const syncEndpoint = ref(localStorage.getItem(SYNC_EP_KEY) || "");
const syncToken = ref(localStorage.getItem(SYNC_TK_KEY) || "");
const syncing = ref(false);
const syncOk = ref<string | null>(null);
const syncError = ref<string | null>(null);

async function syncToCloud() {
  syncOk.value = null;
  syncError.value = null;
  if (!csvText.value.trim()) {
    syncError.value = "请先载入 CSV 内容";
    return;
  }
  const endpoint = syncEndpoint.value.trim().replace(/\/+$/, "");
  if (!endpoint || !syncToken.value) {
    syncError.value = "请先填写同步地址与导入口令";
    return;
  }
  localStorage.setItem(SYNC_EP_KEY, endpoint);
  localStorage.setItem(SYNC_TK_KEY, syncToken.value);

  syncing.value = true;
  try {
    const res = await fetch(`${endpoint}/import`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Import-Token": syncToken.value,
      },
      body: JSON.stringify({ csv: csvText.value, fileName: fileName.value || "粘贴内容.csv" }),
    });
    const j = await res.json().catch(() => ({}));
    if (!res.ok || !j.ok) throw new Error(j.error || `HTTP ${res.status}`);
    syncOk.value = `已提交到仓库（${j.path}）。自动重建与部署约需 2–4 分钟，完成后所有设备打开站点即为最新数据。`;
  } catch (e) {
    syncError.value = e instanceof Error ? e.message : "同步失败";
  } finally {
    syncing.value = false;
  }
}
function exportJson() {
  if (!preview.value) return;
  const blob = new Blob([JSON.stringify(preview.value, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `import-${preview.value.meta.importedAt.slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <div class="import-page">
    <header class="page-head">
      <div>
        <p class="page-eyebrow">数据管理</p>
        <h1 class="page-title serif-title">数据导入</h1>
        <p class="page-sub">上传 DivTracker 导出的「adjusted」CSV，浏览器本地解析并刷新整份仪表盘，无需联网、无需等待。</p>
      </div>
    </header>

    <div v-if="store.isImported && store.importedMeta" class="active-banner">
      <span class="chip chip-gold">导入生效中</span>
      <span class="chip" :class="store.persistOk ? 'chip-saved' : 'chip-failed'">
        {{ store.persistOk ? `已存档 · ${persistBackendLabel}` : "未存档" }}
      </span>
      <span class="banner-text">
        当前展示为导入数据 · 来源 {{ store.importedMeta.fileName }} · 导入于
        {{ formatDateTime(store.importedMeta.importedAt) }}
      </span>
      <button class="btn" @click="clearImport">恢复静态数据</button>
    </div>

    <div v-if="store.persistStatus === 'failed'" class="card card-pad state-error">
      <h3 class="section-title serif-title">⚠ 本次导入没有写入浏览器存档</h3>
      <p class="section-hint">{{ store.persistMessage }}</p>
      <p class="section-hint">
        常见原因：无痕 / 隐私窗口、页面被嵌在 iframe 里、浏览器设置了阻止第三方存储、或站点域名刚变过（存档按域名隔离）。
        可以改在普通标签页打开后再导入，或先点下方「导出存档 JSON」保存，下次用「恢复存档」导入。
      </p>
      <div class="actions">
        <button class="btn" @click="exportArchive">导出存档 JSON</button>
      </div>
    </div>

    <!-- 上传区 -->
    <section class="card card-pad">
      <h3 class="section-title serif-title">① 上传 CSV</h3>
      <p class="section-hint">
        仅使用 <b>Ticker</b> / <b>Quantity (Adjusted)</b> / <b>Date</b> 三列；成本价与佣金不参与计算。
      </p>
      <div
        class="dropzone"
        :class="{ over: dragOver }"
        @click="pickFile"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
      >
        <p class="dz-icon">⤓</p>
        <p class="dz-title">点击选择文件，或将 CSV 拖拽到此处</p>
        <p class="dz-hint" v-if="fileName">已载入：{{ fileName }}</p>
        <input ref="fileInput" type="file" accept=".csv,text/csv" hidden @change="onFile" />
      </div>

      <p class="or-sep">或粘贴 CSV 文本</p>
      <textarea
        v-model="csvText"
        class="csv-area input"
        placeholder="Ticker,Quantity (Adjusted),Cost Per Share (Adjusted),Currency,Date,Commission,Commission Currency&#10;000660.KR,2.0,1850000.0,KRW,2026-07-16,4000.0,USD"
        rows="6"
      ></textarea>

      <div class="actions">
        <button class="btn btn-navy" @click="parsePreview">解析并预览</button>
      </div>
    </section>

    <div v-if="parseError" class="card card-pad state-error">{{ parseError }}</div>

    <!-- 预览 -->
    <template v-if="preview && preview.meta">
      <section class="card card-pad">
        <h3 class="section-title serif-title">② 解析概览</h3>
        <p class="section-hint">
          行情数据截至 <b>{{ preview.meta.priceAsOf }}</b>；{{ preview.meta.priceAsOf < preview.meta.lastTradeDate ? "8/15 之后市值按最近收盘价估算，可让助手刷新行情获取最新价。" : "估值所用行情为内嵌最新序列。" }}
        </p>
        <div class="kpi-row">
          <div class="kpi">
            <p class="kpi-label">当前总资产（{{ lastDay?.date }}）</p>
            <p class="kpi-value num">{{ compactMoney(lastDay?.totalAssets ?? 0) }}</p>
          </div>
          <div class="kpi">
            <p class="kpi-label">交易笔数</p>
            <p class="kpi-value num">{{ preview.meta.tradeCount }}</p>
            <p class="kpi-hint">{{ preview.meta.firstTradeDate }} ~ {{ preview.meta.lastTradeDate }}</p>
          </div>
          <div class="kpi">
            <p class="kpi-label">基线标的（截至 2025-12-31）</p>
            <p class="kpi-value num">{{ preview.meta.baselineCount }}</p>
          </div>
          <div class="kpi">
            <p class="kpi-label">当前持仓标的</p>
            <p class="kpi-value num">{{ preview.meta.holdingCount }}</p>
          </div>
        </div>
        <div v-if="preview.meta.warningCodes.length" class="warn-row">
          <span class="chip chip-warn">缺行情</span>
          <span class="warn-text">以下标的无内嵌行情，未计入市值：{{ preview.meta.warningCodes.join("、") }}</span>
        </div>
      </section>

      <section class="card card-pad">
        <h3 class="section-title serif-title">③ 当前持仓预览</h3>
        <p class="section-hint">基于最后一日持仓 × 当日收盘价 × 汇率（合并静态股息口径）· 预览仅用于核对，<b>需点击下方「应用到仪表盘」才会生效</b></p>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th class="num">头寸</th>
                <th class="num">收盘价</th>
                <th class="num">汇率</th>
                <th class="num">市值</th>
                <th class="num">仓位</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="h in previewHoldings" :key="h.code">
                <td>{{ h.code }}</td>
                <td>{{ h.name }}</td>
                <td class="num">{{ h.shares }} 股</td>
                <td class="num">{{ h.price }}</td>
                <td class="num">{{ h.fx }}</td>
                <td class="num">{{ compactMoney(h.mv) }}</td>
                <td class="num">
                  {{ lastDay ? ((h.mv / lastDay.totalAssets) * 100).toFixed(2) : "0.00" }}%
                </td>
              </tr>
            </tbody>
            <tfoot v-if="lastDay">
              <tr>
                <td>合计</td>
                <td colspan="4"></td>
                <td class="num">{{ compactMoney(lastDay.totalAssets) }}</td>
                <td class="num">100.00%</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      <section class="card card-pad apply-card">
        <h3 class="section-title serif-title">④ 应用到仪表盘</h3>
        <p class="section-hint">
          应用后，总览 / 持仓 / 股息 / 时间线 将全部切换到这份导入数据，并写入<b>本浏览器的本地存档</b>（重新打开自动恢复）。
          存档按域名隔离，换设备 / 换浏览器 / 换域名都不会跟着走；需要长期固定请用「导出存档 JSON」或下方第⑤步云端同步。
        </p>
        <div class="actions">
          <button class="btn btn-gold" @click="apply">应用到仪表盘</button>
          <button class="btn" @click="exportJson">导出计算结果 JSON</button>
          <button class="btn" @click="exportArchive">导出存档 JSON</button>
          <button class="btn" @click="pickArchive">恢复存档 JSON</button>
        </div>
        <input ref="archiveInput" type="file" accept=".json,application/json" hidden @change="onArchive" />
      </section>

      <section class="card card-pad">
        <h3 class="section-title serif-title">⑤ 同步到云端（跨设备持久化）</h3>
        <p class="section-hint">
          把这份 CSV 原文提交到 GitHub 仓库 <b>data/inbox/</b>，自动触发行情抓取、数据重算与站点部署；
          2–4 分钟后所有设备打开站点即为最新数据。此步骤独立于第④步，不应用也可直接同步。
          首次使用需按 <b>DEPLOY-CLOUD.md</b> 部署同步代理并配置地址与口令。
        </p>
        <div class="sync-cfg">
          <input
            v-model="syncEndpoint"
            class="input sync-input"
            type="url"
            placeholder="同步代理地址，如 https://api.example.com"
            spellcheck="false"
          />
          <input
            v-model="syncToken"
            class="input sync-input"
            type="password"
            placeholder="导入口令"
            autocomplete="off"
          />
        </div>
        <div class="actions">
          <button class="btn btn-navy" :disabled="syncing || !preview" @click="syncToCloud">
            {{ syncing ? "提交中…" : "同步 CSV 到云端" }}
          </button>
        </div>
        <p v-if="syncOk" class="sync-ok">{{ syncOk }}</p>
        <p v-if="syncError" class="sync-err">{{ syncError }}</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.import-page {
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

.page-eyebrow {
  font-size: 11px;
  font-weight: 500;
  color: var(--gold-deeper);
  margin: 0 0 4px;
  letter-spacing: 0.06em;
}

.page-title {
  font-size: 26px;
  color: var(--ink);
  margin: 0;
}

.page-sub {
  font-size: 12px;
  color: var(--ink-faint);
  margin: 4px 0 0;
  max-width: 640px;
}

.active-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  background: var(--surface-tint);
  border: 0.5px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
}

.banner-text {
  font-size: 12.5px;
  color: var(--ink-soft);
  flex: 1;
  min-width: 200px;
}

.dropzone {
  margin-top: 12px;
  border: 1.5px dashed var(--line);
  border-radius: var(--radius-lg);
  padding: 28px 16px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.dropzone:hover,
.dropzone.over {
  border-color: var(--gold-deep);
  background: var(--surface-tint);
}

.dz-icon {
  font-size: 28px;
  color: var(--gold-deep);
  margin: 0 0 6px;
}

.dz-title {
  font-size: 13px;
  color: var(--ink-soft);
  margin: 0;
}

.dz-hint {
  font-size: 12px;
  color: var(--gold-deeper);
  margin: 6px 0 0;
}

.or-sep {
  font-size: 12px;
  color: var(--ink-faint);
  text-align: center;
  margin: 14px 0 8px;
}

.csv-area {
  width: 100%;
  resize: vertical;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  line-height: 1.5;
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-top: 14px;
}

.kpi {
  background: var(--surface-tint);
  border-radius: var(--radius-md);
  padding: 12px 14px;
}

.kpi-hint {
  font-size: 12px;
  color: var(--ink-faint);
  margin: 2px 0 0;
}

.warn-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.warn-text {
  font-size: 12.5px;
  color: var(--up);
}

.chip-warn {
  color: var(--up);
  border-color: var(--up);
  background: transparent;
}

.chip-saved {
  color: var(--down);
  border-color: var(--down);
  background: transparent;
}

.chip-failed {
  color: var(--up);
  border-color: var(--up);
  background: transparent;
}

.state-error .section-title {
  color: var(--up);
  margin-bottom: 6px;
}

.table-wrap {
  overflow-x: auto;
  margin-top: 12px;
}

.apply-card {
  background: var(--navy);
  border-color: var(--navy);
}

.apply-card .section-title {
  color: #f3ebdd;
}

.apply-card .section-hint {
  color: #9fb3c8;
}

.state-error {
  color: var(--up);
  border-color: var(--up);
}

.sync-cfg {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 10px;
  margin-top: 12px;
}

.sync-input {
  width: 100%;
  font-size: 12.5px;
}

.sync-ok {
  margin: 10px 0 0;
  font-size: 12.5px;
  color: var(--down);
}

.sync-err {
  margin: 10px 0 0;
  font-size: 12.5px;
  color: var(--up);
}

@media (max-width: 640px) {
  .sync-cfg {
    grid-template-columns: 1fr;
  }
}
</style>
