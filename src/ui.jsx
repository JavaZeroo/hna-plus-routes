import React, {useState} from 'react';
import flights from './assets/flights.json';

export const useDataApp=()=>({queries:{flights:{rows:flights}}});
export function Button({children,...props}){return <button type="button" {...props}>{children}</button>}
export function Dropdown({label,value,choices,choiceLabels={},onChange,disabled}){return <div className="control"><label>{label}<select value={value} disabled={disabled} onChange={e=>onChange(e.target.value)}>{choices.map(v=><option key={v} value={v}>{choiceLabels[v]||v}</option>)}</select></label></div>}
export function Switch({label,checked,onChange}){return <div className="switch"><label><input type="checkbox" checked={checked} onChange={e=>onChange(e.target.checked)}/>{label}</label></div>}
export function DataComponent({title,description,headerControls,children}){return <section className="section"><div className="section-heading"><h2>{title}</h2>{headerControls}</div><p className="description">{description}</p>{children}</section>}
export function DataTable({columns,rows,caption,rowKey,onRowSelect}){
 const [search,setSearch]=useState(''),[page,setPage]=useState(0),[sort,setSort]=useState(null);
 let filtered=rows.filter(r=>!search||Object.values(r).some(v=>String(v).toLowerCase().includes(search.toLowerCase())));
 if(sort)filtered=[...filtered].sort((a,b)=>String(a[sort.field]??'').localeCompare(String(b[sort.field]??''),'zh-CN')*sort.order);
 const max=Math.max(0,Math.ceil(filtered.length/10)-1),current=Math.min(page,max),shown=filtered.slice(current*10,current*10+10);
 return <div><div className="table-tools"><label>搜索明细 <input type="search" value={search} placeholder="航班、城市、机场…" onChange={e=>{setSearch(e.target.value);setPage(0)}}/></label><span>{filtered.length.toLocaleString()} 条记录</span></div><div className="table-scroll"><table><caption>{caption}</caption><thead><tr>{columns.map(c=><th key={c.field}><button onClick={()=>setSort({field:c.field,order:sort?.field===c.field?-sort.order:1})}>{c.label}{sort?.field===c.field?(sort.order===1?' ↑':' ↓'):''}</button></th>)}</tr></thead><tbody>{shown.map(r=><tr key={r[rowKey]} tabIndex="0" onClick={()=>onRowSelect(r)} onKeyDown={e=>{if(e.key==='Enter')onRowSelect(r)}}>{columns.map(c=><td key={c.field}>{c.renderCell?c.renderCell(r[c.field],r):r[c.field]}</td>)}</tr>)}</tbody></table>{!shown.length&&<p className="empty-table">暂无匹配记录</p>}</div><nav className="pagination" aria-label="表格分页"><Button disabled={!current} onClick={()=>setPage(current-1)}>上一页</Button><span>第 {current+1} / {max+1} 页</span><Button disabled={current>=max} onClick={()=>setPage(current+1)}>下一页</Button></nav></div>
}
