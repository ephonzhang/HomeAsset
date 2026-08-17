<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch, nextTick } from "vue";
import * as echarts from "echarts/core";
import { BarChart, LineChart, PieChart, TreemapChart, GaugeChart, SunburstChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DatasetComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  TreemapChart,
  GaugeChart,
  SunburstChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DatasetComponent,
  CanvasRenderer,
]);

const props = defineProps<{
  option: echarts.EChartsCoreOption;
  height?: string;
  events?: Record<string, (params: any) => void>;
}>();

const el = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;
let observer: ResizeObserver | null = null;

function render() {
  if (chart && props.option) {
    chart.setOption(props.option, true);
  }
}

function bindEvents() {
  if (!chart || !props.events) return;
  Object.entries(props.events).forEach(([name, handler]) => {
    chart?.on(name, handler);
  });
}

onMounted(async () => {
  await nextTick();
  if (!el.value) return;
  chart = echarts.init(el.value);
  render();
  bindEvents();
  observer = new ResizeObserver(() => chart?.resize());
  observer.observe(el.value);
});

watch(
  () => props.option,
  () => render(),
  { deep: true },
);

onBeforeUnmount(() => {
  observer?.disconnect();
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div ref="el" class="echart" :style="{ height: height || '300px' }" />
</template>

<style scoped>
.echart {
  width: 100%;
  min-height: 200px;
}
</style>
