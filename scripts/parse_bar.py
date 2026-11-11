import os, re, json, subprocess
from PIL import Image
DS='/tmp/dataset'

def components(img, thresh=140):
    W,H=img.size; px=img.load()
    mask=[[1 if px[x,y]<thresh else 0 for x in range(W)] for y in range(H)]
    seen=[[0]*W for _ in range(H)]; comps=[]
    for y in range(H):
        for x in range(W):
            if mask[y][x] and not seen[y][x]:
                st=[(y,x)]; seen[y][x]=1
                minx=maxx=x; miny=maxy=y
                while st:
                    cy,cx=st.pop()
                    if cx<minx: minx=cx
                    if cx>maxx: maxx=cx
                    if cy<miny: miny=cy
                    if cy>maxy: maxy=cy
                    for dy in (-1,0,1):
                        for dx in (-1,0,1):
                            ny,nx=cy+dy,cx+dx
                            if 0<=ny<H and 0<=nx<W and mask[ny][nx] and not seen[ny][nx]:
                                seen[ny][nx]=1; st.append((ny,nx))
                comps.append(dict(x0=minx,x1=maxx,y0=miny,y1=maxy,w=maxx-minx+1,h=maxy-miny+1))
    return comps

def glyphs_of(path):
    img=Image.open(path).convert('L')
    comps=[c for c in components(img) if 12<=c['h']<=60 and 4<=c['w']<=80]
    comps.sort(key=lambda c:c['x0'])
    return img, comps

def is_icon(c): return (28<=c['h']<=48) and (c['w']>=22)

REF=DS+'/2023-01-08_21-33_bar.png'
img0,gl0=glyphs_of(REF)
tpls=[]
for c in [c for c in gl0 if is_icon(c)][:4]:
    crop=img0.crop((c['x0'],c['y0'],c['x1']+1,c['y1']+1)).resize((32,32), Image.LANCZOS)
    tpls.append(list(crop.getdata()))

def icon_class(img,c):
    crop=img.crop((c['x0'],c['y0'],c['x1']+1,c['y1']+1)).resize((32,32), Image.LANCZOS)
    px=list(crop.getdata())
    best=(0,1e9)
    for i,t in enumerate(tpls):
        d=sum(abs(a-b) for a,b in zip(px,t))/1024.0
        if d<best[1]: best=(i,d)
    return best

def ocr_num(img, box):
    x0,y0,x1,y1=box
    crop=img.crop((max(0,x0-4),max(0,y0-5),x1+4,y1+5))
    crop=crop.resize((crop.size[0]*6, crop.size[1]*6), Image.LANCZOS)
    crop.save('/tmp/_n.png')
    out=subprocess.run(['/tmp/ocr','/tmp/_n.png'],capture_output=True,text=True).stdout
    txt=' '.join(l.split(chr(9))[-1] for l in out.strip().split(chr(10)) if l.strip())
    m=re.findall(r'[0-9]+', txt)
    return (int(m[0]) if m else None)

def parse(path):
    img,gl=glyphs_of(path)
    ics=sorted([(icon_class(img,c)[0], c) for c in gl if is_icon(c)], key=lambda p:p[1]['x0'])
    res={}
    used=set()
    for idx,(cls,c) in enumerate(ics):
        nxt = ics[idx+1][1]['x0'] if idx+1<len(ics) else 10**9
        # take contiguous components right of icon
        cand=[g for g in gl if g['x0']>c['x1'] and g['x0']<nxt]
        run=[]
        prev_x=c['x1']
        for g in cand:
            if g['x0']-prev_x <= 26:
                run.append(g); prev_x=g['x1']
            else:
                break
        digits=[g for g in run if g['w']<=22]
        text = any(g['w']>22 for g in run)
        if digits and not text:
            box=(min(d['x0'] for d in digits), min(d['y0'] for d in digits), max(d['x1'] for d in digits), max(d['y1'] for d in digits))
            res[cls]=ocr_num(img, box)
        elif text:
            res[cls]=0
        else:
            res[cls]=0
    return [res.get(i) for i in range(4)]

files=sorted([f for f in os.listdir(DS) if f.endswith('_bar.png')])
out={}
for f in files:
    out[f[:-8]]=parse(os.path.join(DS,f))
json.dump(out, open('/tmp/bar_parse3.json','w'), ensure_ascii=False, indent=1)
ok=sum(1 for v in out.values() for x in v if x is not None)
print('parsed bars', len(out), 'cells ok', ok, '/', len(out)*4)
for k in list(out)[:8]: print(k, out[k])
