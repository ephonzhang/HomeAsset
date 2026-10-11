# 家庭财产统计 · 长期记忆

## 持仓数据权威来源
持仓明细（标的代码、名称、数量、股息税率、BYTE 价格、汇率口径）以
`~/.workbuddy/skills/portfolio-dividend-dashboard/references/portfolio_rules.md` 为准。
任何刷新总表/仪表盘的操作，先读该文件，再改。非用户明确指示不得改固定持仓。

## 当前组合（**2026-10-09 快照**，已落库并上线）
**13 项**：QQQM **4990**、VOO 700、IYW 1500、QNDX **14562**、BITB 3000、0883.HK 30000、
SMH **149**、0700.HK 1500、CGDV 1500、690D.DE 30000、BYTE 171、**TLT 242**、000660.KS 10。
已清仓：GPIQ、QQQI。总资产 **¥22,922,946.68**（2026-10-11 起；BYTE 单价 229.5→241.35 后）。
（较 09-28 版：QQQM 5000→4990、QNDX 14330→14562、SMH 60→149、新增 TLT 242 股。）

**行情源（2026-10-10 实测可用）**
- 美股（QQQM.OQ/QNDX.OQ/SMH.OQ/TLT.OQ/VOO.am/BITB.am/IYW.am/CGDV.am）与港股（00883/00700）：
  腾讯 `https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=us{sym},day,,,30,`，**需走代理 7897**；字段 day[idx][2]=收盘。
- 韩股 000660：Naver `https://fchart.stock.naver.com/sise.nhn?symbol=000660&timeframe=day&count=30&requestType=0`（euc-kr）。
- 德股 690D.DE：**Yahoo 直连与自建代理均失败**（429/空）；stooq/德交所/börse-frankfurt API 均无该代码；
  可用 **`https://r.jina.ai/https://query1.finance.yahoo.com/v8/finance/chart/690D.DE?range=3mo&interval=1d`** 中转取 JSON。
- 汇率：新浪 `https://vip.stock.finance.sina.com.cn/forex/api/jsonp.php/var%20_fx=/NewForexService.getDayKLine?symbol=fx_susdcny`（同理 shkdcny/seurcny/skrwcny），需 Referer。

## 前端实现
- 2026-08-15 起仪表盘改为 **Vue 3 + Vite + TS + Pinia + ECharts**（替代 React+Tailwind+Recharts），
  项目位于本工作区根目录（/Users/zhangyifeng/WorkBuddy/家庭财产统计/），数据契约仍为 public/data/portfolio.json。
- 依赖安装必须走 `--registry=https://registry.npmmirror.com`（npmjs 在沙箱内不可达）。
- 2026-08-15 第二版改造为「家庭财富报告」纸感风格：设计 Token 见 src/styles/main.css
  （米白纸底 #faf7f0、深海军蓝 #16324a、香槟金 #c9a96a、墨色 #20262e、涨红 #c0392b、跌绿 #1f7a5c），
  顶部章节导航（01-05 章），衬线标题（Songti/Georgia）× 无衬线数据。
  **主用线上站（GitHub Pages）：https://ephonzhang.github.io/HomeAsset/** —— ⚠️ **该域名在中国大陆真直连被封锁**
  （`185.199.108.153` Fastly IP，443 被 RST；实测 `--noproxy '*'` 返回 000）。**只在挂了代理的电脑上能开，手机上打不开。**
  **手机/免代理请用国内分享链接：https://home-asset-stats.app.workbuddy.host/**（2026-10-10 发布，
  目录 `deploy/2026-10-10/`，真直连 200/0.42s；含 FIRE 页 + 2026-10-09 数据）。
  **2026-10-11 已同目录覆盖重发**（移除「数据导入」页后的构建）：链接**不变**，真直连 3/3×200、0.37–0.47s，
  线上入口 `index-DZRsnpJA.js`、6 章齐全。**重发流程就两步**：
  ① `rm -rf deploy/2026-10-10/assets deploy/2026-10-10/index.html && cp -R dist/. deploy/2026-10-10/`
  （先清旧 assets 再整份覆盖，避免残留旧哈希产物）；② 用 sites 发布能力把该目录再发一次
  （`directory=deploy/2026-10-10`、`appName=家庭资产统计`、`domainPrefix=home-asset-stats`、`userAskedToPublish=true`），
  **按目录查表命中同一 app → 链接稳定**。`data/` 与 dist 内容一致，无需单独动。
  数据更新走 gh-pages 分支的 `data/`（与本地 `public/data/` 同名三个文件）；**代码更新要整份覆盖 `index.html` + `assets/`**。
  历史教训（2026-10-10）：gh-pages 长期只推 data/、从不推 assets/，导致第 05 章「生活方案」(FIRE) 与「数据导入」
  虽在源码/分享链接上有，线上却一直没有 —— 已用 `d94150e` 补齐全量构建修复。
  路由为 hash 模式，FIRE 页直达 `.../#/fire`。
  push 前 git 必须显式加 `-c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897`。
  （2026-10-10 数据/代码均已上线；main 侧源码 commit c185671 / ce1a386。）
  **发布国内链接的做法（推荐）**：固定用 `deploy/2026-10-10/`（`cp -R dist/. deploy/2026-10-10/` 覆盖后）重新发布
  → **同一目录复用同一 app，链接不变、内容被覆盖**，即可长期用**固定地址**更新数据（sites skill 明示）。
  仅在需绕开浏览器缓存时才复制到**新日期目录**，但那会新建 app → **换新链接**，地址不再固定。
  **稳定性实测（2026-10-11，`--noproxy '*'` 真直连）**：新链 6/6×200、0.17–0.44s；09-01 旧链存活 34 天仍 200（首请求 2.28s 疑冷启）；
  两域名**同 IP `49.233.240.214`**（腾讯云北京 CLB，`server: CloudStudio Gateway`）；TLS `*.workbuddy.host` 到期 **2027-03-27**。
  云端四文件与本地 dist **SHA-256 逐字节一致** → 真·云端快照、不依赖本地沙箱；**内容是快照、不会自动更新**（旧链数据仍停 08-31 即证）。
  **旧分享链接（2026-09-01 部署，含 FIRE 页但数据停留在 08-31）：https://4ce76621a30344a8a0c25d607bf576bc.app.workbuddy.link**
  （同目录重部署会复用沙箱+链接，但浏览器易缓存旧资源；要「无缓存」就复制到新目录部署换新链接。
   旧链 2a2e5564…、78fc1e8d… 仍在线，待用户确认后下线）
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

## 「数据导入」页已下线（2026-10-11，用户指示）
- 用户认定本站是**纯静态页**，不要浏览器端 CSV 导入。已**整章移除**：
  `lib/chapters.ts` 的 `/import` 章节、`router` 路由、`views/ImportView.vue` 全删；
  导航回到 **6 章**（扉页/持仓透视/股息收益/时间线/生活方案/档案）。
- `stores/portfolio.ts` **同步瘦身**：删掉 importEngine 依赖、`importedMeta/isImported`、
  `buildPreview/applyResult/applyCsv/exportArchive/restoreArchive/clearImport`，
  以及整套 IndexedDB/localStorage 存档与冷启动恢复逻辑 ——
  **站点现在每次加载都以 `public/data/` 静态文件为准，不再有「导入覆盖」这回事**。
  副作用（正向）：不会再出现「浏览器里残留的旧导入盖住线上最新数据」。
- 保留 `src/lib/importEngine.ts` 未删：`scripts/rebuild_from_csv.py` 头部注释仍以它为口径基准。
- ⚠️ **改完必须提交 main**：`.github/workflows/rebuild.yml` 是 checkout main → npm run build → publish gh-pages，
  **源码不回 main 的话，下次 data/inbox 触发重建会把「数据导入」tab 又推回线上**。
- 数据更新路径不变（且不再依赖网页）：DivTracker CSV → `scripts/rebuild_from_csv.py --write` →
  `npm run build` → 发布；或丢进 `data/inbox/` 让 CI 自动重算+部署。
  `worker/`（Cloudflare 同步代理）与 `DEPLOY-CLOUD.md` 随之成为**死代码**，未清理，用户需要时可删。

## 曾经的导入持久化边界（2026-09-01 记录，现已作废）
- 站点是**纯静态站、无后端**。页面上传 CSV 只是**在浏览器本地存档**（IndexedDB 优先、localStorage 兜底），
  **不会**写回 public/data。刷新能否恢复完全取决于浏览器是否允许写本地存档。
- 存档失败的典型场景：无痕/隐私窗口、页面被嵌在第三方 iframe（WorkBuddy 预览面板）、
  浏览器阻止第三方存储、**站点域名变了**（存档按 origin 隔离，CloudStudio 每次重发都是新域名）。
- 因此**要长期生效必须落库**：用 `scripts/rebuild_from_csv.py <csv> --end YYYY-MM-DD --write`
  重算 daily-holdings.json + portfolio.json → `npm run build` → 重新部署。
- 2026-09-01 起前端已加固：存档写入结果可见（「已存档 · IndexedDB / localStorage 兜底 / 未存档」），
  失败时拦截跳转并明确告警；导入页支持「导出/恢复存档 JSON」。

## 关键约定
- BYTE：**241.35** × 171 份 = **¥276,221.67**（USD/CNY 6.6929），零股息，除非用户明确要求更新。
  （2026-10-11 用户明确把 BYTE 单价 229.5 → **241.35 USD/份**，全部 282 天历史与总资产已同步重算。）
- BITB：零股息。
- 000660.KS：韩股 SK海力士，股息税按 10%（2026-08-15 用户改为 10%）。
- 汇率：美股+BYTE 用 USD/CNY；港股用 HKD/CNY；690D.DE 用 EUR/CNY；000660.KS 用 KRW/CNY。
- 用户偏好：暂不计算成本价与收益，只维护持仓快照与股息口径。
