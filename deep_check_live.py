#!/usr/bin/env python3
"""深度抽查几个超大直播源：随机取多个位置的频道，看是否成人内容。"""
import json, subprocess, random

UA = 'okhttp/3.12.0'
kept = json.load(open('/tmp/live_kept.json'))

# 频道数最多的几个，逐个深查
targets = [k for k in sorted(kept, key=lambda e: -e['channels'])[:6]]

ADULT = ('裸', '骚', '做爱', '无码', '有码', '三级', '伦理', '自拍', '约炮',
         '福利', '色情', '私拍', '偷拍', '巨乳', '奶子', 'AV', 'av', 'sex',
         'Sex', 'porn', 'Porn', '番号', '媚', '诱惑', '丝袜', '制服', '萝莉',
         '少妇', '御姐', '麻豆', '传媒', '18+', '成人', '激情', '艳', '情色',
         '现场', '偷情', '诱惑', '美腿', '诱惑', '露出', '制服诱惑', 'OL', '女优')

for s in targets:
    cmd = ['curl', '-s', '-L', '--max-time', '30', '-A', s.get('ua') or UA, s['url']]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
    except Exception:
        continue
    lines = [l for l in r.stdout.split('\n') if l.strip() and not l.strip().startswith('#')]
    n = len(lines)
    random.seed(7)
    # 随机取 3 段，每段 60 行
    picks = []
    for frac in (0.05, 0.35, 0.65):
        start = min(int(n * frac), max(n - 60, 0))
        picks.extend(lines[start:start + 60])
    names = []
    for l in picks:
        nm = l.split(',')[0].strip() if ',' in l else l[:30].strip()
        names.append(nm)
    bad = [nm for nm in names if any(a in nm for a in ADULT)]
    ratio = len(bad) / max(len(names), 1)
    flag = '🔴' if ratio > 0.1 else ('🟡' if bad else '🟢')
    print(f"{flag} {s['name'][:24]:26s} 共{n:6d}频道  抽样{len(names):3d}  成人{len(bad):3d} ({ratio*100:.1f}%)")
    print(f"      中段样本: {names[60:68]}")
    if bad:
        print(f"      成人样本: {bad[:8]}")
    print()
