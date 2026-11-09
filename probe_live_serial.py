#!/usr/bin/env python3
"""串行、逐个测直播源【真实分片】速度，区分索引通/不通。
输出可直接用于决定是否剔除某些直播组。"""
import json, subprocess, time

UA = 'okhttp/3.12.0'


def clean(s):
    return ''.join(ch for ch in s if ord(ch) >= 0x20)


def probe(url):
    """返回 (索引状态, 分片HTTP, 分片KB, KB/s)"""
    try:
        r = subprocess.run(['curl', '-s', '--max-time', '10', '-A', UA, url],
                           capture_output=True, text=True, errors='replace')
    except Exception:
        return ('ERR', 'ERR', 0, 0)
    if not r.stdout.strip().startswith('#EXTM3U'):
        return ('no-idx', '-', 0, 0)
    seg = None
    for line in r.stdout.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            seg = clean(line)
            break
    if not seg:
        return ('idx-ok', 'no-seg', 0, 0)
    try:
        r2 = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}|%{size_download}|%{time_total}',
             '--max-time', '30', '-A', UA, seg],
            capture_output=True, text=True, errors='replace')
    except Exception:
        return ('idx-ok', 'ERR', 0, 0)
    p = r2.stdout.split('|')
    if len(p) < 3:
        return ('idx-ok', 'ERR', 0, 0)
    code = p[0]
    size = int(p[1]) if p[1].isdigit() else 0
    t = float(p[2]) if p[2] else 0
    sp = size / 1024 / t if t > 0 and size > 0 else 0
    return ('idx-ok', code, size / 1024, sp)


d = json.load(open('/tmp/final_tv.json'))
lives = d.get('lives', [])

# 每组取 2 个频道探针
by_group = {}
order = []
for g in lives:
    gn = g.get('group', '?')
    if gn not in by_group:
        by_group[gn] = []
        order.append(gn)
    for c in g.get('channels', []):
        for u in c.get('urls', [])[:1]:
            by_group[gn].append((c.get('name', ''), u))
            break
        if len(by_group[gn]) >= 2:
            break

print(f"共 {len(order)} 个直播组，逐组串行测速中…\n")
print(f"{'直播组':34s}{'频道':14s}{'索引':9s}{'分片':7s}{'大小':9s}{'速度'}")
print('-' * 88)

group_result = {}
for gn in order:
    probes = by_group[gn][:2]
    best = None
    detail = []
    for cn, u in probes:
        idx, code, kb, sp = probe(u)
        detail.append((cn, idx, code, kb, sp))
        if code == '200' and (best is None or sp > best[1]):
            best = (cn, sp)
    for cn, idx, code, kb, sp in detail:
        flag = '✅' if code == '200' else '❌'
        print(f"{gn[:33]:34s}{str(cn)[:13]:14s}{idx:9s}{flag}{str(code):6s}{kb:8.0f}KB{sp:8.0f}KB/s")
    group_result[gn] = best

print('\n' + '=' * 88)
good = [g for g, b in group_result.items() if b and b[1] > 1500]
mid = [g for g, b in group_result.items() if b and 0 < b[1] <= 1500]
dead = [g for g, b in group_result.items() if not b]
print(f"✅ 快(>1500KB/s) {len(good)} 组: {good}")
print(f"⚠️ 慢(<=1500KB/s) {len(mid)} 组: {mid}")
print(f"❌ 不通 {len(dead)} 组: {dead}")
