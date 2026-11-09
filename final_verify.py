#!/usr/bin/env python3
"""最终验收：拉取实际对外的配置，确认成人内容已清除、正常内容保留。"""
import json, subprocess, re

URL = 'http://192.168.3.61:5678/'

ADULT = [
    '偷窥', '自慰', '做爱', '口交', '性爱', '裸聊', '裸播', '裸体', '全裸',
    '强姦', '强奸', '调教', '露出', '偷情', '情趣', '约炮', '一夜情',
    'AV女优', 'AV主播', 'AV资源', '番号', '里番', '福利姬', '痴女', '嫩模',
    '麻豆传媒', '星辰传媒', '国产传媒', '蜜桃传媒', '麻豆视频',
    '三级片', '伦理片', '18禁', '禁漫', 'Hentai',
    'Pornhub', 'xvideos', 'xhamster', 'redtube', 'Jable', 'SupJav', 'MissAV',
    'JavBus', 'JavDb', '超碰', '小萝莉爱爱', '重口味爱好者', '媚宅', '涩涩',
    '色播', '色猫', '大尺度', '香艳', '艳遇', '情涩', '巨乳', '爆乳', '奶子',
    '骚货', '骚年', '女优', '色情片', '重口味', '小电影', '福利', '无码', '有码',
    '偷拍', '自拍', '裸', '骚', '淫', '媚', '诱惑', '丝袜', '制服', '萝莉',
    '少妇', '熟女', '麻豆', '传媒', '成人', 'av', 'sex', 'porn', 'AV',
]

SAFE = ['速度与激情', '回家的诱惑', '犯罪现场', '赤裸惊情', '生活娱乐',
        '综合频道', '新闻频道', 'CCTV', '卫视', '少儿', '购物', '农业农村']

r = subprocess.run(['curl', '-s', '--max-time', '200', URL],
                   capture_output=True, text=True, errors='replace')
d = json.loads(r.stdout)

sites = d.get('sites', [])
lives = d.get('lives', [])
parses = d.get('parses', [])

print("=" * 68)
print("最终验收")
print("=" * 68)
print(f"点播站点: {len(sites)}   直播组: {len(lives)}   解析: {len(parses)}")

n_ch = sum(len(g.get('channels', [])) for g in lives)
print(f"直播频道总数: {n_ch}")


def check(items, label):
    bad = []
    for it in items:
        blob = str(it)
        if any(s in blob for s in SAFE):
            continue
        for a in ADULT:
            if a.lower() in blob.lower():
                bad.append((blob[:58], a))
                break
    print(f"\n【{label}】残留可疑: {len(bad)}")
    for b in bad[:12]:
        print(f"   {b[0]}   <-- {b[1]}")
    return len(bad)


bad_sites = check([f"{s.get('key','')} {s.get('name','')} {s.get('api','')}" for s in sites], '点播站点')
bad_live = check([f"{g.get('group','')} {c.get('name','')}"
                  for g in lives for c in g.get('channels', [])], '直播频道')
bad_parse = check([f"{p.get('key','')} {p.get('name','')}" for p in parses], '解析')

print("\n" + "=" * 68)
print("正常内容抽查（必须还在）")
print("=" * 68)
allnames = [str(s.get('name', '')) for s in sites]
livenames = [str(c.get('name', '')) for g in lives for c in g.get('channels', [])]
livegroups = [str(g.get('group', '')) for g in lives]

for kw in ['央视', '卫视', 'CCTV', '红果', '茶杯狐', '人人影视', '老张影视',
           '影探', '饭太硬', '苹果', '搜狗', '免费']:
    hit = [n for n in allnames if kw in n][:1]
    print(f"  点播 {kw:8s}: {'✅ ' + hit[0][:44] if hit else '❌ 缺失'}")

for kw in ['央视', 'CCTV', '卫视', '全国组播', '清舒', '咪咕', '江苏移动', '湖南', '浙江']:
    hit = [g for g in livegroups if kw in g][:1]
    print(f"  直播组 {kw:8s}: {'✅ ' + hit[0][:40] if hit else '—'}")

print("\n" + "=" * 68)
total = bad_sites + bad_live + bad_parse
print(f"总计残留: {total}  {'✅ 全部清除' if total == 0 else '⚠️ 仍有残留'}")
