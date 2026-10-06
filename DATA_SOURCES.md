# 官方航线数据与范围

航线、航班号、起飞时刻、班期、日期和产品标注仅来自海南航空官方。已移除第三方班表。

| 数据 | 官方原文 | 范围与限制 |
| --- | --- | --- |
| 2026 已查询计划 | [权益卡适用航班查询](https://m.hnair.com/hnams/plusMember/ableAirlineQuery) | 2026-10-06 采集。查询日期 2026-10-09；杭州→任意地点的2666航班25条；杭州→北京首都“全部航班”6条。合并同班号、机场对、起飞时刻的重复项后28条、17方向。其余城市未收录。 |
| 2025 全国历史参考表 | [海航 PLUS 会员权益卡适用航班参考列表](https://m.hnair.com/cms/me/plus/info/202508/t20250808_78914.html) | 完整导入表内1692条记录、11航司、983单向机场对。表页标注更新至2025-10-29，“即日起—12月25日”。不是2026当前计划，也不是全时段全国班表。 |
| 权益规则 | [海航 PLUS 官方使用规则](https://m.hnair.com/cms/me/plus/info/202505/t20250519_76300.html) | 按官方规则筛选时间窗；时刻筛选结果不保证实际执飞或出票资格。 |

## 为什么目前还不是最新全国全量

官方H5“全部航班”要求同时选择出发地和到达地；权益卡模式可以只选出发城市。公开网页没有提供全国一键导出。直接调用对应接口返回“验签错误”，本项目没有绕过验证、保存凭据或复制签名。另查到的官方下载班表有历史年份，不能冒充当前计划。当前尚未取得覆盖11家适用航司的最新全国全时段表。

当前收集范围必须在网页显著显示。“未收录”“未查询日期”不等于没有航班。2025历史表与2026数据不能混合为一个当前全国统计。

## 转换与可复核记录

- `data/official/official-2025-raw.json`：官方表全部数据行，顺序与表页一致；标准化记录 `source_row` 包括表头行号。
- `data/official/official-hgh-2666.json`、`official-hgh-pek-all.json`：官方H5界面可见的原始文本，含出到城市、航班号、班期、生效范围、时刻及产品标记；不是库存数据。
- `scripts/import-official.py`：将上述官方记录映射到地图机场坐标。运行方式：`python scripts/import-official.py RESEARCH_DIR data/official`；`RESEARCH_DIR` 需含 `official-2025-raw.json` 与机场坐标源 `airport-codes.csv`。
- 当前记录保留官方生效起止日，但日期筛选仅支持实际查询确认的2026-10-09。未查其他日期不外推结果。
- 历史表未公布到达时刻及逐班起止日：到达显示“未公布”，具体日期筛选禁用；支持官方班期星期和起飞时间筛选。
- 不依据已有第三方航班记录补齐官方缺失字段，不从旧表推断今年航线。

## 地图辅助资料与许可

机场坐标来自 [datasets/airport-codes](https://github.com/datasets/airport-codes)，源于 OurAirports，PDDL；机场代码与坐标仅用于地图定位。中国省界来自 [DataV.GeoAtlas](https://datav.aliyun.com/portal/school/atlas/area_selector)，服务条款适用。这些辅助资料不决定任何航线或班表。

本项目原创代码 MIT；MIT 不覆盖官方内容及第三方底图。React / React DOM、Vite、vite-plugin-singlefile 等依赖许可随各包提供。构建文件内置全部数据，可离线使用；不会自动刷新。
