#!/usr/bin/env python3
"""更宽口径识别成人/擦边源：
1) 直接看符号标记（🔞 等）
2) 看站点 key（很多成人源 key 就是域名或拼音缩写，站点名反而干净）
3) 按 api 域名黑名单
输出真实站点名样本，供人工确认。"""
import json, collections, re

CFG = '/tmp/cur.json'
d = json.load(open(CFG))
sites = d.get('sites', [])

# 明显的成人 api 域名（独立于站点名）
ADULT_DOMAIN = [
    'pgxdy', 'msnii', 'xrbsp', 'jav', 'av', 'sex', 'porn', 'm3u8.pw', '91',
    '福利', '伦理', '三级', 'soav', 'souav', 'cg', 'mdx', 't28', 'jvid', 'hentai',
    'xiaohua', 'mimi', 'kk', 'hanami', 'yandex', '18', 'meijiushe', '福利姬',
]

# 站点名/标记里的成人符号与词
SYMBOL = ['🔞', '❌成人', '成人', '番号', '黄片', '无码', '有码', '三级', '伦理',
          '色情', '情色', '福利', '偷拍', '自慰', '裸', '裸聊', '约炮', '重口',
          '萝莉', '少妇', '熟女', '御姐', '丝袜', '诱惑', '黑丝', '白丝', '制服',
          '春堂', '搜视', '里番', '魔性', '福利区', '18禁', '禁漫', '里番', 'jav',
          'JAV', 'porn', 'Porn', 'sex', 'Sex', '裸聊', '绅士', '里番动画',
          '媚', '诱惑', '美腿', '翘臀', '爆乳', '丝袜诱惑', '偷窥', '无码资源',
          '福利资源', 'AV资源', 'av资源']

print(f"总站点: {len(sites)}\n")


def scan(s):
    name = str(s.get('name', ''))
    key = str(s.get('key', ''))
    api = str(s.get('api', ''))
    reasons = []
    low_all = (name + ' ' + key + ' ' + api).lower()
    for sym in SYMBOL:
        if sym.lower() in low_all:
            reasons.append(sym)
            break
    for dom in ADULT_DOMAIN:
        if dom.lower() in low_all:
            reasons.append('dom:' + dom)
            break
    return reasons


hits = []
for s in sites:
    r = scan(s)
    if r:
        hits.append((s, r))

print(f"宽口径命中: {len(hits)} 个 ({len(hits)/len(sites)*100:.1f}%)")
print()
print(f"{'key':22s}{'name':66s}{'type':6s}原因")
print('-' * 120)
for s, r in hits[:80]:
    print(f"{str(s.get('key',''))[:21]:22s}{str(s.get('name',''))[:65]:66s}{str(s.get('type','')):6s}{','.join(r[:2])}")

print()
print("=" * 70)
print("命中站点按 api 域名归类")
print("=" * 70)
dom = collections.Counter()
for s, r in hits:
    api = str(s.get('api', ''))
    m = re.search(r'https?://([^/]+)', api)
    dom[m.group(1) if m else '(type=3 本地爬虫)'] += 1
for k, v in dom.most_common(20):
    print(f"  {v:4d}  {k}")
