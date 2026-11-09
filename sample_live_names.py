#!/usr/bin/env python3
"""对【其他】类直播源抽样看频道名，人工确认是否成人内容。"""
import json, subprocess, re

UA = 'okhttp/3.12.0'
cls = json.load(open('/tmp/live_classified.json'))

# 优先检查频道数最多的几个
cands = sorted(cls['other'], key=lambda e: -e['channels'])[:12]

ADULT_HINT = re.compile(
    r'性|裸|骚|媚|诱惑|丝袜|制服|OL|御姐|萝莉|少妇|操|做爱|无码|有码|'
    r'三级|伦理|自拍|约炮|福利|AV|色情|18|av|sex|私拍|偷拍|巨乳|'
    r'播|-room|ROOM|MM|HOT|热播', re.IGNORECASE)

for s in cands:
    cmd = ['curl', '-s', '-L', '--max-time', '25', '-A', s.get('ua') or UA, s['url']]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
    except Exception:
        continue
    lines = [l for l in r.stdout.split('\n') if l.strip() and not l.strip().startswith('#')]
    names = []
    for l in lines[:120]:
        if ',' in l:
            names.append(l.split(',')[0].strip())
        else:
            names.append(l[:24].strip())
    # 命中成人特征的频道名
    bad = [n for n in names if ADULT_HINT.search(n)]
    ratio = len(bad) / max(len(names), 1)
    flag = '🔴成人' if ratio > 0.15 else ('🟡擦边' if bad else '🟢正常')
    print(f"{flag} {s['name'][:26]:28s} 频道{len(lines):6d}  成人特征 {len(bad):3d}/{len(names)} ({ratio*100:.0f}%)")
    print(f"      样本: {names[:6]}")
    if bad:
        print(f"      成人样本: {bad[:6]}")
    print()
