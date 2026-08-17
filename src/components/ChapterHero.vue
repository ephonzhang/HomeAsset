<script setup lang="ts">
defineProps<{
  no: string;
  label: string;
  intro: string;
  actions?: boolean;
}>();
</script>

<template>
  <section class="chapter-hero">
    <div class="hero-meta">
      <span class="hero-eyebrow">第 {{ no }} 章</span>
      <h1 class="hero-title serif-title">{{ label }}</h1>
      <p class="hero-intro">{{ intro }}</p>
    </div>
    <div v-if="actions" class="hero-actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<style scoped>
.chapter-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 0 0 18px;
  margin-bottom: 6px;
  border-bottom: 0.5px solid var(--line);
  flex-wrap: wrap;
}

.hero-meta {
  flex: 1;
  min-width: 0;
}

.hero-eyebrow {
  display: inline-block;
  font-size: 11px;
  font-weight: 500;
  color: var(--gold-deeper);
  letter-spacing: 0.08em;
  padding: 2px 8px;
  background: var(--gold-soft, #f3ebdd);
  border-radius: 4px;
  margin-bottom: 8px;
}

.hero-title {
  font-size: 26px;
  color: var(--ink);
  margin: 0 0 4px;
  letter-spacing: 0.01em;
}

.hero-intro {
  font-size: 13px;
  color: var(--ink-faint);
  margin: 0;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
</style>