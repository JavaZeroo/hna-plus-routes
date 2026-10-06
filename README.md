# 海航 PLUS · 全国航线地图

海南航空 2666 PLUS 会员 ¥199 经济舱权益的候选航班筛选工具。中国地图与日期、城市、省份、航司、时段和班期筛选联动，支持地图缩放、平移、机场点击和航班明细查询。

## 数据范围

- 公开快照覆盖 **2026-09-01 至 2026-10-24**；采集日期为 2026-10-05。
- 1,594 条班表记录、11 家航空公司、161 个机场；不保证完整覆盖。
- 公开班表不代表实际执飞、出票资格或实时 ¥199 库存。须以海南航空 APP 为准，税费另付。
- 本项目与海南航空及数据来源无隶属关系。

## 本地运行

需要 Node.js 22.12+。

```sh
npm ci
npm run dev
```

```sh
npm run build
```

构建产物 `dist/index.html` 为自包含单文件，可以离线打开，也可以通过任意静态服务器部署。

## GitHub Pages

在仓库 Settings → Pages 中选择 **GitHub Actions**。提交到 `main` 后，`.github/workflows/pages.yml` 会构建并部署；也可手动触发。项目使用相对资源路径，支持仓库子路径部署。

## 修改与更新

- `src/DashboardContent.jsx`：地图与筛选界面。
- `src/flight-model.js`：日期、班期、时间窗与航线汇总逻辑。
- `src/ui.jsx`：独立 UI 组件；无 ChatGPT 运行时依赖。
- `src/assets/flights.json`：班表快照。
- `src/assets/airports.json`：机场坐标。
- `src/assets/china.json`：省界底图。

更新班表时，同步调整 `flight-model.js` 的覆盖起止日期、覆盖期日期数量和页面中的快照说明；保留指定执飞日期、有效区间和源备注。文件不会自动更新。

## 来源及许可

本项目原创代码采用 MIT 许可。第三方数据与依赖遵循各自条款，**MIT 许可不覆盖第三方数据**，详见 [DATA_SOURCES.md](DATA_SOURCES.md)。
