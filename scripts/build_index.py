import os, re, json, collections
DIR='/Users/tg/Library/CloudStorage/OneDrive-个人/桌面/公众号写作/他人公众号文章下载/缓慢思考'
FILES=[f for f in os.listdir(DIR) if f.endswith('.md') and not f.startswith('_')]
tags=json.load(open('/tmp/tags.json',encoding='utf-8'))
CATS=['股东信解读','公司分析','投资人与机构','书与博客','投资理念','商业与创业','生活与思考']

def parse_fm(txt):
    m=re.match(r'^---\s*\n([\s\S]*?)\n---\s*\n', txt)
    d={}
    if m:
        for line in m.group(1).split('\n'):
            mm=re.match(r'^([a-z_]+):\s*(.*)$', line)
            if mm: d[mm.group(1)]=mm.group(2).strip().strip('"')
    return d

def rebuild(txt, newtags):
    m=re.match(r'^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$', txt)
    if not m: return None
    fm=m.group(1); body=m.group(2)
    fm2=re.sub(r'^tags:\s*\n(?:\s+- .*\n)+', '', fm, flags=re.M).rstrip('\n')
    add='tags:\n' + ''.join('  - '+t+'\n' for t in newtags)
    return '---\n'+fm2+'\n'+add+'---\n'+body

meta={}
for f in FILES:
    p=os.path.join(DIR,f)
    txt=open(p,encoding='utf-8',errors='replace').read()
    tg=tags.get(f, ['生活与思考'])
    out=rebuild(txt, tg) or txt
    if out!=txt: open(p,'w',encoding='utf-8').write(out)
    d=parse_fm(out)
    meta[f]=dict(title=d.get('title') or os.path.splitext(f)[0], publish=d.get('publish',''), tags=tg)
print('updated', len(FILES), 'sample tags', meta[FILES[0]]['tags'])

allitems=sorted(meta.items(), key=lambda kv: kv[1]['publish'], reverse=True)
L=['---','title: "ThinkingSlow缓慢思考 · 全部文章目录"','tags:','  - MOC','  - 公众号','  - 缓慢思考','author: "戴汨"','updated: 2026-11-11','---','',
   '# ThinkingSlow缓慢思考 · 全部文章目录','',
   f'共 **{len(allitems)}** 篇；按语义分为 {len(CATS)} 类，每篇最多 3 个标签。','',
   '## 分类索引','']
for c in CATS:
    items=[it for it in allitems if c in it[1]['tags']]
    L.append(f'### {c}（{len(items)} 篇）')
    L.append('')
    for f,md in items:
        name=os.path.splitext(f)[0]
        others=[t for t in md['tags'] if t!=c]
        suffix=('　（' + ' / '.join(others) + '）') if others else ''
        L.append(f'- [[{name}]] · {md["publish"][:10]}{suffix}')
    L.append('')
L += ['## 全部文章（按时间倒序）','']
cur=None
for f,md in allitems:
    y=md['publish'][:4] or '未知'
    if y!=cur:
        L.append(''); L.append(f'### {y}'); L.append(''); cur=y
    L.append(f'- [[{os.path.splitext(f)[0]}]] · {md["publish"][:10]}')
open(os.path.join(DIR,'_目录.md'),'w',encoding='utf-8').write('\n'.join(L))
print('index lines', len(L))
cnt=collections.Counter()
for f,md in allitems:
    for t in md['tags']: cnt[t]+=1
print(dict(cnt))
