#!/Users/tg/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3
# -*- coding: utf-8 -*-
"""
解析微信文章截图顶部信息行 (_hdr.png) 中的「听全文」人数。

思路（纯离线图像处理，不依赖 GUI / 微信）：
  1. 二值化 + 8 连通域，把整行拆成字形 (connected components)。
  2. 顶部信息行里所有深色字形按横向间隔 (gap>60) 天然分成两组：
       [公众号名 深蓝色文字]  ... gray 日期/地区(灰度较浅, 阈值 140 不会被选中) ...  [右侧: 耳机图标 N人 AI摘要]
     取最后一组作为「右侧组」。
  3. 右侧组第一个连通域恒为耳机图标 (26x25)。用全数据集众数模板定位图标，
     图标右侧紧邻的窄高字形就是数字 (宽 8-16, 高 21-22)；更宽的「人」(27x28) 表示数字结束。
  4. 数字字形用「全数据集字形聚类 + OCR 投票」自动建立模板库，再按最近邻分类。
     —— 这样避开了 OCR 把图标粘到数字上 (71 -> 671)、以及 OCR 把 6/9 读反的问题。
  5. 「人」前面若没有数字 (老的没人听过的文章显示为 🎧 听全文) -> 记为 0。

输出: /tmp/listened.json  {"2026-04-16_11-05": 71, ...}

运行环境: 需要 Pillow (numpy 可选, 装了会快很多)。本机用 DSH 自带 python:
  /Users/tg/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3 /tmp/parse_listened.py
"""
import os, re, sys, json, subprocess, collections

from PIL import Image

DS   = '/tmp/dataset'
OCR  = '/tmp/ocr'
THRESH = 140          # 二值化阈值: 深蓝色正文/图标 < 110, 灰色日期文字 ~180
GAP    = 60           # 右侧组的横向间隔阈值
BANK_TH    = 0.02     # 字形聚类阈值 (20x20 归一化后平均绝对差)
CLS_TH     = 10.0     # 最近邻分类接受阈值 (远小于不同数字间的最小距离 ~18)
DIG_W      = (7, 18)  # 数字字形宽度范围
DIG_H      = (17, 23) # 数字字形高度范围
REN_W      = (25, 30) # 「人」字宽度范围
REN_H      = (26, 30) # 「人」字高度范围

# ---------------------------------------------------------------- 连通域
try:
    import numpy as np
    def components(img, thresh=THRESH):
        """8-连通域, 返回 [{'x0','x1','y0','y1','w','h'}] (基于行游程 + 并查集)"""
        a = np.asarray(img)
        H, W = a.shape
        mask = (a < thresh)
        parent, runs = [], []          # runs: (y, start, end) inclusive
        row_runs = []                  # 每行游程索引
        for y in range(H):
            row = mask[y]
            if not row.any():
                row_runs.append([])
                continue
            d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
            starts = np.flatnonzero(d == 1)
            ends   = np.flatnonzero(d == -1) - 1
            cur = []
            for s, e in zip(starts.tolist(), ends.tolist()):
                idx = len(runs)
                runs.append((y, s, e))
                parent.append(idx)
                cur.append(idx)
                # 与上一行 8-邻接的游程合并
                for pi in (row_runs[y - 1] if y > 0 else ()):
                    py, ps, pe = runs[pi]
                    if ps <= e + 1 and s <= pe + 1:
                        ra, rb = find(parent, pi), find(parent, idx)
                        if ra != rb:
                            parent[rb] = ra
            row_runs.append(cur)
        # 归集
        groups = {}
        for i, (y, s, e) in enumerate(runs):
            r = find(parent, i)
            g = groups.get(r)
            if g is None:
                groups[r] = [s, e, y, y]
            else:
                if s < g[0]: g[0] = s
                if e > g[1]: g[1] = e
                if y < g[2]: g[2] = y
                if y > g[3]: g[3] = y
        comps = []
        for s, e, y0, y1 in groups.values():
            comps.append(dict(x0=int(s), x1=int(e), y0=int(y0), y1=int(y1),
                              w=int(e - s + 1), h=int(y1 - y0 + 1)))
        return comps

    def find(parent, i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
except ImportError:                                   # 没有 numpy 时的纯 python 兜底
    def components(img, thresh=THRESH):
        W, H = img.size
        px = img.load()
        mask = [[1 if px[x, y] < thresh else 0 for x in range(W)] for y in range(H)]
        seen = [[0] * W for _ in range(H)]
        comps = []
        for y in range(H):
            for x in range(W):
                if mask[y][x] and not seen[y][x]:
                    st = [(y, x)]; seen[y][x] = 1
                    minx = maxx = x; miny = maxy = y
                    while st:
                        cy, cx = st.pop()
                        minx = min(minx, cx); maxx = max(maxx, cx)
                        miny = min(miny, cy); maxy = max(maxy, cy)
                        for dy in (-1, 0, 1):
                            for dx in (-1, 0, 1):
                                ny, nx = cy + dy, cx + dx
                                if 0 <= ny < H and 0 <= nx < W and mask[ny][nx] and not seen[ny][nx]:
                                    seen[ny][nx] = 1; st.append((ny, nx))
                    comps.append(dict(x0=minx, x1=maxx, y0=miny, y1=maxy,
                                      w=maxx - minx + 1, h=maxy - miny + 1))
        return comps

# ---------------------------------------------------------------- 工具
def right_cluster(comps, gap=GAP):
    """按横向间隔切分, 返回最右一组连通域 (即耳机图标那一组)"""
    groups = []
    for c in sorted(comps, key=lambda c: c['x0']):
        if groups and c['x0'] - groups[-1][-1]['x1'] <= gap:
            groups[-1].append(c)
        else:
            groups.append([c])
    return groups[-1] if groups else []

def norm_vec(img, c, size=20):
    crop = img.crop((c['x0'], c['y0'], c['x1'] + 1, c['y1'] + 1)).resize((size, size), Image.LANCZOS)
    return list(crop.tobytes())

def l1(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / float(len(a))

def ocr_text(path):
    try:
        out = subprocess.run([OCR, path], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ''
    return ' '.join(l.split('\t')[-1] for l in out.strip().split('\n') if l.strip())

def is_digit_box(c):
    return DIG_W[0] <= c['w'] <= DIG_W[1] and DIG_H[0] <= c['h'] <= DIG_H[1]

def is_ren(c):
    return c is not None and REN_W[0] <= c['w'] <= REN_W[1] and REN_H[0] <= c['h'] <= REN_H[1]

# ---------------------------------------------------------------- 主流程
def main():
    files = sorted(f for f in os.listdir(DS) if f.endswith('_hdr.png'))
    if not files:
        print('no _hdr.png in', DS); return 1

    imgs, clusters = {}, {}
    for f in files:
        img = Image.open(os.path.join(DS, f)).convert('L')
        imgs[f] = img
        clusters[f] = right_cluster(components(img))

    # --- 1. 自举耳机图标模板: 各图右侧组最左连通域取众数 ---
    firsts = []
    for f in files:
        cl = clusters[f]
        if cl:
            firsts.append(tuple(norm_vec(imgs[f], cl[0])))
    if not firsts:
        print('no components found'); return 1
    icon_tpl = list(collections.Counter(firsts).most_common(1)[0][0])

    # --- 2. 逐图定位图标 / 数字游程 / 后续「人」 ---
    records = {}
    for f in files:
        cl = clusters[f]
        if not cl:
            records[f] = dict(ok=False, why='empty'); continue
        icon_d, icon_i = min(((l1(norm_vec(imgs[f], c), icon_tpl), i) for i, c in enumerate(cl)))
        if icon_d > 5.0:
            records[f] = dict(ok=False, why='icon not found dist=%.1f' % icon_d); continue
        run = []
        j = icon_i + 1
        while j < len(cl) and is_digit_box(cl[j]) and cl[j]['x0'] - cl[j - 1]['x1'] <= 16:
            run.append(cl[j]); j += 1
        nxt = cl[j] if j < len(cl) else None
        records[f] = dict(ok=True, img=imgs[f], run=run, nxt=nxt,
                          ren_ok=is_ren(nxt), icon_i=icon_i)

    # --- 3. 数字字形样本 + OCR 投票标注 (仅取结构确定: 数字后紧跟「人」) ---
    glyphs = []          # (vec, w, h, file, pos)
    for f in files:
        r = records[f]
        if not r['ok'] or not r['run'] or not r['ren_ok']:
            continue
        x0 = min(c['x0'] for c in r['run']); x1 = max(c['x1'] for c in r['run'])
        y0 = min(c['y0'] for c in r['run']); y1 = max(c['y1'] for c in r['run'])
        crop = r['img'].crop((max(0, x0 - 3), max(0, y0 - 4), x1 + 5, y1 + 4))
        crop = crop.resize((crop.size[0] * 6, crop.size[1] * 6), Image.LANCZOS)
        tmp = '/tmp/_lp_ocr.png'; crop.save(tmp)
        txt = ocr_text(tmp)
        nums = re.findall(r'[0-9]+', txt)
        lab = nums[0] if nums else None
        r['ocr_num'] = (lab if lab and len(lab) == len(r['run']) else None)
        for pos, c in enumerate(r['run']):
            glyphs.append(dict(vec=norm_vec(r['img'], c), w=c['w'], h=c['h'],
                               file=f, pos=pos, lab=(lab[pos] if lab and len(lab) == len(r['run']) else None)))

    # --- 4. 字形聚类 -> 模板库 (票数最多者为该字形代表的数字) ---
    bank = []            # [ [centroid, [ [label, n], ... ] ] ]
    for g in glyphs:
        best, bd = None, 1e9
        for i, item in enumerate(bank):
            d = l1(item[0], g['vec'])
            if d < bd:
                bd, best = d, i
        if best is not None and bd <= BANK_TH:
            cen, votes, n = bank[best]
            n = n + 1
            bank[best][0] = [(a * (n - 1) + b) / n for a, b in zip(cen, g['vec'])]
            bank[best][2] = n
            if g['lab']:
                votes[g['lab']] = votes.get(g['lab'], 0) + 1
        else:
            bank.append([list(g['vec']), ({g['lab']: 1} if g['lab'] else {}), 1])

    tpls = []            # [{'label': '7', 'vec': [...], 'n': k, 'purity': p}]
    for cen, votes, n in bank:
        if votes:
            lab, cnt = max(votes.items(), key=lambda kv: kv[1])
            purity = cnt / float(sum(votes.values()))
        else:
            lab, purity = None, 0.0
        tpls.append(dict(label=lab, vec=cen, n=n, purity=purity, votes=dict(votes)))
    tpls = [t for t in tpls if t['label']]
    print('字形模板库: %d 类, 覆盖 %d 个数字字形' % (len(tpls), len(glyphs)))

    def classify(vec):
        best, bd = None, 1e9
        for t in tpls:
            d = l1(vec, t['vec'])
            if d < bd:
                bd, best = d, t
        return best, bd

    # --- 5. 解析全部文件 ---
    result, fails = {}, []
    ocr_mismatch = []
    for f in files:
        pub = f[:-len('_hdr.png')]
        r = records[f]
        try:
            if not r['ok']:
                raise RuntimeError(r['why'])
            if not r['run'] or not r['ren_ok']:
                # 图标后没有数字, 或数字后面不是「人」-> 🎧 听全文, 无人收听
                result[pub] = 0
                continue
            digits = []
            for c in r['run']:
                t, d = classify(norm_vec(r['img'], c))
                if t is None or d > CLS_TH:
                    raise RuntimeError('digit glyph unclassified (dist=%.1f)' % d)
                digits.append(t['label'])
            result[pub] = int(''.join(digits))
        except Exception as e:
            fails.append((pub, str(e)))

    # --- 6. 与 OCR 交叉核对 (OCR 仅作审计, 不参与最终结果) ---
    for f in files:
        r = records[f]
        pub = f[:-len('_hdr.png')]
        if pub not in result or not r.get('ocr_num'):
            continue
        if int(r['ocr_num']) != result[pub]:
            ocr_mismatch.append((pub, result[pub], r['ocr_num']))

    # --- 7. 输出 ---
    with open('/tmp/listened.json', 'w') as fh:
        json.dump(result, fh, ensure_ascii=False, indent=0, sort_keys=True)

    total = len(files)
    n_ok = len(result)
    print()
    print('=' * 64)
    print('总数: %d   成功: %d   失败: %d' % (total, n_ok, len(fails)))
    if fails:
        print('失败列表(前 20):')
        for pub, why in fails[:20]:
            print('   %s  %s' % (pub, why))
    zeros = [k for k, v in result.items() if v == 0]
    print('结果为 0 (🎧 听全文 / 无人收听): %d 篇' % len(zeros))
    vals = sorted(v for v in result.values() if v > 0)
    if vals:
        print('人数分布: min=%d  p25=%d  median=%d  p75=%d  max=%d' % (
            vals[0], vals[len(vals) // 4], vals[len(vals) // 2],
            vals[3 * len(vals) // 4], vals[-1]))
    by_digit = collections.defaultdict(lambda: [0, 0])   # digit -> [样本数, 纯票数]
    for t in tpls:
        by_digit[t['label']][0] += t['n']
        by_digit[t['label']][1] += round(t['purity'] * t['n'])
    print('模板库(数字: 样本数/OCR 投票纯度): %s' % ', '.join(
        '%s:%d(%.0f%%)' % (d, n, 100.0 * c / max(1, n)) for d, (n, c) in sorted(by_digit.items())))
    print('与 OCR 数字不一致(OCR 6/9 等误读, 以模板为准): %d 篇' % len(ocr_mismatch))
    for pub, ours, theirs in ocr_mismatch[:20]:
        print('   %s  模板=%d  OCR=%s' % (pub, ours, theirs))
    print('输出: /tmp/listened.json')
    print('=' * 64)
    # 已知人工真值
    for pub, expect in (('2026-04-16_11-05', 71), ('2026-11-09_15-07', 73)):
        if pub in result:
            print('真值核对 %s: 脚本=%d 参考=%s %s' % (
                pub, result[pub], expect, 'OK' if abs(result[pub] - expect) <= 1 else 'MISMATCH'))
    return 0

if __name__ == '__main__':
    sys.exit(main())
