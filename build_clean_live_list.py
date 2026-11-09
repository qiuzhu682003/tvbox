#!/usr/bin/env python3
"""
生成「干净的直播源清单」：
1. 从 113 个直播源里剔除成人源
2. 剔除死源（404/空）
3. 保留高质量电视直播源
4. 剔除明显是成人频道的源（按频道名采样判定）
输出到 /tmp/live_kept.json
"""
import json, subprocess, re, concurrent.futures

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
            'logo': g.get('logo', ''),
        })

# ── 明确的成人直播源（源名）──
ADULT_NAME = re.compile(
    r'成人|18|sex|porm|porn|fc2|麻豆|传媒|supjav|番号|伦理|三级|'
    r'自拍|福利|媚|丝袜|诱惑|国产传媒|星空传媒|精东|果冻|天美|几个传媒|'
    r'pron|jable|missav|超碰|无码|有码|偷拍|约炮|裸|骚|'
    r'vip源|美腿丝袜|花活|live18|181818|绝品|珍藏', re.IGNORECASE)

# ── 频道名级成人特征（用于判定「其他」类里的擦边源）──
ADULT_CH = re.compile(
    r'情色|裸|骚|媚|诱惑|丝袜|制服|御姐|萝莉|少妇|操|做爱|无码|有码|'
    r'三级|伦理|自拍|约炮|福利|色情|私拍|偷拍|巨乳|奶子|'
    r'情涩|里番|番号|约炮|无码|开房|自慰', re.IGNORECASE)


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

kept, dropped_adult, dropped_dead = [], [], []
for s, content in fetched:
    lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
    n = len(lines)
    # 死源判定
    if n <= 1 and ('404' in content[:40] or 'error code' in content[:40] or not content.strip()):
        dropped_dead.append(s)
        continue
    # 成人源名判定
    if ADULT_NAME.search(s['name']):
        dropped_adult.append((s, n, '源名'))
        continue
    # 频道名判定（采样前 300 行）
    names = []
    for l in lines[:300]:
        names.append(l.split(',')[0].strip() if ',' in l else l[:24].strip())
    bad = sum(1 for nm in names if ADULT_CH.search(nm))
    ratio = bad / max(len(names), 1)
    if ratio > 0.05:
        dropped_adult.append((s, n, f'频道名 {ratio*100:.0f}%'))
        continue
    kept.append(dict(s, channels=n, adult_ratio=round(ratio, 4)))

print(f"总 {len(srcs)}  →  保留 {len(kept)} | 屏蔽成人 {len(dropped_adult)} | 死源 {len(dropped_dead)}")
print(f"保留源合计频道: {sum(k['channels'] for k in kept)}")
print(f"屏蔽掉的成人频道: {sum(n for _, n, _ in dropped_adult)}")

print("\n【被屏蔽的成人源】")
for s, n, why in sorted(dropped_adult, key=lambda x: -x[1]):
    print(f"  {n:6d} 频道  {s['name'][:26]:28s} ({why})")

print("\n【保留的高质量源 Top 20】")
for k in sorted(kept, key=lambda e: -e['channels'])[:20]:
    print(f"  {k['channels']:6d} 频道  {k['name'][:26]:28s} 成人率 {k['adult_ratio']*100:.1f}%")

json.dump(kept, open('/tmp/live_kept.json', 'w'), ensure_ascii=False, indent=1)
json.dump([{'name': s['name'], 'url': s['url'], 'channels': n, 'why': w}
           for s, n, w in dropped_adult], open('/tmp/live_dropped.json', 'w'),
          ensure_ascii=False, indent=1)
print("\n已存 /tmp/live_kept.json 与 /tmp/live_dropped.json")
