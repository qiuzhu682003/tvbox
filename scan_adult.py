#!/usr/bin/env python3
"""扫描点播站点，找出成人/擦边内容，并按来源归类，便于定向屏蔽。"""
import json, collections, re

CFG = '/tmp/cur.json'
d = json.load(open(CFG))
sites = d.get('sites', [])
parses = d.get('parses', [])
lives = d.get('lives', [])

# 成人/擦边关键词（大小写不敏感）
ADULT_KW = [
    '福利', '伦理', '三级', '国产', '自慰', '偷拍', '约炮', '裸', '成人', '无码', '有码',
    '小电影', '重口', ' porn', ' porn', 'sex', 'av', '福利姬', '传媒', '色情', '情色',
    '媚', '诱惑', '私密', '炮', '91', 'gv', '偷窥', '慰', '明星', '麻豆', '无码',
    '黑丝', '白丝', '制服', '诱惑', '御姐', '萝莉', '少妇', '熟女', '丝袜', '诱惑',
    'JVID', 'MDX', 'T28', '番号', '无码', '破解', '里番', '里番', 'acg', 'jav',
]

# 明显正常的优质关键词（用于判断"高质量源"）
GOOD_KW = ['央视', 'CCTV', '卫视', '高清', '蓝光', '4K', '豆瓣', '时光', '追剧', '热播',
           '电影', '电视剧', '综艺', '动漫', '纪录片', '少儿', '新闻', '体育']


def is_adult(blob):
    low = blob.lower()
    for k in ADULT_KW:
        if k.lower() in low:
            return True
    return False


adult = []
for s in sites:
    blob = ' '.join(str(s.get(k, '')) for k in ('key', 'name', 'api'))
    if is_adult(blob):
        adult.append(s)

print(f"总站点: {len(sites)}   解析: {len(parses)}   直播组: {len(lives)}")
print(f"疑似成人/擦边站点: {len(adult)} ({len(adult)/max(len(sites),1)*100:.1f}%)")
print()

# 按 api 域名归类，看成人源集中在哪些源
by_domain = collections.Counter()
for s in adult:
    api = str(s.get('api', ''))
    m = re.search(r'https?://([^/]+)', api)
    dom = m.group(1) if m else '(无api)'
    by_domain[dom] += 1

print("成人站点按域名分布 (Top 25):")
for dom, n in by_domain.most_common(25):
    print(f"  {n:4d}  {dom}")

print()
print("成人站点样本 (前 30):")
for s in adult[:30]:
    print(f"  {s.get('key','')[:18]:20s} {s.get('name','')[:66]}")

# 解析(parses)里有没有成人
print()
adult_parses = [p for p in parses if is_adult(' '.join(str(p.get(k, '')) for k in ('key', 'name', 'type', 'ext')))]
print(f"疑似成人解析: {len(adult_parses)}/{len(parses)}")
for p in adult_parses[:15]:
    print(f"  {p.get('key','')[:20]:22s} {str(p.get('name',''))[:50]:52s} type={p.get('type')}")
