#!/usr/bin/env python3
"""串行测试直播分片真实速度（避免并发争抢带宽导致误判），
并与 GitHub 静态版 tvbox.json 的直播源做对比。"""
import json, subprocess, time, sys

UA = 'okhttp/3.12.0'


def clean(s):
    return ''.join(ch for ch in s if ord(ch) >= 0x20)


def probe(url, label):
    try:
        r = subprocess.run(['curl', '-s', '--max-time', '10', '-A', UA, url],
                           capture_output=True, text=True, errors='replace')
    except Exception as e:
        return (label, 'ERR', 0, 0)
    seg = None
    for line in r.stdout.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            seg = clean(line)
            break
    if not seg:
        return (label, 'no-seg', 0, 0)
    try:
        t0 = time.time()
        r2 = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}|%{size_download}|%{time_total}',
             '--max-time', '30', '-A', UA, seg],
            capture_output=True, text=True, errors='replace')
    except Exception:
        return (label, 'ERR', 0, 0)
    p = r2.stdout.split('|')
    if len(p) < 3:
        return (label, 'ERR', 0, 0)
    code = p[0]
    size = int(p[1]) if p[1].isdigit() else 0
    t = float(p[2]) if p[2] else 0
    sp = size / 1024 / t if t > 0 and size > 0 else 0
    return (label, code, size / 1024, sp)


def collect(cfg_path, label):
    d = json.load(open(cfg_path))
    lives = d.get('lives', [])
    groups = []
    seen = set()
    for g in lives:
        gn = g.get('group', '?')
        for c in g.get('channels', []):
            for u in c.get('urls', [])[:1]:
                if u in seen:
                    continue
                seen.add(u)
                groups.append((f"{gn[:18]} / {c.get('name','')[:10]}", u))
                break
            else:
                continue
            break
    return groups


print("=" * 78)
print("【串行测试 · 当前 iMac 聚合版】前 8 个直播流")
print("=" * 78)
cur = collect('/tmp/final_tv.json', 'current')
for lbl, u in cur[:8]:
    label, code, kb, sp = probe(u, lbl)
    status = f"{code} | {kb:.0f}KB | {sp:.0f}KB/s"
    flag = '✅快' if sp > 3000 else ('⚠️慢' if sp > 0 else '❌不通')
    print(f"{flag}  {lbl:32s} {status}")

print()
print("=" * 78)
print("【对比 · GitHub 静态版 tvbox.json】直播组数量与抽样")
print("=" * 78)
try:
    static = json.load(open('/Users/qiuzhu/tvbox/tvbox.json'))
    sl = static.get('lives', [])
    print(f"静态版 lives 组数: {len(sl)}")
    print(f"当前版 lives 组数: {len(json.load(open('/tmp/final_tv.json')).get('lives', []))}")
    print()
    for lbl, u in collect('/Users/qiuzhu/tvbox/tvbox.json', 'static')[:8]:
        label, code, kb, sp = probe(u, lbl)
        status = f"{code} | {kb:.0f}KB | {sp:.0f}KB/s"
        flag = '✅快' if sp > 3000 else ('⚠️慢' if sp > 0 else '❌不通')
        print(f"{flag}  {lbl:32s} {status}")
except Exception as e:
    print("静态版读取失败:", e)
