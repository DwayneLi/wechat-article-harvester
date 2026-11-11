import json, os, re
DIR='/Users/tg/Library/CloudStorage/OneDrive-个人/桌面/公众号写作/他人公众号文章下载/缓慢思考'
res=json.load(open('/tmp/bar_parse_final.json'))
norm={}
for k,v in res.items():
    m=re.match(r'(?:unknown_|train_)?(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})', k)
    if m:
        norm[m.group(1)+' '+m.group(2)+':'+m.group(3)]=v
print('parse entries', len(norm))
updated=0
for f in os.listdir(DIR):
    if not f.endswith('.md') or f.startswith('_'): continue
    p=os.path.join(DIR,f)
    t=open(p,encoding='utf-8',errors='replace').read()
    m=re.match(r'^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$', t)
    if not m: continue
    fm, body = m.group(1), m.group(2)
    mp=re.search(r'^publish:\s*"?(.*?)"?$', fm, re.M)
    pub=mp.group(1) if mp else ''
    v=norm.get(pub)
    if not v: continue
    for k2,val in [('likes',v[0]),('shares',v[1]),('wows',v[2]),('comments',v[3])]:
        if re.search(r'^'+k2+r':', fm, re.M):
            fm=re.sub(r'^'+k2+r':.*$', k2+': '+str(val), fm, flags=re.M)
        else:
            fm = fm + chr(10) + k2 + ': ' + str(val)
    open(p,'w',encoding='utf-8').write('---'+chr(10)+fm.strip(chr(10))+chr(10)+'---'+chr(10)+body)
    updated+=1
print('md updated', updated)
