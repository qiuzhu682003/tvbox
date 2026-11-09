#!/usr/bin/env python3
"""
扫描当前聚合配置里的所有直播源，测每个源的【真实分片】下载速度，
把「索引通但分片拉不动」的死源标记出来，供人工决定是否剔除。

用法: python3 ~/tvbox/scan_live_sources.py [最大测试源数]
"""
import json, subprocess, concurrent.futures, sys, collections

CONFIG = '/tmp/final_tv.json'
MAX_GROUPS = int(sys.argv[1]) if len(sys.argv) > 1 else 40

d = json.load(open(CONFIG))
lives = d.get('lives', [])

# 按来源组归集，每个组取前 2 个频道做探针
by_group = collections.OrderedDict()
for g in lives:
    gname = g.get('group', '(无名组)')
    chans = g.get('channels', [])
    if not chans:
        continue
    probes = []
    for c in chans[:2]:
        for u in c.get('urls', [])[:1]:
            probes.append((c.get('name'), u))
    if probes:
        by_group.setdefault(gname, []).extend(probes)

items = []
for gname, probes in by_group.items():
    for cn, u in probes[:2]:
        items.append((gname, cn, u))
        if len(items) >= MAX_GROUPS:
            break
    if len(items) >= MAX_GROUPS:
        break


def probe(item):
    gname, cn, u = item
    # 恶意/损坏的源 URL 里可能混入空字节等控制字符，直接跳过
    if not u or any(ord(ch) < 0x20 for ch in u):
        return (gname, cn, 'skip', 'skip', '-', '-')
    # 1) 索引
    r = subprocess.run(['curl', '-s', '--max-time', '8', '-A', 'okhttp/3.12.0', u],
                       capture_output=True, text=True, errors='replace')
    idx = 'ok' if r.stdout.strip().startswith('#EXTM3U') else 'bad'
    seg = None
    for line in r.stdout.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            # 去掉控制字符/空字节，否则 subprocess 会炸
            seg = ''.join(ch for ch in line if ord(ch) >= 0x20)
            break
    if not seg:
        return (gname, cn, idx, '-', '-', '-')
    # 2) 分片
    try:
        r2 = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}|%{time_total}|%{speed_download}',
             '--max-time', '20', '-A', 'okhttp/3.12.0', seg],
            capture_output=True, text=True, errors='replace')
    except ValueError:
        return (gname, cn, idx, 'bad-url', '-', '-')
    p = r2.stdout.split('|')
    if len(p) < 3:
        return (gname, cn, idx, 'err', '-', '-')
    code = p[0]
    t = float(p[1]) if p[1] else 0
    sp = int(p[2]) / 1024 if p[2].isdigit() else 0
    return (gname, cn, idx, code, f"{t:.1f}s", f"{sp:.0f}KB/s")


print(f"共 {len(items)} 个探针，并发 8 路测试中…\n")
with concurrent.futures.ThreadPoolExecutor(8) as ex:
    results = list(ex.map(probe, items))

good, slow, dead = [], [], []
print(f"{'来源组':22s}{'频道':14s}{'索引':6s}{'HTTP':6s}{'耗时':8s}{'速度'}")
print('-' * 72)
for gname, cn, idx, code, t, sp in results:
    print(f"{gname[:21]:22s}{str(cn)[:13]:14s}{idx:6s}{str(code):6s}{t:8s}{sp}")
    if code == '200' and t and float(t.rstrip('s')) < 4:
        good.append((gname, cn, sp))
    elif code == '200':
        slow.append((gname, cn, t, sp))
    else:
        dead.append((gname, cn, code))

print(f"\n✅ 快 (<4s): {len(good)}   ⚠️ 慢: {len(slow)}   ❌ 不通: {len(dead)}")
if slow:
    print("\n慢源:", sorted({g for g, _, _, _ in slow}))
if dead:
    print("\n死源:", sorted({g for g, _, _ in dead}))
