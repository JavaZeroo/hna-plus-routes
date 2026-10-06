# 数据来源与第三方说明

| 内容 | 来源 | 许可/说明 |
| --- | --- | --- |
| 2666 PLUS 权益条件 | [海南航空官方规则](https://m.hnair.com/cms/me/plus/info/202505/t20250519_76300.html) | 规则摘要，仅供查询，以官方最新条件为准 |
| 班表快照 | [海航随心飞助手](https://www.sxfroute.com/)（公开 `/api/flight-data`） | 来源未提供明确开放数据许可；仅保留航班事实记录与来源说明，第三方数据不纳入本项目 MIT 许可 |
| 机场坐标 | [datasets/airport-codes](https://github.com/datasets/airport-codes)，源于 OurAirports | PDDL；按中国机场 IATA 代码选取坐标 |
| 中国省界地图 | [DataV.GeoAtlas](https://datav.aliyun.com/portal/school/atlas/area_selector)，`100000_full.json` | 来源服务条款适用；第三方底图不纳入本项目 MIT 许可 |

快照于 2026-10-05 获取，覆盖 2026-09-01—2026-10-24。地图机场连线为示意，不用于导航。不提供实时会员库存，也不保证航班实际执飞或可出票。

依赖：React / React DOM（MIT）、Vite（MIT）、vite-plugin-singlefile（MIT）以及它们的传递依赖。依赖版本由 `package-lock.json` 固定；各包完整许可随安装包提供。
