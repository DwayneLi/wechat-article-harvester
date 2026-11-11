
import os, re, json, shutil
BASE='/Users/tg/WorkBuddy/2026-11-10-22-52-14'
DIR='/Users/tg/Library/CloudStorage/OneDrive-个人/桌面/公众号写作/他人公众号文章下载/缓慢思考'
BACKUP=os.path.join(DIR,'_原始备份')
STATS_PATH='/tmp/stats.json'
JUNK_START='预览时标签不可点'
TOP_JUNK={'在小说阅读器读本章','去阅读',''}

def parse_header(lines):
    title=''; author=''; publish=''; location=''; body_start=0
    for i,l in enumerate(lines[:8]):
        if l.startswith('#'):
            title=l.lstrip('#').strip(); body_start=i+1
        elif l.strip() and not author and 'ThinkingSlow' in l:
            s=l.replace('ThinkingSlow缓慢思考','').strip()
            s=re.sub(r'^(原创|转载)\s*','',s)
            parts=[p.strip() for p in re.split(r'\s{2,}', s) if p.strip()]
            seen=[]
            for p in parts:
                if p not in seen: seen.append(p)
            author='/'.join(seen); body_start=i+1
        elif l.strip().startswith('_') and re.search(r'\d{4}年\d{2}月\d{2}日', l):
            m=re.search(r'(\d{4})年(\d{2})月(\d{2})日\s*(\d{2}:\d{2})?', l)
            if m:
                publish=f'{m.group(1)}-{m.group(2)}-{m.group(3)}' + (f' {m.group(4)}' if m.group(4) else '')
            rest=re.sub(r'_+',' ',l)
            rest=re.sub(r'\d{4}年\d{2}月\d{2}日\s*\d{2}:\d{2}','',rest)
            toks=[t.strip() for t in re.split(r'\s{2,}', rest) if t.strip()]
            if toks: location=toks[-1]
            body_start=i+1
    return title, author, publish, location, body_start

def clean_body(lines, start):
    body=lines[start:]
    while body and (body[0].strip() in TOP_JUNK):
        body.pop(0)
    text='\n'.join(body)
    idx=text.find(JUNK_START)
    if idx>=0:
        head=text[:idx]
        head=re.sub(r'(\n\s*#{2,}\s*)+\s*$','',head)
        text=head
    text=re.sub(r'!\[作者头像\]\([^)]*\)\s*','',text)
    text=re.sub(r'!\[\]\([^)]*QxXhRzAmk7[^)]*\)\s*','',text)
    text=re.sub(r'[ \t]+\n','\n',text)
    text=re.sub(r'\n{3,}','\n\n',text).strip()
    return text

def to_quotes(text):
    out=[]
    for para in text.split('\n\n'):
        p=para.strip()
        if not p: continue
        if p.startswith('#') or p.startswith('![') or p.startswith('>') or p.startswith('|'):
            out.append(p); continue
        is_q=False
        for a,b in (('“','”'),('「','」'),('"','"')):
            if p.startswith(a):
                end=p.rfind(b)
                if end >= max(5, int(len(p)*0.5)):
                    is_q=True
                    break
        out.append(('> ' + p) if is_q else p)
    return '\n\n'.join(out)

def split_author(a):
    return a.split('/')[0] if a else ''

def build_front_matter(meta, st):
    tags=['公众号','缓慢思考']
    if '股东信' in meta['title']: tags.append('巴菲特股东信')
    if 'Taleb' in meta['title'] or '塔勒布' in meta['title']: tags.append('塔勒布')
    lines=['---']
    lines.append('title: ' + json.dumps(meta['title'], ensure_ascii=False))
    lines.append('author: ' + json.dumps(split_author(meta['author']), ensure_ascii=False))
    lines.append('source: "ThinkingSlow缓慢思考"')
    lines.append('publish: ' + json.dumps(meta['publish'], ensure_ascii=False))
    lines.append('location: ' + json.dumps(meta['location'], ensure_ascii=False))
    lines.append('url: ' + json.dumps(meta['url'], ensure_ascii=False))
    for k in ('listened','reads','likes','shares','wows','comments'):
        v = st.get(k) if st else None
        lines.append(f'{k}: ' + (str(v) if v not in (None,'') else ''))
    lines.append('tags:')
    for t in tags: lines.append('  - ' + t)
    lines.append('updated: ' + meta['updated'])
    lines.append('---')
    return '\n'.join(lines)

def strip_front_matter(text):
    if text.startswith('---'):
        m=re.match(r'^---\s*\n[\s\S]*?\n---\s*\n', text)
        if m: return text[m.end():]
    return text

def process(fname, stats):
    path=os.path.join(DIR,fname)
    content=strip_front_matter(open(path,encoding='utf-8',errors='replace').read())
    raw=content.split('\n')
    title,author,publish,location,start=parse_header(raw)
    body=to_quotes(clean_body(raw,start))
    key=os.path.splitext(fname)[0]
    url=stats.get(key,{}).get('url','') if stats else ''
    st=stats.get(key,{}) if stats else {}
    meta=dict(title=title,author=author,publish=publish,location=location,url=url,updated='2026-11-11')
    fm=build_front_matter(meta, st)
    return fm + '\n\n# ' + title + '\n\n' + body + '\n', meta

if __name__=='__main__':
    files=sorted([f for f in os.listdir(DIR) if f.endswith('.md')])
    stats={}
    if os.path.exists(STATS_PATH):
        raw=json.load(open(STATS_PATH,encoding='utf-8'))
        stats=raw
    os.makedirs(BACKUP, exist_ok=True)
    n=0
    for f in files:
        if f.startswith('_'): continue
        src=os.path.join(DIR,f)
        if not os.path.exists(os.path.join(BACKUP,f)):
            shutil.copy2(src, os.path.join(BACKUP,f))
        out,meta=process(f, stats)
        open(src,'w',encoding='utf-8').write(out)
        n+=1
    print('cleaned', n)
