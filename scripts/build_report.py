import os, re, collections
from openpyxl import Workbook
DIR='/Users/tg/Library/CloudStorage/OneDrive-个人/桌面/公众号写作/他人公众号文章下载/缓慢思考'
rows=[]
for f in os.listdir(DIR):
    if not f.endswith('.md') or f.startswith('_'): continue
    t=open(os.path.join(DIR,f),encoding='utf-8',errors='replace').read(1500)
    m=re.match(r'^---\s*\n([\s\S]*?)\n---', t)
    d={}
    if m:
        for line in m.group(1).split('\n'):
            mm=re.match(r'^([a-z_]+):\s*(.*)$', line)
            if mm: d[mm.group(1)]=mm.group(2).strip().strip('"')
    fields=['listened','reads','likes','shares','wows','comments']
    have=sum(1 for x in fields if str(d.get(x,'')).strip() not in ('','None'))
    state='完整' if have==6 else ('部分' if have>0 else '缺失')
    rows.append([d.get('title') or f[:-3], d.get('publish',''), d.get('listened',''), d.get('reads',''),
                 d.get('likes',''), d.get('shares',''), d.get('wows',''), d.get('comments',''), f, state, d.get('url','')])
rows.sort(key=lambda r: r[1], reverse=True)
wb=Workbook(); ws=wb.active; ws.title='互动数据核对'
ws.append(['序号','文章标题','发布时间','听全文','阅读','赞','转发','在看','评论','文件名','完整度','链接'])
for i,r in enumerate(rows, start=1): ws.append([i]+r)
for col,w in zip('ABCDEFGHIJKL',[6,42,18,9,9,7,7,7,7,40,8,58]): ws.column_dimensions[col].width=w
ws.freeze_panes='A2'
p=os.path.join(DIR,'_互动数据核对表.xlsx')
wb.save(p)
print('rows', len(rows), dict(collections.Counter(r[9] for r in rows)))
