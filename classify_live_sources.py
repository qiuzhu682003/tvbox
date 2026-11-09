#!/usr/bin/env python3
"""
分析 113 个直播源文件，分类：
- 成人源（要屏蔽）
- 高质量电视直播源（要保留/优先）
- 死源（404/空）
输出方案，供写入聚合器的直播源列表。
"""
import json, subprocess, concurrent.futures, re

UA = 'okhttp/3.12.0'

raw = subprocess.run(['curl', '-s', '--max-time', '40', '-A', UA, 'https://tv.cc0cd.cc.cd'],
                     capture_output=True, text=True, errors='replace').stdout
d = json.loads(raw)
lives = d.get('lives', [])

srcs = []
for g in lives:
    u = g.get('url') or g.get('api') or ''
    if u.startswith('http'):
        srcs.append({
            'name': g.get('name', '?'),
            'url': u,
            'ua': g.get('ua', ''),
            'timeout': g.get('timeout', 15),
            'playerType': g.get('playerType'),
            'epg': g.get('epg', ''),
        })

# 成人直播源关键词（源名层面）
ADULT_NAME = re.compile(
    r'成人|18|sex|porm|porn|fc2|麻豆|传媒|supjav|javab|番号|伦理|三级|'
    r'自拍|福利|媚|丝袜|诱惑|国产传媒|星空传媒|精东|果冻|天美|几个传媒|'
    r'麻豆传媒|pron|jable|missav|超碰|无码|有码|偷拍|约炮|裸|骚|'
    r'vip源|美腿丝袜|花活|live18|181818|至���|终极|经典|成人电影|珍藏|绝品',
    re.IGNORECASE)

# 高质量电视直播源（源名层面）
GOOD_TV = re.compile(
    r'央视|央视|卫视|稳定|高清|超清|4K|咪咕|江苏移动|河南|地方|全国组播|'
    r'省台|市台|综合|新闻|体育|电影直播|经典电视剧|港澳台|电视直播',
    re.IGNORECASE)


def fetch_src(s):
    cmd = ['curl', '-s', '-L', '--max-time', str(max(int(s['timeout'] or 15), 20)),
           '-A', s['ua'] or UA, s['url']]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
        return s, r.stdout
    except Exception:
        return s, ''


with concurrent.futures.ThreadPoolExecutor(8) as ex:
    fetched = list(ex.map(fetch_src, srcs))

adult, good, dead, other = [], [], [], []
for s, content in fetched:
    lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
    n = len(lines)
    entry = dict(s, channels=n, sample=lines[0][:70] if lines else '')
    if n <= 1 and ('404' in content[:40] or 'error code' in content[:40] or not content.strip()):
        dead.append(entry)
    elif ADULT_NAME.search(s['name']):
        adult.append(entry)
    elif GOOD_TV.search(s['name']):
        good.append(entry)
    else:
        other.append(entry)

print("=" * 92)
print(f"直播源总 {len(srcs)}  →  成人 {len(adult)} | 高质量电视 {len(good)} | 死源 {len(dead)} | 其他 {len(other)}")
print("=" * 92)

print(f"\n【成人源】{len(adult)} 个（合计 {sum(x['channels'] for x in adult)} 频道）—— 必须屏蔽")
for x in sorted(adult, key=lambda e: -e['channels']):
    print(f"   {x['channels']:6d} 频道  {x['name'][:28]:30s} {x['url'][:52]}")

print(f"\n【高质量电视源】{len(good)} 个（合计 {sum(x['channels'] for x in good)} 频道）—— 保留")
for x in sorted(good, key=lambda e: -e['channels']):
    print(f"   {x['channels']:6d} 频道  {x['name'][:28]:30s} {x['url'][:52]}")

print(f"\n【死源】{len(dead)} 个 —— 自动忽略")
print(f"\n【其他】{len(other)} 个（合计 {sum(x['channels'] for x in other)} 频道）")
for x in sorted(other, key=lambda e: -e['channels'])[:20]:
    print(f"   {x['channels']:6d} 频道  {x['name'][:28]:30s}")

json.dump({'adult': adult, 'good': good, 'other': other, 'dead': dead},
          open('/tmp/live_classified.json', 'w'), ensure_ascii=False, indent=1)
print("\n已存 /tmp/live_classified.json")
