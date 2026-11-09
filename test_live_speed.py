#!/usr/bin/env python3
# 测试各直播源的真实分片下载速度（播放器实际体验）
import json, subprocess, concurrent.futures

d = json.load(open('/tmp/final_tv.json'))
groups = []
for g in d.get('lives', []):
    for c in g.get('channels', []):
        for u in c.get('urls', [])[:1]:
            groups.append((g.get('group', '')[:16], c.get('name'), u))

seen = set()
uniq = []
for gname, cn, u in groups:
    if u in seen:
        continue
    seen.add(u)
    uniq.append((gname, cn, u))
    if len(uniq) >= 6:
        break


def test(item):
    gname, cn, u = item
    r = subprocess.run(
        ['curl', '-s', '--max-time', '10', '-A', 'okhttp/3.12.0', u],
        capture_output=True, text=True)
    seg = None
    for line in r.stdout.split('\n'):
        if line.strip() and not line.startswith('#'):
            seg = line.strip()
            break
    if not seg:
        return (gname, cn, '无分片', '-', '-')
    r2 = subprocess.run(
        ['curl', '-s', '-o', '/dev/null', '-w',
         '%{http_code}|%{size_download}|%{time_total}|%{speed_download}',
         '--max-time', '25', '-A', 'okhttp/3.12.0', seg],
        capture_output=True, text=True)
    p = r2.stdout.split('|')
    if len(p) < 4:
        return (gname, cn, 'err', '-', '-')
    size_kb = int(p[1]) / 1024 if p[1].isdigit() else 0
    return (gname, cn, p[0], f"{p[2]}s", f"{size_kb:.0f}KB/s")


with concurrent.futures.ThreadPoolExecutor(6) as ex:
    results = list(ex.map(test, uniq))

print(f"{'来源组':18s}{'频道':12s}{'分片HTTP':10s}{'耗时':8s}{'速度'}")
print('-' * 62)
for gname, cn, code, t, sp in results:
    print(f"{gname:18s}{str(cn):12s}{str(code):10s}{t:8s}{sp}")
