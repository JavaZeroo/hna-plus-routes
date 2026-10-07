import React,{useMemo,useState,useRef} from 'react';
import {DataComponent,DataTable,Dropdown,Button,Switch,useDataApp} from './ui.jsx';
import china from './assets/china.json';
import airports from './assets/airports.json';
import {START,END,SOURCES,coverage,time,minute,weekday,dateLabel,matches,routesFrom,DEFAULT,DEFAULT_DATE,operates} from './flight-model.js';
import './hna.css';
const RULES='https://m.hnair.com/cms/me/plus/info/202505/t20250519_76300.html';
const rad=Math.PI/180;
const merc=y=>Math.log(Math.tan(Math.PI/4+y*rad/2));
function project([lon,lat]){return [(lon-73)*14+90,(merc(54)-merc(lat))*14/rad+25]}
function inset([lon,lat]){return [(lon-105)*5.1+858,(25-lat)*5.1+462]}
function paths(feature,insetMode=false){const g=feature.geometry,polys=g.type==='MultiPolygon'?g.coordinates:[g.coordinates],p=insetMode?inset:project;return polys.flatMap(poly=>poly.map(ring=>ring.filter(c=>insetMode?c[0]>=105&&c[0]<=125&&c[1]<=25:c[1]>=17.5).map((c,i)=>{const q=p(c);return (i?'L':'M')+q[0].toFixed(2)+','+q[1].toFixed(2)}).join('')+'Z')).filter(s=>s!=='Z')}
const basemap=china.features.flatMap((f,i)=>paths(f).map((d,j)=>({d,id:i+'-'+j,name:f.properties.name||''})));
const insets=china.features.flatMap((f,i)=>paths(f,true).map((d,j)=>({d,id:i+'-'+j})));
function curve(a,b){const A=project([a.lon,a.lat]),B=project([b.lon,b.lat]);const dx=B[0]-A[0],dy=B[1]-A[1],l=Math.hypot(dx,dy),bend=Math.min(65,l*.14),c=[(A[0]+B[0])/2-dy/(l||1)*bend,(A[1]+B[1])/2+dx/(l||1)*bend];return `M${A} Q${c} ${B}`}
function RouteMap({routes,rows,chosen,onChoose,onAirport,originCity}){
 const [zoom,setZoom]=useState(1),[pan,setPan]=useState([0,0]),[hover,setHover]=useState(null);const drag=useRef(null);const svgRef=useRef(null);
 const nodes=useMemo(()=>{const m=new Map();routes.forEach(r=>[r.origin,r.dest].forEach(k=>m.set(k,(m.get(k)||0)+1)));return [...m].sort((a,b)=>b[1]-a[1])},[routes]);
 const labelKeys=new Set(nodes.filter(([k],i)=>i<15||airports[k].city===originCity||nodes.length<24).map(x=>x[0]));
 const chosenRoute=routes.find(r=>r.key===chosen);const displayRoute=hover||chosenRoute;
 function start(e){if(e.target.closest('[data-interactive]'))return;const r=svgRef.current.getBoundingClientRect();drag.current={x:e.clientX,y:e.clientY,pan:[...pan],scale:1100/r.width};e.currentTarget.setPointerCapture(e.pointerId)}
 function move(e){if(!drag.current)return;const d=drag.current;setPan([d.pan[0]+(e.clientX-d.x)*d.scale,d.pan[1]+(e.clientY-d.y)*d.scale])}
 return <div className="hna-map-panel"><div className="hna-map-controls"><Button onClick={()=>setZoom(z=>Math.min(3,z+.35))} aria-label="放大地图">＋</Button><Button onClick={()=>setZoom(z=>Math.max(1,z-.35))} aria-label="缩小地图">－</Button><Button onClick={()=>{setZoom(1);setPan([0,0])}}>复位</Button></div>
 <svg ref={svgRef} className="hna-map" viewBox="0 0 1100 690" role="img" aria-label={`中国航线地图，${routes.length}条单向航线`} onPointerDown={start} onPointerMove={move} onPointerUp={()=>drag.current=null} onPointerCancel={()=>drag.current=null}>
 <defs><pattern id="hna-grid" width="50" height="50" patternUnits="userSpaceOnUse"><path d="M50 0H0V50" fill="none" stroke="#203848" strokeWidth=".5"/></pattern><clipPath id="hna-map-clip"><rect width="1100" height="690"/></clipPath></defs><rect width="1100" height="690" fill="#0b1d2a"/><rect width="1100" height="690" fill="url(#hna-grid)"/>
 <g clipPath="url(#hna-map-clip)"><g transform={`translate(${pan[0]} ${pan[1]}) translate(550 345) scale(${zoom}) translate(-550 -345)`}>
 {basemap.map(p=><path key={p.id} d={p.d} fill="#142f40" stroke="#365567" strokeWidth=".7"><title>{p.name}</title></path>)}
 <g className="hna-route-lines">{routes.map(r=><path key={r.key} d={curve(airports[r.origin],airports[r.dest])} fill="none" stroke={r.exclusive?'#ffb35f':'#50ced4'} strokeWidth={chosen===r.key?3:1.2} opacity={chosen?(chosen===r.key?1:.10):(originCity ? .70 : .36)} />)}</g>
 {routes.map(r=><path data-interactive="route" key={r.key} d={curve(airports[r.origin],airports[r.dest])} fill="none" stroke="transparent" strokeWidth="9" className="hna-route-hit" onPointerEnter={()=>setHover(r)} onPointerLeave={()=>setHover(null)} onClick={()=>onChoose(r)}><title>{airports[r.origin].city} → {airports[r.dest].city} · {r.flights.length}条记录；点击查看</title></path>)}
 {nodes.map(([k,n])=>{const a=airports[k],p=project([a.lon,a.lat]),active=originCity===a.city;return <g data-interactive="airport" key={k} transform={`translate(${p})`} className="hna-airport" role="button" tabIndex="0" aria-label={`${a.city} ${a.name}，筛选从此机场出发`} onClick={()=>onAirport(a)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onAirport(a)}}}><circle r={10} fill="transparent"/><circle r={active?6:Math.min(4.5,2.3+Math.sqrt(n)/5)} fill={active?'#ffb35f':'#b0edf0'} stroke="#0b1d2a" strokeWidth="1.3"/>{labelKeys.has(k)&&<text x="8" y="-7" className="hna-city-label">{a.city}{['PEK','PKX','PVG','SHA','TFU','CTU'].includes(k)?' '+k:''}</text>}<title>{a.name} {k} · {n}条连接，点击设为出发地</title></g>})}
 </g></g>
 <g className="hna-inset"><rect x="850" y="458" width="115" height="130" rx="3" fill="#0b1d2a" stroke="#365567"/>{insets.map(p=><path key={p.id} d={p.d} fill="#142f40" stroke="#365567" strokeWidth=".4"/>)}<text x="855" y="605" fill="#8ea8b9" fontSize="13">南海诸岛</text></g>
 <text x="30" y="651" fill="#8ea8b9" fontSize="14">机场间连线示意 · 不代表实际飞行航路</text></svg>
 <div className="hna-map-legend"><span><i className="common"/>共有时刻 / 全时段对照</span><span><i className="exclusive"/>2666 独享时刻</span><span>点击机场筛选出发地；拖动地图平移</span></div>
 {displayRoute&&<div className="hna-route-preview"><b>{airports[displayRoute.origin].city} {displayRoute.origin} → {airports[displayRoute.dest].city} {displayRoute.dest}</b><span>{displayRoute.flights.length} 条班表记录 · {displayRoute.flights.map(f=>f.flight_no).filter((v,i,a)=>a.indexOf(v)===i).slice(0,5).join(' / ')}</span><small>官方计划 · 按起飞时刻筛选</small></div>}
 </div>
}
export function DashboardContent(){
 const {queries}=useDataApp();const all=queries.flights?.rows||[];const [filters,setFilters]=useState(DEFAULT),[selected,setSelected]=useState(''),[selectedFlight,setSelectedFlight]=useState(null);
 const set=(key,value)=>{setFilters(f=>({...f,[key]:value,...(key==='origin'?{originAirport:''}:{}),...(key==='dest'?{destAirport:''}:{})}));setSelected('');setSelectedFlight(null)};
 const rows=useMemo(()=>all.filter(f=>matches(f,filters)),[all,filters]);const routes=useMemo(()=>routesFrom(rows),[rows]);
 const visibleRows=selected?rows.filter(f=>f.origin_iata_code+'-'+f.dest_iata_code===selected):rows;
 const sourceRows=all.filter(f=>f.source_id===filters.source); const source=SOURCES[filters.source]; const archive=filters.source==='official-2025';
 const carriers=[...new Set(sourceRows.map(f=>f.carrier_name))].sort((a,b)=>a.localeCompare(b,'zh-CN'));
 const cities=[...new Set(sourceRows.flatMap(f=>[f.origin_city,f.dest_city]))].sort((a,b)=>a.localeCompare(b,'zh-CN'));
 const provinces=[...new Set(sourceRows.flatMap(f=>[f.origin_province,f.dest_province]))].sort((a,b)=>a.localeCompare(b,'zh-CN'));
 const scopeFilters=Object.fromEntries(Object.entries(filters).filter(([,v])=>v));
 const conflictKeys=useMemo(()=>{if(!filters.date)return new Set();const m=new Map();rows.forEach(f=>{const k=f.flight_no+'-'+f.origin_iata_code+'-'+f.dest_iata_code;m.set(k,new Set([...(m.get(k)||[]),f.dep_time]))});return new Set([...m].filter(([,v])=>v.size>1).map(([k])=>k))},[rows,filters.date]);
 const conflict=f=>conflictKeys.has(f.flight_no+'-'+f.origin_iata_code+'-'+f.dest_iata_code);
 const tableRows=visibleRows.map(f=>({...f,route:f.origin_city+' '+f.origin_iata_code+' → '+f.dest_city+' '+f.dest_iata_code,dep:time(f.dep_time),arr:time(f.arr_time)+(f.arr_time&&minute(f.arr_time)<minute(f.dep_time)?' +1天':''),week:f.days==='1234567'?'每天':'周'+[...f.days].map(x=>['','一','二','三','四','五','六','日'][x]).join('、'),validity:archive?'2025年历史表；逐班日期未公布':`${f.valid_from} — ${f.valid_to}（官网时刻表分段，抓取于 ${f.fetched_at}）`,tier:minute(f.dep_time)>540&&minute(f.dep_time)<1140?'时段不适用':f.is_2666_exclusive?'2666独享':'两档共有',check:archive?'官方历史表':conflict(f)?'同班号多时刻':'官方时刻表'}));
 function selectRoute(r){setSelected(r.key);setSelectedFlight(null)}
 function airport(a){setFilters(f=>({...f,origin:a.city,originProvince:'',originAirport:a.iata}));setSelected('');setSelectedFlight(null)}
 const columns=[{field:'flight_no',label:'航班',renderCell:(v,r)=><span className="hna-flight-id">{v}<small>{r.carrier_name}</small></span>},{field:'route',label:'航线'},{field:'dep',label:'起飞'},{field:'arr',label:'到达'},{field:'week',label:'班期'},{field:'tier',label:'套餐'},{field:'check',label:'核验状态',renderCell:(v,r)=><span className={conflict(r)?'hna-warning-tag':'hna-neutral-tag'}>{v}</span>}];
 return <article className="hna-dashboard">
 <div className="hna-intro"><div><span className="hna-pill">2666 PLUS</span><strong>经济舱 ¥199 / 单程</strong><span>税费另付</span></div><p>11 家航司境内自营航班 · 北京时间 19:00—次日 09:00 · 春运、暑运除外</p></div>
 <div className="hna-coverage"><b>航线与班表仅使用官方来源 · 采集于 {coverage.fetched_to}</b><span>{source.description}</span><a href={source.url} target="_blank" rel="noreferrer">查看官方原文 / 查询入口</a></div>
 <Dropdown label="数据范围" showLabel value={filters.source} choices={Object.keys(SOURCES)} choiceLabels={Object.fromEntries(Object.entries(SOURCES).map(([k,v])=>[k,v.label]))} onChange={v=>{setFilters({...DEFAULT,source:v,date:v==='official-2025'?'':DEFAULT_DATE});setSelected('');setSelectedFlight(null)}}/>
 <div className="hna-filters">
 <label className="hna-date">出发日期<input aria-label="出发日期" type="date" disabled={archive} value={filters.date} onChange={e=>set('date',e.target.value)}/><button className="hna-text-button" onClick={()=>set('date','')}>查看已收录计划</button></label>
 <Dropdown label="出发城市" showLabel value={filters.origin||'全部城市'} choices={['全部城市',...cities]} onChange={v=>set('origin',v==='全部城市'?'':v)}/>
 <Dropdown label="到达城市" showLabel value={filters.dest||'全部城市'} choices={['全部城市',...cities]} onChange={v=>set('dest',v==='全部城市'?'':v)}/>
 <Dropdown label="航空公司" showLabel value={filters.carrier||'全部航司'} choices={['全部航司',...carriers]} onChange={v=>set('carrier',v==='全部航司'?'':v)}/>
 <Dropdown label="起飞时段" showLabel value={filters.window||'every'} choices={['every','morning','night','all']} choiceLabels={{every:'2666适用时段',morning:'00:00—09:00',night:'19:00—23:59',all:'全部已收录时段'}} onChange={v=>set('window',v==='every'?'':v)}/>
 <Switch label="只看 2666 独享时刻" checked={filters.exclusive} onChange={v=>set('exclusive',v)}/>
 </div>
 <div className="hna-more-filters"><Dropdown label="出发省份" showLabel value={filters.originProvince||'全部省份'} choices={['全部省份',...provinces]} onChange={v=>set('originProvince',v==='全部省份'?'':v)}/><Dropdown label="到达省份" showLabel value={filters.destProvince||'全部省份'} choices={['全部省份',...provinces]} onChange={v=>set('destProvince',v==='全部省份'?'':v)}/><Dropdown label="星期" showLabel disabled={!!filters.date} value={filters.dow||'every'} choices={['every','1','2','3','4','5','6','7']} choiceLabels={{every:'全部星期',1:'周一',2:'周二',3:'周三',4:'周四',5:'周五',6:'周六',7:'周日'}} onChange={v=>set('dow',v==='every'?'':v)}/><Button onClick={()=>{setFilters({...filters,origin:filters.dest,dest:filters.origin,originAirport:filters.destAirport,destAirport:filters.originAirport,originProvince:filters.destProvince,destProvince:filters.originProvince});setSelected('')}}>交换出发 / 到达</Button><Button onClick={()=>{setFilters(DEFAULT);setSelected('');setSelectedFlight(null)}}>重置筛选</Button></div>
 {(filters.originAirport||filters.destAirport)&&<div className="hna-airport-filter">机场筛选：{filters.originAirport&&airports[filters.originAirport].name} {filters.destAirport&&' → '+airports[filters.destAirport].name}<button onClick={()=>{setFilters(f=>({...f,originAirport:'',destAirport:''}));setSelected('')}}>清除机场限制</button></div>}
 {filters.date&&(filters.date<START||filters.date>END)&&<div className="hna-empty-alert">所选日期超出官网时刻表的生效区间（{START} — {END}），无法判断该日适用航班；空结果不代表该日没有航班。</div>}
 <DataComponent id="flight-map" queryId="flights" kind="custom" title="官方来源航线地图" sourceRows={rows} displayRows={rows} scopeFilters={scopeFilters} variant="plain" description="按所选来源的单向机场对汇总。地图与筛选联动；橙色表示该方向当前筛选记录均在2666独享时刻内。蓝色还可能包含白天对照班次。">
 <div className="hna-map-stats" data-reviewed-rows><span><b>{rows.length.toLocaleString()}</b>班表记录</span><span><b>{routes.length}</b>单向航线</span><span><b>{new Set(rows.flatMap(f=>[f.origin_iata_code,f.dest_iata_code])).size}</b>机场</span><span><b>{rows.filter(f=>f.is_2666_exclusive).length}</b>独享时刻记录</span><span className="hna-status">{filters.date?dateLabel(filters.date):archive?'2025 历史参考，非当前航班':'全部已查询计划'}</span></div>
 <RouteMap routes={routes} rows={rows} chosen={selected} onChoose={selectRoute} onAirport={airport} originCity={filters.origin}/>
 {!rows.length&&<p className="hna-empty">当前条件没有候选记录，可清除城市、省份或时段限制后重试。</p>}
 </DataComponent>
 <DataComponent id="flight-table" queryId="flights" kind="table" title={selected?'所选航线 · 航班明细':'航班明细'} sourceRows={visibleRows} displayRows={tableRows} scopeFilters={{...scopeFilters,...(selected?{route:selected}:{})}} variant="plain" description="仅显示所选官方来源。点击行查看官方来源、班期和查询范围；表内搜索只影响本表。" headerControls={selected?<Button onClick={()=>{setSelected('');setSelectedFlight(null)}}>返回全部筛选结果</Button>:null}>
 <DataTable columns={columns} rows={tableRows} caption="海航2666 PLUS候选航班明细" rowKey="id" onRowSelect={r=>{setSelectedFlight(r);setSelected(r.origin_iata_code+'-'+r.dest_iata_code)}} rowActionLabel={r=>`查看 ${r.flight_no} 航班详情`} />
 </DataComponent>
 {selectedFlight&&<div className="hna-detail" data-reviewed-rows><div><h3>{selectedFlight.flight_no} · {selectedFlight.carrier_name}</h3><button aria-label="关闭航班详情" onClick={()=>setSelectedFlight(null)}>关闭</button></div><dl><dt>出发机场</dt><dd>{selectedFlight.origin_airport}（{selectedFlight.origin_iata_code}）</dd><dt>到达机场</dt><dd>{selectedFlight.dest_airport}（{selectedFlight.dest_iata_code}）</dd><dt>时刻 / 班期</dt><dd>{selectedFlight.dep}—{selectedFlight.arr} · {selectedFlight.week}（北京时间）</dd><dt>运行日期</dt><dd>{selectedFlight.validity}</dd><dt>官方产品标注</dt><dd>{selectedFlight.official_product||'未标注权益卡产品'}</dd><dt>原始备注</dt><dd>{selectedFlight.note||'无'}</dd><dt>官方来源</dt><dd><a href={source.url} target="_blank" rel="noreferrer">{source.label}</a> · {archive?'2025年历史记录':`查询条件：${selectedFlight.query_pair}，抓取于 ${selectedFlight.fetched_at}`}</dd></dl></div>}
 <details className="hna-rules"><summary>199 元权益的使用条件与数据范围</summary><div className="hna-rule-grid"><div><h3>适用权益</h3><p>2666 档：19:00（含）至次日 09:00（含）起飞，按北京时间。国内自营航班，不含港澳台、代码共享和包机。五一、国庆可用；春运（农历腊月十五至正月廿五）和暑运（7 月 1 日—8 月 31 日）除外。</p><p>激活后有效期一年，首次乘坐航班须为有效期起算之日起七天后；最多同时保留 3 段未出行单程客票。经济舱 B 舱每班初始配额不少于 30 张，经停长短段合并计算。建议至少提前三天预订，三天内依开放舱位及余票决定。199 元不含机建、燃油和其他税费。</p><p><a href={RULES} target="_blank" rel="noreferrer">海南航空官方使用规则</a></p></div><div><h3>官方数据与覆盖缺口</h3><p>当前计划来自海航官网公开「航班时刻表」，按城市对逐一查询（{coverage.pairs_queried.toLocaleString()} 对，抓取于 {coverage.fetched_to}），保留官网给出的航班号、起降时刻、班期和分段生效区间。只遍历了 2025 参考表出现过的城市对，新开航线可能缺失；时刻表不标注代码共享，权益按官方规则以起飞时间判断。官网提示时刻表仅供参考，以实际执行为准。未收录不代表没有航班。</p><p>全国历史库来自海航官方全国参考表，完整导入表内1,692条记录，保留官方班期和产品标注。这是2025年的适用航班参考表，已经筛过权益时段，无法用于研究白天全部航班，也不能推断2026年仍然执飞。</p><p>每条记录可查看来源链接与原始备注。只研究航线与计划时刻，不采集库存。199元权益按官方规则判断，税费另付。</p><p>机场坐标：<a href="https://github.com/datasets/airport-codes" target="_blank" rel="noreferrer">OurAirports / airport-codes（PDDL）</a>；地图：<a href="https://datav.aliyun.com/portal/school/atlas/area_selector" target="_blank" rel="noreferrer">DataV.GeoAtlas</a>。辅助地图资料不用于确定航线或时刻。</p><p>页面数据、地图与代码已内置，可离线使用。下载文件不会自动更新。</p></div></div></details>
 </article>
}
