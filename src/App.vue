<script setup lang="ts">
import { computed, onMounted } from "vue";
import AppSidebar from "./components/AppSidebar.vue";
import ThemeToggle from "./components/ThemeToggle.vue";
import { usePortfolioStore } from "./stores/portfolio";
import { formatDataDate } from "./lib/portfolioData";

const store = usePortfolioStore();

// 顶栏日期 = 数据日期（portfolio.json 的 date，即最近一次数据落库/上传时间）
const dataDateLabel = computed(() => (store.dataDate ? formatDataDate(store.dataDate) : "最新数据"));

onMounted(() => {
  if (!store.dataDate) store.load();
});
</script>

<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-main">
      <header class="app-topbar">
        <p class="topbar-date">家庭财富报告 · {{ dataDateLabel }}</p>
        <ThemeToggle />
      </header>
      <main class="app-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.app-topbar {
  display: none;
}

.app-content {
  flex: 1;
  width: 100%;
  max-width: 1440px;
  margin: 0 auto;
  padding: 28px 28px 48px;
}

@media (max-width: 767px) {
  .app-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    position: sticky;
    top: 0;
    z-index: 30;
    background: var(--paper);
    border-bottom: 0.5px solid var(--line);
  }

  .topbar-date {
    font-family: var(--font-serif);
    font-size: 13px;
    color: var(--ink);
    margin: 0;
  }

  .app-content {
    padding: 16px 14px 84px;
  }
}
</style>