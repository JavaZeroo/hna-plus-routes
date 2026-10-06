export const START='2026-10-09', END='2026-10-09';
export const SOURCES={
 'official-current':{label:'2026 官方已查询计划 · 杭州出发',url:'https://m.hnair.com/hnams/plusMember/ableAirlineQuery',description:'2026-10-09：杭州出发2666计划；杭州→北京首都补充全部时段。28条记录、17个方向。全国最新全量尚未取得；其他城市未收录，不代表无航班。'},
 'official-2025':{label:'2025 官方全国参考表 · 历史',url:'https://m.hnair.com/cms/me/plus/info/202508/t20250808_78914.html',description:'官方表全部1,692条记录，11家航司、983个单向机场对。更新于2025-10-29，表页标注“即日起—12月25日”。历史参考，不能用于判断2026年可用航班；不是全时段班表。'}
};
export const minute=s=>Number(s.slice(0,2))*60+Number(s.slice(2));
export const time=s=>s?s.slice(0,2)+':'+s.slice(2):'未公布';
export const weekday=d=>new Date(d+'T12:00:00+08:00').getUTCDay()||7;
export const dateLabel=d=>d+' 周'+['','一','二','三','四','五','六','日'][weekday(d)];
export function operates(f,d){return f.source_id==='official-current'&&f.observed_dates?.includes(d)&&d>=f.valid_from&&d<=f.valid_to&&f.days.includes(String(weekday(d)))}
export function matches(f,{source='official-current',date='',dow='',carrier='',origin='',dest='',originProvince='',destProvince='',window='',exclusive=false,originAirport='',destAirport=''}){
 if(f.source_id!==source)return false;
 const m=minute(f.dep_time),eligible=m<=540||m>=1140,isExclusive=(m>480&&m<=540)||(m>=1140&&m<1200);
 if(window!=='all'&&!eligible)return false;
 if(source==='official-2025'&&date)return false;
 if(date&&!operates(f,date))return false;
 if(!date&&dow&&!f.days.includes(String(dow)))return false;
 return (!carrier||f.carrier_name===carrier)&&(!origin||f.origin_city===origin)&&(!dest||f.dest_city===dest)&&(!originProvince||f.origin_province===originProvince)&&(!destProvince||f.dest_province===destProvince)&&(!originAirport||f.origin_iata_code===originAirport)&&(!destAirport||f.dest_iata_code===destAirport)&&(!exclusive||isExclusive)&&(!window||window==='all'||window==='morning'&&m<=540||window==='night'&&m>=1140);
}
export function routesFrom(rows){const m=new Map();rows.forEach(f=>{const key=f.origin_iata_code+'-'+f.dest_iata_code;if(!m.has(key))m.set(key,{key,origin:f.origin_iata_code,dest:f.dest_iata_code,flights:[],exclusive:true});const r=m.get(key);r.flights.push(f);r.exclusive=r.exclusive&&f.is_2666_exclusive});return [...m.values()]}
export const DEFAULT={source:'official-current',date:START,dow:'',carrier:'',origin:'',dest:'',originProvince:'',destProvince:'',window:'',exclusive:false,originAirport:'',destAirport:''};
