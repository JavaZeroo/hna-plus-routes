export const START='2026-09-01', END='2026-10-24';
export const minute=s=>Number(s.slice(0,2))*60+Number(s.slice(2));
export const time=s=>s.slice(0,2)+':'+s.slice(2);
export const weekday=d=>new Date(d+'T12:00:00+08:00').getUTCDay()||7;
export const dateLabel=d=>d+' 周'+['','一','二','三','四','五','六','日'][weekday(d)];
export function operates(f,d){
 if(d<START||d>END)return false;
 if(f.operating_dates?.length)return f.operating_dates.includes(d);
 return d>=(f.valid_from||START)&&d<=(f.valid_to||END)&&f.days.includes(String(weekday(d)));
}
const ALL_DATES=Array.from({length:54},(_,i)=>{let d=new Date(START+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+i);return d.toISOString().slice(0,10)});
export function matches(f,{date='',dow='',carrier='',origin='',dest='',originProvince='',destProvince='',window='',exclusive=false,originAirport='',destAirport=''}){
 const m=minute(f.dep_time),isExclusive=(m>480&&m<=540)||(m>=1140&&m<1200);if(!(m<=540||m>=1140))return false;
 if(date?!operates(f,date):!ALL_DATES.some(d=>operates(f,d)&&(!dow||weekday(d)===Number(dow))))return false;
 return (!carrier||f.carrier_name===carrier)&&(!origin||f.origin_city===origin)&&(!dest||f.dest_city===dest)&&(!originProvince||f.origin_province===originProvince)&&(!destProvince||f.dest_province===destProvince)&&(!originAirport||f.origin_iata_code===originAirport)&&(!destAirport||f.dest_iata_code===destAirport)&&(!exclusive||isExclusive)&&(!window||window==='morning'&&m<=540||window==='night'&&m>=1140);
}
export function routesFrom(rows){const m=new Map();rows.forEach(f=>{const key=f.origin_iata_code+'-'+f.dest_iata_code;if(!m.has(key))m.set(key,{key,origin:f.origin_iata_code,dest:f.dest_iata_code,flights:[],exclusive:true});const r=m.get(key);r.flights.push(f);r.exclusive=r.exclusive&&f.is_2666_exclusive});return [...m.values()]}
export const DEFAULT={date:'2026-10-09',dow:'',carrier:'',origin:'',dest:'',originProvince:'',destProvince:'',window:'',exclusive:false,originAirport:'',destAirport:''};
