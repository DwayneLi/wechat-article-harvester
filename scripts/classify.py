
import os, re, json, collections
DIR='/Users/tg/Library/CloudStorage/OneDrive-个人/桌面/公众号写作/他人公众号文章下载/缓慢思考'
FILES=[f for f in os.listdir(DIR) if f.endswith('.md') and not f.startswith('_')]

def fm_get(txt):
    m=re.match(r'^---\s*\n([\s\S]*?)\n---', txt)
    if not m: return {}
    d={}
    for line in m.group(1).split('\n'):
        mm=re.match(r'^([a-z_]+):\s*(.*)$', line)
        if mm: d[mm.group(1)]=mm.group(2).strip().strip('"')
    return d

COMPANY='拼多多|腾讯|茅台|苹果|亚马逊|特斯拉|阿里|美团|京东|谷歌|Google|Meta|Facebook|Netflix|奈飞|Costco|好市多|比亚迪|NVO|诺和诺德|AppLovin|Uber|滴滴|字节|小米|美的|海尔|招商银行|平安|伯克希尔|可口可乐|喜诗|华盛顿邮报|蓝筹印花|GEICO|美国运通|富国银行|卡夫|亨氏|IBM|微软|英伟达|宁德时代|隆基|药明|海底捞|星巴克|耐克|LV|爱马仕|宇通|格力|万科|恒大|融创|贝壳|B站|快手|网易|搜狐|新浪|微博|知乎|蔚来|理想|小鹏|零跑|广汽|赛力斯|泡泡玛特|蜜雪冰城|瑞幸|SpaceX|Ebay|Yelp|Zulily|Homejoy|HelloFresh|Pinterest|Twitter|Instagram|On Demand'
INVESTOR='巴菲特|Buffett|Buffet|芒格|格雷厄姆|段永平|李录|张磊|高瓴|红杉|彼得·林奇|林奇|卡拉曼|马克斯|泰瑞|Terry|桥水|达里奥|索罗斯|费雪|邓普顿|格林布拉特|阿克曼|Burry|贝索斯|乔布斯|马斯克|Klarman|Benchmark|A16Z|YC|Y-Combinator|Seth|查理|李光耀|科比|MM|大师|查理'
BIZ='创业|公司|商业|融资|增长|产品|CEO|团队|行业|生意|独角兽|IPO|扩张|董事会|创始人|VC|投资银行|销售|市场|模式|竞争|并购|A轮|广告|电商'
BOOK='《|书|演讲|访谈|格言|笔记|摘录|来自|总结|教训|读书|读的|信|致辞|对话|启示|法则|清单|世界观'
INVEST='投资|价值|估值|安全边际|能力圈|风险|复利|周期|市场|股票|价格|财富|投机|确定性|概率|芒格|股东|输钱|赚钱|收益|回报|亏|生意|现金|资产|价格|买入|卖出|金钱|钱'

def tags_for(title, body):
    t=title
    tags=[]
    if '股东信' in t:
        tags.append('股东信解读')
        if re.search('巴菲特|芒格|伯克希尔|巴菲特', t) or '喜诗' in t: tags.append('投资人与机构')
        return tags
    if re.search(BOOK, t):
        tags.append('书与博客')
    if re.search(COMPANY, t) or re.search('财报|资产表|估值|IPO|招股|毛利|内在价值', t):
        tags.append('公司分析')
    if re.search(INVESTOR, t):
        tags.append('投资人与机构')
    if re.search(BIZ, t):
        tags.append('商业与创业')
    if re.search(INVEST, t) and '投资理念' not in tags:
        tags.append('投资理念')
    if not tags:
        tags=['生活与思考']
        if re.search('思考|人生|生活|学习|愚蠢|聪明|恐惧|焦虑|快乐|习惯|时间|错误|秘密|故事', t):
            tags=['生活与思考']
    # dedupe preserve
    out=[]
    for x in tags:
        if x not in out: out.append(x)
    return out[:3]

res={}
cnt=collections.Counter()
rows=[]
for f in FILES:
    txt=open(os.path.join(DIR,f),encoding='utf-8',errors='replace').read()
    d=fm_get(txt)
    title=d.get('title') or os.path.splitext(f)[0]
    body=txt
    tg=tags_for(title, body)
    res[f]=tg
    for x in tg: cnt[x]+=1
    rows.append((d.get('publish',''), title, tg))
print(json.dumps(cnt, ensure_ascii=False))
json.dump(res, open('/tmp/tags.json','w'), ensure_ascii=False, indent=1)
rows.sort(key=lambda x:x[0], reverse=True)
import random
random.seed(3)
for p,t,tg in random.sample(rows, 18): print(p[:10], t[:30], '->', tg)
