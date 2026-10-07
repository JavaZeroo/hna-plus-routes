import coverage from './assets/coverage.json';
export {coverage};
export const START=coverage.valid_from, END=coverage.valid_to;
const n=x=>x.toLocaleString();
export const SOURCES={
 'official-timetable':{label:'官网航班时刻表 · 当前计划',url:'https://new.hnair.com/hainanair/ibe/common/flightSchedule.do',description:`海航官网公开航班时刻表，${coverage.fetched_to} 按城市对抓取：查询 ${n(coverage.pairs_queried)} 个城市对，${n(coverage.pairs_with_schedule)} 个有班表，共 ${n(coverage.timetable_rows)} 条分段记录、${n(coverage.timetable_flights)} 个航班号、${n(coverage.timetable_routes)} 个单向机场对、${coverage.timetable_carriers} 家航司。生效区间 ${coverage.valid_from} — ${coverage.valid_to}。只遍历 2025 参考表出现过的城市对，新开航线可能未收录；官网提示时刻表仅供参考。`},
 'official-2025':{label:'2025 官方全国参考表 · 历史',url:'https://m.hnair.com/cms/me/plus/info/202508/t20250808_78914.html',description:`官方表全部 ${n(coverage.archive_rows)} 条记录，${coverage.archive_carriers} 家航司、${coverage.archive_routes} 个单向机场对。更新于2025-10-29，表页标注“即日起—12月25日”。历史参考，不能用于判断2026年可用航班；不是全时段班表。`}
};
const today=new Date(Date.now()+8*3600e3).toISOString().slice(0,10);
export const DEFAULT_DATE=today<START?START:today>END?END:today;
export const minute=s=>Number(s.slice(0,2))*60+Number(s.slice(2));
export const time=s=>s?s.slice(0,2)+':'+s.slice(2):'未公布';
export const weekday=d=>new Date(d+'T12:00:00+08:00').getUTCDay()||7;
export const dateLabel=d=>d+' 周'+['','一','二','三','四','五','六','日'][weekday(d)];
export function operates(f,d){return f.source_id==='official-timetable'&&d>=f.valid_from&&d<=f.valid_to&&f.days.includes(String(weekday(d)))}
export function matches(f,{source='official-timetable',date='',dow='',carrier='',origin='',dest='',originProvince='',destProvince='',window='',exclusive=false,originAirport='',destAirport=''}){
 if(f.source_id!==source)return false;
 const m=minute(f.dep_time),eligible=m<=540||m>=1140,isExclusive=(m>480&&m<=540)||(m>=1140&&m<1200);
 if(window!=='all'&&!eligible)return false;
 if(source==='official-2025'&&date)return false;
 if(date&&!operates(f,date))return false;
 if(!date&&dow&&!f.days.includes(String(dow)))return false;
 return (!carrier||f.carrier_name===carrier)&&(!origin||f.origin_city===origin)&&(!dest||f.dest_city===dest)&&(!originProvince||f.origin_province===originProvince)&&(!destProvince||f.dest_province===destProvince)&&(!originAirport||f.origin_iata_code===originAirport)&&(!destAirport||f.dest_iata_code===destAirport)&&(!exclusive||isExclusive)&&(!window||window==='all'||window==='morning'&&m<=540||window==='night'&&m>=1140);
}
export function routesFrom(rows){const m=new Map();rows.forEach(f=>{const key=f.origin_iata_code+'-'+f.dest_iata_code;if(!m.has(key))m.set(key,{key,origin:f.origin_iata_code,dest:f.dest_iata_code,flights:[],exclusive:true});const r=m.get(key);r.flights.push(f);r.exclusive=r.exclusive&&f.is_2666_exclusive});return [...m.values()]}
export const DEFAULT={source:'official-timetable',date:DEFAULT_DATE,dow:'',carrier:'',origin:'',dest:'',originProvince:'',destProvince:'',window:'',exclusive:false,originAirport:'',destAirport:''};
