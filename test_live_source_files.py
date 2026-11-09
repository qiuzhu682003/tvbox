#!/usr/bin/env python3
"""
测试 tvyuan 的各个【直播源文件】的可用性与频道质量。
直播源文件是 txt（频道名,url 格式），聚合时下载展开。
"""
import json, subprocess, random, concurrent.futures

UA = 'okhttp/3.12.0'

raw = subprocess.run(['curl', '-s', '--max-time', '40', '-A', UA, 'https://tv.cc0cd.cc.cd'],
                     capture_output=True, text=True, errors='replace').stdout
d = json.loads(raw)
lives = d.get('lives', [])

srcs = []
for g in lives:
    u = g.get('url') or g.get('api') or ''
    if u.startswith('http'):
        srcs.append((g.get('name', '?'), u, g.get('ua', ''), g.get('timeout', 15)))

print(f"直播源文件 {len(srcs)} 个\n")


def fetch_src(item):
    name, url, ua, to = item
    cmd = ['curl', '-s', '-L', '--max-time', str(max(int(to or 15), 20)), '-A', ua or UA, url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
        return (name, url, r.stdout)
    except Exception:
        return (name, url, '')


with concurrent.futures.ThreadPoolExecutor(6) as ex:
    fetched = list(ex.map(fetch_src, srcs))

print(f"{'源名':24s}{'状态':10s}{'频道数':>8s}  样本")
print('-' * 88)
good_sources = []
for name, url, content in fetched:
    if not content.strip():
        print(f"{name[:23]:24s}{'❌ 空':10s}")
        continue
    lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
    n = len(lines)
    sample = lines[0][:60] if lines else ''
    flag = '✅' if n > 10 else ('⚠️' if n > 0 else '❌')
    print(f"{name[:23]:24s}{flag:10s}{n:>8d}  {sample}")
    if n > 10:
        good_sources.append((name, url, lines))

print()
print(f"可用直播源文件: {len(good_sources)} 个")
# 存下来供下一步逐频道测速
json.dump([{'name': n, 'url': u, 'lines': l[:60]} for n, u, l in good_sources],
          open('/tmp/live_sources.json', 'w'), ensure_ascii=False)
print("已存 /tmp/live_sources.json")
