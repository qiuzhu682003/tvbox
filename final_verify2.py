#!/usr/bin/env python3
"""
精确复检：修正上一版的误判（av 命中 bravo/travel、骚命中骚火电影=正常影视站、
福利命中"粉丝福利"、裸命中"裸奔的蜗牛"=乐队名）。
只报告【确定是成人】的内容。
"""
import json, subprocess, re

URL = 'http://192.168.3.61:5678/'
r = subprocess.run(['curl', '-s', '--max-time', '200', URL],
                   capture_output=True, text=True, errors='replace')
d = json.loads(r.stdout)

sites = d.get('sites', [])
lives = d.get('lives', [])
parses = d.get('parses', [])

# ── 确定成人（精确词组，不做子串误伤）──
ADULT_EXACT = [
    '偷窥', '自慰', '做爱', '口交', '性爱', '裸聊', '裸播', '全裸', '一丝不挂',
    '强姦', '强奸', '调教', '露出癖', '偷情', '情趣酒店', '约炮', '一夜情',
    'AV女优', 'AV主播', 'AV资源', 'AV影片', '日AV', '无码流出', '无码视频',
    '有码流出', '日本AV', '番号', '里番', '福利姬', '痴女', '嫩模', '素人',
    '无码资源', '有码资源', '麻豆传媒', '星辰传媒', '国产传媒', '蜜桃传媒',
    '麻豆视频', '爱豆传媒', '三级片', '伦理片', '18禁', '禁漫', 'Hentai',
    'Pornhub', 'xvideos', 'xhamster', 'redtube', 'Jable', 'SupJav',
    'MissAV', 'JavBus', 'JavDb', '超碰', '小萝莉爱爱', '重口味爱好者',
    '媚宅', '涩涩', '色播', '色猫', '大尺度', '香艳', '艳遇', '情涩',
    '巨乳', '爆乳', '奶子', '骚货', '女优', '色情片', 'AV片', '偷拍',
    '主播福利', '福利姬', '激情时刻', '性福时刻', '春色满园', 'av', 'AV资源',
    'Porm', 'Sex', 'FC2', 'Pron', 'Jable', 'MissAV', '麻豆', '传媒',
    '自慰', '偷窥', '做爱', '口交', '性福', '裸体',
]

# ── 明确正常（命中即放行）──
SAFE = [
    '速度与激情', '回家的诱惑', '犯罪现场', '赤裸惊情', '生活娱乐', '综合频道',
    '新闻频道', 'CCTV', '卫视', '少儿', '购物', '农业农村', '骚火电影',
    '骚火', '白嫖资源', '裸奔的蜗牛', '漫威', '粉丝福利', '了不起的',
    'bravo', 'travel', 'avaz', 'gigavision', 'Travel', 'Bravo',
    '知��', '综艺', '影视', '动漫', '体育', '音乐', '新闻', '纪录',
]


def scan(text):
    low = text.lower()
    for s in SAFE:
        if s.lower() in low:
            return None
    for a in ADULT_EXACT:
        if a.lower() in low:
            return a
    return None


print("=" * 70)
print("精确复检")
print("=" * 70)

# 点播
site_hits = []
for s in sites:
    blob = f"{s.get('key','')} {s.get('name','')} {s.get('api','')}"
    r_ = scan(blob)
    if r_:
        site_hits.append((str(s.get('name', ''))[:56], r_))

# 直播
live_hits = []
for g in lives:
    gname = str(g.get('group', ''))
    for c in g.get('channels', []):
        blob = f"{c.get('name','')} {gname}"
        r_ = scan(blob)
        if r_:
            live_hits.append((gname[:20], str(c.get('name', ''))[:44], r_))

# 解析
parse_hits = []
for p in parses:
    blob = f"{p.get('key','')} {p.get('name','')}"
    r_ = scan(blob)
    if r_:
        parse_hits.append((str(p.get('key', ''))[:30], r_))

print(f"点播残留: {len(site_hits)}")
for h in site_hits[:12]:
    print(f"   {h[0]}  <-- {h[1]}")
print(f"\n直播残留: {len(live_hits)}")
for h in live_hits[:15]:
    print(f"   {h[0]:22s} {h[1]:46s} <-- {h[2]}")
print(f"\n解析残留: {len(parse_hits)}")
for h in parse_hits[:10]:
    print(f"   {h[0]:32s} <-- {h[1]}")

print()
print(f"总计: {len(site_hits) + len(live_hits) + len(parse_hits)}")
