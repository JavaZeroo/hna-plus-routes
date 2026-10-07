# 海航 PLUS · 官方航线地图

海南航空2666 PLUS会员¥199经济舱权益的航线与时刻筛选工具。地图与城市、省份、航司、时间及班期筛选联动，支持缩放、平移、机场点击和航班详情。航线与时刻仅依赖官方数据，不采集库存。

## 当前覆盖范围

- **官网航班时刻表（当前计划）**：按城市对抓取海航官网公开「航班时刻表」，覆盖 2025 参考表出现过的约 1400 个城市对、11 家航司，保留官网给出的航班号、起降时刻、班期和分段生效区间。抓取日期、记录数和生效区间见 `src/assets/coverage.json`，页面顶部同步显示。只遍历已知城市对，新开航线可能缺失；官网提示时刻表仅供参考。
- **2025官方全国历史表**：海航官网参考表全部1692条记录、11航司、983单向机场对。表页更新至2025-10-29。历史参考，不能判断2026航班；具体日期筛选禁用。
- 权益档位不依赖人工标注：2025 官方表的“2666 / 666/2666”标注全部可由起飞时刻推出，页面按官方规则以起飞时间判断（19:00—次日 09:00 适用；08:00—09:00、19:00—20:00 为 2666 独享）。代码共享、包机、港澳台不在时刻表里标注，仍需购票时确认。
- 两个来源分开选择与统计。每条记录可查看官方原文链接和原始备注。未收录不代表没有航班。
- 199元税费另付；以官方规则及实际购票内容为准。本项目与海南航空无隶属关系。

## 本地运行和构建

需要Node.js22.12+。

```sh
npm ci
npm run dev
npm run build
```

`dist/index.html`是自包含静态HTML，可离线打开。提交到main后GitHub Actions自动构建并部署Pages。

## 数据流水线

```sh
python3 scripts/crawl-official-timetable.py cities     # 官网地点库 → data/official/timetable/cities.json
python3 scripts/crawl-official-timetable.py crawl      # 官网时刻表 → data/official/timetable/rows.jsonl（可续跑；--refresh 全量重抓）
python3 scripts/build-flights.py                       # 官方记录 → src/assets/flights.json、coverage.json、airports.json
npm run build && npm run smoke                         # 构建单文件页面并用无头 Chromium 做端到端冒烟测试
```

`data/official/` 保存可复核的官方原文；`src/assets/` 只放生成结果，`python3 scripts/build-flights.py --check` 用于校验两者一致。不要用第三方班表补全，也不要手改生成文件。

## 自动化

- `.github/workflows/ci.yml`：每次推送和 PR 校验生成文件与官方数据一致、构建成功、冒烟测试通过，并上传构建产物。
- `.github/workflows/update-timetable.yml`：每周二凌晨（北京时间）自动全量重抓官网时刻表，重建数据、构建并冒烟通过后提交到 main，再触发 Pages 部署；也可手动运行并选择 `matrix` 范围。记录数相比上次下降超过 30% 时拒绝覆盖，避免官网异常时写入空数据。
- `.github/workflows/pages.yml`：main 分支构建并部署 GitHub Pages。

完整范围、官方查询限制、转换规则、地图辅助来源及许可见[DATA_SOURCES.md](DATA_SOURCES.md)。原创代码MIT；官方内容、底图和依赖遵循各自条款。
