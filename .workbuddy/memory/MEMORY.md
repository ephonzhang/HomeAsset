# 家庭财产统计 · 长期记忆

## 持仓数据权威来源
持仓明细（标的代码、名称、数量、股息税率、BYTE 价格、汇率口径）以
`~/.workbuddy/skills/portfolio-dividend-dashboard/references/portfolio_rules.md` 为准。
任何刷新总表/仪表盘的操作，先读该文件，再改。非用户明确指示不得改固定持仓。

## 当前组合（2026-08-15 起）
12 项：QQQM 5000、VOO 700、QNDX 14330、BITB 3000、IYW 1500、CGDV 1500、
SMH 60、000660.KS 10、690D.DE 30000、0883.HK 30000、0700.HK 1500、BYTE 171。
已清仓：GPIQ、QQQI。

## 前端实现
- 2026-08-15 起仪表盘改为 **Vue 3 + Vite + TS + Pinia + ECharts**（替代 React+Tailwind+Recharts），
  项目位于本工作区根目录（/Users/zhangyifeng/WorkBuddy/家庭财产统计/），数据契约仍为 public/data/portfolio.json。
- 依赖安装必须走 `--registry=https://registry.npmmirror.com`（npmjs 在沙箱内不可达）。
- 2026-08-15 第二版改造为「家庭财富报告」纸感风格：设计 Token 见 src/styles/main.css
  （米白纸底 #faf7f0、深海军蓝 #16324a、香槟金 #c9a96a、墨色 #20262e、涨红 #c0392b、跌绿 #1f7a5c），
  顶部章节导航（01-05 章），衬线标题（Songti/Georgia）× 无衬线数据。
  分享链接（CloudStudio 沙箱会回收，旧链 1242e777…已失效）：https://2a2e55642ca64ac1a8bd571002fada4e.app.workbuddy.link
  （每次重新发布都会换新地址，需手动更新此条）
- 派息日历（股息页）月份分布为示意算法，真实月份需数据层提供派息公告明细。
- 2026-08-15 起**取消历史快照归档机制**（不再定时刷新/回溯 history/ 数据），
  前端已移除 DatePicker 归档选择器、时间线「归档快照」区块、首页快照曲线与快照统计；
  OverviewView 净值曲线改用 daily-holdings.json（最近 90 天），涨跌口径改为「较上日」。
  持仓变动一律以用户提供的交易记录文档为准；市值/股价/汇率刷新时从网上获取（WebFetch）。

## 每日持仓演进（daily-holdings.json）
- 数据文件：public/data/daily-holdings.json（2026-01-01 ~ 今天，227 自然日，~267KB）。
  days[] 每项：date / totalAssets / holdings{code:{shares,price,fx,mv}} / events（当日交易事件）。
  另含顶层 fx（4 汇率对）与 prices（各标的历史收盘价）原始交易日序列。
- 生成方式：用户提供 DivTracker 交易 CSV（~/Downloads/DivTracker_Fire__*.csv，全部历史交易、不含 BYTE）
  → 2025-12-31 基线（累计至 2025-12-31 的交易 + BYTE 171 手动加入）
  → 按自然日演进持仓 → 市值 = 头寸 × 当日收盘价 × 汇率（nearest 填充：1/1 后向到 1/2，周末前向到上周五）。
- 生成脚本 /tmp/market_data/build_daily.py（一次性，未入库）；行情原始数据 /tmp/market_data/*.json。
- 行情获取：沙箱 curl 被墙，仅 WebFetch 可联网；Yahoo chart API 必须用 `range=ytd&interval=1d`
  （period1/period2 会被忽略返回超长乱数据）。2026 年曾持仓但已清仓的标的（GPIQ/QQQI/SCHD/SPCX）也要拉价格。
- 前端：04 时间线页（HistoryView.vue）顶部「每日持仓演进」章节（KPI 四卡 + 总资产每日曲线 + 市值堆叠面积图
  + 点击图表联动当日明细表 + 交易事件时间线）；EChart.vue 支持 events 透传；lib/portfolioData.ts 有 loadDailyHoldings()。
- 汇率/价格口径：历史收盘价（Yahoo），与 portfolio.json 的实时价快照会有 <1% 差异，属正常。

## 关键约定
- BYTE：171 × 229.5 USD/份，零股息，除非用户明确要求更新。
- BITB：零股息。
- 000660.KS：韩股 SK海力士，股息税按 10%（2026-08-15 用户改为 10%）。
- 汇率：美股+BYTE 用 USD/CNY；港股用 HKD/CNY；690D.DE 用 EUR/CNY；000660.KS 用 KRW/CNY。
- 用户偏好：暂不计算成本价与收益，只维护持仓快照与股息口径。
