#!/usr/bin/env python3
"""补验剩余未核台标的频道 + 抓候选线路（CCTV-16/17）。"""
import os
import re
import subprocess

UA = 'okhttp/5.3.2'
OUT = '/tmp/logos3'
os.makedirs(OUT, exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
TS = 'http://112.123.243.37:50085/tsfile/live'
HUB = 'http://113.57.140.161:10081/newlive/live/hls'
G = 'http://120.40.39.246:352/newlive/live/hls'

ITEMS = [
    ('t0131', f'{TS}/0131_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0120', f'{TS}/0120_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0125', f'{TS}/0125_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0123', f'{TS}/0123_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('g2', f'{G}/2/live.m3u8'),
    ('g3', f'{G}/3/live.m3u8'),
    ('g17', f'{G}/17/live.m3u8'),
    ('g18', f'{G}/18/live.m3u8'),
    ('h20', f'{HUB}/20/live.m3u8'),
    ('h21', f'{HUB}/21/live.m3u8'),
]


def fetch(url, t=12):
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


def first_seg(url):
    idx = fetch(url)
    if not idx.strip().startswith('#EXTM3U'):
        return None
    for line in idx.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            return absolute(url, line)
    return None


pngs = []
for label, url in ITEMS:
    seg = first_seg(url)
    if not seg:
        print(f'✗ {label}: 索引不通', flush=True)
        continue
    ts = f'{OUT}/{label}.ts'
    subprocess.run(['curl', '-s', '--max-time', '25', '-A', UA, '-o', ts, seg], capture_output=True)
    if not os.path.exists(ts) or os.path.getsize(ts) < 10000:
        print(f'✗ {label}: 分片失败', flush=True)
        continue
    png = f'{OUT}/{label}.png'
    vf = (f"crop=iw:ih*0.15:0:0,scale=1100:-1,pad=iw+260:ih:260:0:black,"
          f"drawtext=fontfile={FONT}:text='{label}':x=20:y=h/2-th/2:fontsize=54:fontcolor=yellow")
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '2',
                    '-i', ts, '-frames:v', '1', '-vf', vf, png, '-y'], capture_output=True)
    if os.path.exists(png):
        pngs.append(png)
        print(f'✓ {label}', flush=True)

if pngs:
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error']
    for p in pngs:
        cmd += ['-i', p]
    fc = ''.join(f'[{i}:v]' for i in range(len(pngs))) + f'vstack=inputs={len(pngs)}[v]'
    cmd += ['-filter_complex', fc, '-map', '[v]', f'{OUT}/rest.png', '-y']
    subprocess.run(cmd, capture_output=True)
    print(f'rest.png 完成（{len(pngs)} 条）')
