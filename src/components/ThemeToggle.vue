<script setup lang="ts">
import { ref, watch, onMounted } from "vue";

const isDark = ref(false);

function applyTheme(dark: boolean) {
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  localStorage.setItem("theme", dark ? "dark" : "light");
}

onMounted(() => {
  const saved = localStorage.getItem("theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  isDark.value = saved ? saved === "dark" : prefersDark;
  applyTheme(isDark.value);
});

watch(isDark, (val) => applyTheme(val));
</script>

<template>
  <button class="theme-toggle" @click="isDark = !isDark" :aria-label="isDark ? '切换到亮色主题' : '切换到暗色主题'">
    <svg v-if="!isDark" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
    <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </svg>
    <span>{{ isDark ? "深色" : "浅色" }}</span>
  </button>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0.5px solid var(--line);
  background: var(--surface);
  color: var(--ink-soft);
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.theme-toggle:hover {
  background: var(--surface-hover);
  color: var(--ink);
}
</style>
