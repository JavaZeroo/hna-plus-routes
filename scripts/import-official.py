"""Normalize the official reference table and visible official H5 query captures.

Usage: python scripts/import-official.py RESEARCH_DIR CAPTURE_DIR
No third-party flight schedule is read. Airport data supplies map positions only.
"""
import csv
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
research, captures = map(Path, sys.argv[1:3])
assets = root / 'src/assets'
airports = json.loads((assets / 'airports.json').read_text())
aliases = {'北京首都':'PEK','北京大兴':'PKX','上海虹桥':'SHA','上海浦东':'PVG','成都天府':'TFU','重庆万州':'WXN','重庆江北':'CKG','大连周水子':'DLC','茅台':'WMT','那拉提':'NLT','香格里拉':'DIG'}
extra = {'乌海':('WUA','内蒙古'),'包头':('BAV','内蒙古'),'台州':('HYN','浙江'),'吕梁':('LLV','山西'),'塔城':('TCG','新疆'),'常州':('CZX','江苏'),'库车':('KCA','新疆'),'张家口':('ZQZ','河北'),'沧源':('CWJ','云南'),'潍坊':('WEF','山东'),'澜沧':('JMJ','云南'),'石河子':('SHF','新疆'),'腾冲':('TCZ','云南'),'茅台':('WMT','贵州'),'那拉提':('NLT','新疆'),'邵阳':('WGN','湖南'),'长治':('CIH','山西'),'香格里拉':('DIG','云南')}
positions = {r['iata_code']:r for r in csv.DictReader((research/'airport-codes.csv').open()) if r['iso_country']=='CN'}
for city,(code,province) in extra.items():
    r = positions[code]
    first,second = map(float,r['coordinates'].split(','))
    lat,lon = (first,second) if first < 60 else (second,first)
    airports[code] = dict(iata=code,city=city,province=province,name=r['name'],lat=lat,lon=lon)
    aliases[city] = code
for code,a in airports.items():
    aliases.setdefault(a['city'],code)
carriers = dict(HU='海南航空',CN='大新华航空',JD='首都航空',GS='天津航空',**{'8L':'祥鹏航空','PN':'西部航空','GX':'北部湾航空','FU':'福州航空','UQ':'乌鲁木齐航空','9H':'长安航空','Y8':'金鹏航空'})
def base(no,orig,dest,dep,days,source):
    o,d = airports[aliases[orig]],airports[aliases[dest]]
    minute = int(dep[:2])*60+int(dep[2:])
    return dict(flight_no=no,carrier_name=carriers[no[:2]],origin_city=o['city'],dest_city=d['city'],origin_iata_code=o['iata'],dest_iata_code=d['iata'],origin_province=o['province'],dest_province=d['province'],origin_airport=o['name'],dest_airport=d['name'],dep_time=dep,arr_time='',days=days,is_2666_exclusive=(480<minute<=540 or 1140<=minute<1200),source_id=source)
rows=[]
for n,(no,orig,dest,dep,days,product) in enumerate(json.loads((research/'official-2025-raw.json').read_text()),2):
    f=base(no,orig,dest,dep.replace(':','').zfill(4),days,'official-2025')
    f.update(id=f'archive-{n}',source_row=n,official_product=product,note='官方历史表：更新于2025-10-29；表页适用日期“即日起—12月25日”。未公布到达时刻及逐班生效起止日。')
    rows.append(f)
current={}
for filename,scope in [('official-hgh-2666.json','杭州→任意地点 / 2666'),('official-hgh-pek-all.json','杭州→北京首都 / 全部航班')]:
    for r in json.loads((captures/filename).read_text()):
        no=re.search(r'([A-Z0-9]{2}\d{3,4})$',r['flight']).group(1)
        dep,arr=re.findall(r'\d{2}:\d{2}',r['times'])
        ds=re.search(r'班期/每周(.*?)生效时段',r['detail']).group(1)
        days=''.join(str('一二三四五六日'.index(c)+1) for c in ds if c in '一二三四五六日')
        start,end=re.findall(r'\d{4}\.\d{2}\.\d{2}',r['detail'])
        f=base(no,r['origin'],r['dest'],dep.replace(':',''),days,'official-current')
        f.update(arr_time=arr.replace(':',''),valid_from=start.replace('.','-'),valid_to=end.replace('.','-'),observed_dates=['2026-10-09'],official_product=r['rights'],note=f'官方查询条件：{scope}；查询日期2026-10-09。仅将已查询日期用于日期筛选。原始显示：'+r['detail'])
        key=(no,f['origin_iata_code'],f['dest_iata_code'],f['dep_time'])
        current[key]=f
for n,f in enumerate(current.values(),1):
    f['id']=f'current-{n}';rows.append(f)
(assets/'flights.json').write_text(json.dumps(rows,ensure_ascii=False,separators=(',',':')))
(assets/'airports.json').write_text(json.dumps(airports,ensure_ascii=False,separators=(',',':')))
print(json.dumps({'archive_rows':1692,'current_rows':len(current),'current_routes':len({(f['origin_iata_code'],f['dest_iata_code']) for f in current.values()}),'archive_routes':len({(f['origin_iata_code'],f['dest_iata_code']) for f in rows if f['source_id']=='official-2025'})}))
