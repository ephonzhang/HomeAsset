<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import ThemeToggle from "./ThemeToggle.vue";
import { chapters } from "../lib/chapters";

const route = useRoute();

const activeIndex = computed(() => {
  const idx = chapters.findIndex((item) => route.path === item.to);
  return idx === -1 ? 0 : idx;
});
</script>

<template>
  <header class="site-header">
    <!-- 第一行：顶部品牌区（视觉锚点） -->
    <div class="brand-bar">
      <div class="brand-inner">
        <router-link to="/" class="brand-block">
          <span class="brand-logo">家</span>
          <span class="brand-text">
            <span class="brand-title serif-title">家庭财富报告</span>
            <span class="brand-sub">2026 年 8 月 · 第 3 期</span>
          </span>
        </router-link>
        <div class="brand-actions">
          <ThemeToggle />
        </div>
      </div>
    </div>

    <!-- 第二行：章节导航（tabs 等宽，bar 精准对齐） -->
    <nav class="chapter-nav">
      <div class="nav-inner">
        <div class="nav-tabs">
          <router-link
            v-for="(item, i) in chapters"
            :key="item.to"
            :to="item.to"
            class="nav-tab"
            :class="{ active: i === activeIndex }"
            :aria-label="item.label"
          >
            <span class="nav-label">{{ item.label }}</span>
          </router-link>
          <span class="nav-active-bar" :style="{ transform: `translateX(${activeIndex * 100}%)` }" />
        </div>
      </div>
    </nav>
  </header>
</template>

<style scoped>
.site-header {
  width: 100%;
  background: var(--paper);
}

/* ===== 品牌区 ===== */
.brand-bar {
  background: var(--navy);
}

.brand-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 14px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
}

.brand-logo {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--gold);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 500;
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.brand-title {
  font-size: 19px;
  color: #f3ebdd;
  letter-spacing: 0.02em;
  line-height: 1.25;
}

.brand-sub {
  font-size: 11px;
  color: #9fb3c8;
  line-height: 1.3;
}

.brand-actions {
  flex-shrink: 0;
}

.brand-actions :deep(.theme-toggle) {
  background: transparent;
  border-color: rgba(243, 235, 221, 0.25);
  color: #f3ebdd;
}

.brand-actions :deep(.theme-toggle:hover) {
  background: rgba(243, 235, 221, 0.1);
  color: #fff;
}

/* ===== 章节导航（第二行）：tabs 等宽、bar 精准对齐 ===== */
.chapter-nav {
  border-bottom: 0.5px solid var(--line);
}

.nav-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 28px;
}

.nav-tabs {
  position: relative;
  display: flex;
  align-items: stretch;
  height: 50px;
}

.nav-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  color: var(--ink-faint);
  transition: color 0.15s ease;
  white-space: nowrap;
  height: 100%;
}

.nav-tab:hover {
  color: var(--ink-soft);
}

.nav-tab.active {
  color: var(--ink);
}

.nav-label {
  font-size: 13.5px;
  font-weight: 500;
}

.nav-active-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 20%; /* 5 等分之一的 tab 宽度，flex 1 平分 */
  height: 2.5px;
  border-radius: 2px;
  background: var(--gold);
  transition: transform 0.32s cubic-bezier(0.16, 1, 0.3, 1);
  pointer-events: none;
}

/* ===== 移动端：品牌区隐藏，导航固定在底部 ===== */
@media (max-width: 767px) {
  .brand-bar {
    display: none;
  }

  .chapter-nav {
    position: fixed;
    bottom: 0;
    top: auto;
    left: 0;
    right: 0;
    background: var(--surface);
    border-top: 0.5px solid var(--line);
    z-index: 40;
  }

  .nav-tab {
    flex-direction: column;
    gap: 1px;
    font-size: 11px;
  }

  .nav-label {
    font-size: 11px;
  }

  .nav-active-bar {
    bottom: auto;
    top: 0;
    height: 2px;
  }
}
</style>