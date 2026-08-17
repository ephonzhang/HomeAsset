import { createRouter, createWebHashHistory } from "vue-router";

const routes = [
  { path: "/", name: "overview", component: () => import("../views/OverviewView.vue"), meta: { title: "总览" } },
  { path: "/holdings", name: "holdings", component: () => import("../views/HoldingsView.vue"), meta: { title: "持仓明细" } },
  { path: "/dividend", name: "dividend", component: () => import("../views/DividendView.vue"), meta: { title: "股息分析" } },
  { path: "/history", name: "history", component: () => import("../views/HistoryView.vue"), meta: { title: "历史趋势" } },
  { path: "/settings", name: "settings", component: () => import("../views/SettingsView.vue"), meta: { title: "设置" } },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
