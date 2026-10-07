# 官方航线数据与范围

航线、航班号、起飞时刻、班期、日期和产品标注仅来自海南航空官方。已移除第三方班表。

| 数据 | 官方原文 | 范围与限制 |
| --- | --- | --- |
| 官网航班时刻表（当前计划） | [航班时刻表](https://new.hnair.com/hainanair/ibe/common/flightSchedule.do) | 按城市对抓取，见下节。抓取日期、城市对数、记录数和生效区间写在 `src/assets/coverage.json`。 |
| H5 权益卡查询抓录（存档） | [权益卡适用航班查询](https://m.hnair.com/hnams/plusMember/ableAirlineQuery) | 2026-10-06 人工抓录杭州出发 2026-10-09 的 25+6 条，保存在 `data/official/official-hgh-*.json`，用于核对。权益标注可由起飞时刻推出，页面不再单独展示此来源。 |
| 2025 全国历史参考表 | [海航 PLUS 会员权益卡适用航班参考列表](https://m.hnair.com/cms/me/plus/info/202508/t20250808_78914.html) | 完整导入表内1692条记录、11航司、983单向机场对。表页标注更新至2025-10-29，“即日起—12月25日”。不是2026当前计划，也不是全时段全国班表。 |
| 权益规则 | [海航 PLUS 官方使用规则](https://m.hnair.com/cms/me/plus/info/202505/t20250519_76300.html) | 按官方规则筛选时间窗；时刻筛选结果不保证实际执飞或出票资格。 |

## 官方航班时刻表抓取（new.hnair.com）

海航官网「[航班时刻表](https://new.hnair.com/hainanair/ibe/common/flightSchedule.do)」无需登录，按城市对返回航班号、起降时刻、班期和分段生效区间，集团各航司（HU、GS、JD、8L、PN、GX、FU、UQ、9H、Y8、CN）在同一个库里。`scripts/crawl-official-timetable.py` 直接使用页面自身的表单接口和地点数据库，不绕过任何验证。

- `python scripts/crawl-official-timetable.py cities`：从官网地点库枚举国内城市与机场，写入 `data/official/timetable/cities.json`（含官网地点 ID、中文名、IATA）。
- `python scripts/crawl-official-timetable.py crawl --pairs all`：遍历官网地点库全部国内城市（及仅有机场条目的地点）的有序组合，约 5.9 万对；`--pairs matrix` 只取 2025 表出现过的城市，`--pairs 2025`（默认）只取该表的城市对。结果逐行追加到 `data/official/timetable/rows.jsonl`，可中断续跑。`--workers N` 并发会话数；默认每个无序城市对先查一个方向，无班表则跳过反向，`--no-prune` 关闭；`--origin`、`--dest`、`--pair`、`--limit`、`--refresh` 控制范围。
- `python scripts/crawl-official-timetable.py summary`：统计已抓取的记录。
- 每条记录保留页面原文：机场对、航班号、航司 logo 代码、起飞/到达时间、周一至周日运行标记、生效时段文本，以及查询时间。查询返回的结果块原样缓存到 `data/official/timetable/raw/`（不入库）。
- 页面提示“此航班时刻表仅供参考，如遇航班调整，请以实际执行时间为准”。时刻表不含权益卡标注；2025 官方参考表 1692 条记录的“2666 / 666/2666”标注全部可由起飞时刻推出（08:00–09:00、19:00–20:00 起飞为 2666 独享，其余权益时段为两档共有），因此权益判断在本地按官方规则进行。
- 官网地点库没有“长治”，该城市的城市对未查询；“茅台”“那拉提”“香格里拉”“达州”分别按官网的“遵义”“新源”“迪庆”“达州金垭（机场）”查询。

## 覆盖边界

官网时刻表只能按城市对查询，没有全国导出，因此按全部国内城市的有序组合逐一查询（约 5.9 万对，反向剪枝后约 3.1 万次请求）。H5 权益卡查询接口有验签，本项目没有绕过验证、保存凭据或复制签名。“未收录”不等于没有航班；2025 历史表与当前时刻表分开统计，不混合。

## 转换与可复核记录

- `data/official/official-2025-raw.json`：官方表全部数据行，顺序与表页一致；标准化记录 `source_row` 包括表头行号。
- `data/official/official-hgh-2666.json`、`official-hgh-pek-all.json`：官方H5界面可见的原始文本，含出到城市、航班号、班期、生效范围、时刻及产品标记；不是库存数据。
- `scripts/build-flights.py`：把时刻表记录和 2025 表映射到地图机场，生成 `src/assets/flights.json`、`coverage.json`、`airports.json`。时刻表给出的机场名按关键字（首都/大兴、虹桥/浦东、双流/天府、新舟/茅台、黄金/瑞金）或同城唯一机场归并到 IATA 代码；`--check` 校验生成文件与官方数据一致。
- 时刻表记录保留官网的分段生效区间和班期，日期筛选按“日期在区间内且班期包含该星期”判断。官网分段像滚动窗口，与 H5 按日查询偶有出入（例如 JD5377 杭州→哈尔滨），因此结果表示“计划执飞”，不是出票保证。
- 历史表未公布到达时刻及逐班起止日：到达显示“未公布”，具体日期筛选禁用；支持官方班期星期和起飞时间筛选。
- 不依据已有第三方航班记录补齐官方缺失字段，不从旧表推断今年航线。

## 地图辅助资料与许可

机场坐标来自 [datasets/airport-codes](https://github.com/datasets/airport-codes)，源于 OurAirports，PDDL；机场代码与坐标仅用于地图定位。中国省界来自 [DataV.GeoAtlas](https://datav.aliyun.com/portal/school/atlas/area_selector)，服务条款适用。这些辅助资料不决定任何航线或班表。

本项目原创代码 MIT；MIT 不覆盖官方内容及第三方底图。React / React DOM、Vite、vite-plugin-singlefile 等依赖许可随各包提供。构建文件内置全部数据，可离线使用；不会自动刷新。
