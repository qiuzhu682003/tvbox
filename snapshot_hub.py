#!/usr/bin/env python3
"""同一时刻批量抓台标（newlive 编号漂移检测）。

对 113.57 那台的 hls/1..23 全部在**同一时刻**各抓一帧，拼图后人工核对，
用来判断「编号 → 频道」是否稳定。
"""
import os
import re
import subprocess

UA = 'okhttp/5.3.2'
OUT = '/tmp/snap'
os.makedirs(OUT, exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
HUB = 'http://113.57.140.161:10081/newlive/live/hls'


def fetch(url, t=10):
    r = subprocess.run(['curl', '-s', '--max-time', str(t), '-A', UA, url],
                       capture_output=True, text=True, errors='replace')
    return r.stdout


def absolute(base, ref):
    if ref.startswith('http'):
        return ref
    m = re.match(r'(https?://[^/]+)(/.*)?', base)
    host = m.group(1)
    if ref.startswith('/'):
        return host + ref
    return host + (m.group(2) or '/').rsplit('/', 1)[0] + '/' + ref


ok = []
for n in list(range(1, 24)):
    url = f'{HUB}/{n}/live.m3u8'
    idx = fetch(url)
    if not idx.strip().startswith('#EXTM3U'):
        continue
    seg = None
    for line in idx.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            seg = absolute(url, line)
            break
    if not seg:
        continue
    ts = f'{OUT}/s{n}.ts'
    subprocess.run(['curl', '-s', '--max-time', '18', '-A', UA, '-o', ts, seg],
                   capture_output=True)
    if not os.path.exists(ts) or os.path.getsize(ts) < 10000:
        continue
    p = f'{OUT}/s{n}.png'
    vf = (f"crop=iw*0.42:ih*0.13:0:0,scale=900:-1,pad=iw+230:ih:230:0:black,"
          f"drawtext=fontfile={FONT}:text='hls/{n}':x=12:y=h/2-th/2:fontsize=36:fontcolor=yellow")
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '2',
                    '-i', ts, '-frames:v', '1', '-vf', vf, p, '-y'], capture_output=True)
    if os.path.exists(p):
        ok.append(p)
        print(f'✓ hls/{n}', flush=True)

for i in range(0, len(ok), 8):
    ch = ok[i:i + 8]
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error']
    for p in ch:
        cmd += ['-i', p]
    fc = ''.join(f'[{j}:v]' for j in range(len(ch))) + f'vstack=inputs={len(ch)}[v]'
    cmd += ['-filter_complex', fc, '-map', '[v]', f'{OUT}/S{i//8}.png', '-y']
    subprocess.run(cmd, capture_output=True)
    print(f'S{i//8}.png ← {len(ch)}', flush=True)
