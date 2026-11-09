#!/usr/bin/env python3
"""最终补核：甘肃/宁夏/辽宁/云南/东南/山西等剩余卫视台标。"""
import os
import re
import subprocess

UA = 'okhttp/5.3.2'
OUT = '/tmp/logos4'
os.makedirs(OUT, exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'

ITEMS = [
    ('gansu_0123', 'http://112.123.243.37:50085/tsfile/live/0123_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('ningxia_0125', 'http://112.123.243.37:50085/tsfile/live/0125_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('liaoning_0126', 'http://112.123.243.37:50085/tsfile/live/0126_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('liaoning_0121', 'http://101.66.195.232:9901/tsfile/live/0121_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('ningxia_1046', 'http://113.25.252.226:9901/tsfile/live/1046_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('shanxi_0120', 'http://112.123.243.37:50085/tsfile/live/0120_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('yunnan_0119', 'http://101.66.195.232:9901/tsfile/live/0119_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('dongnan_0113', 'http://112.123.243.37:50085/tsfile/live/0113_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('shandong_0131', 'http://101.66.194.176:9901/tsfile/live/0131_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('beitao_0138', 'http://112.123.243.37:50085/tsfile/live/0138_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('zhejiang_0019', 'http://112.123.243.37:50085/tsfile/live/0019_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('hebei_0018', 'http://112.123.243.37:50085/tsfile/live/0018_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('xizang_0141', 'http://112.123.243.37:50085/tsfile/live/0141_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('heilong_0143', 'http://101.66.194.176:9901/tsfile/live/0143_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('qinghai', 'http://63.141.230.178:82/gslb/zbdq5.m3u8?id=gswshd'),
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
    vf = (f"crop=iw*0.34:ih*0.15:0:0,scale=820:-1,pad=iw+280:ih:280:0:black,"
          f"drawtext=fontfile={FONT}:text='{label}':x=20:y=h/2-th/2:fontsize=52:fontcolor=yellow")
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '2',
                    '-i', ts, '-frames:v', '1', '-vf', vf, png, '-y'], capture_output=True)
    if os.path.exists(png):
        pngs.append(png)
        print(f'✓ {label}', flush=True)

if pngs:
    for i in range(0, len(pngs), 4):
        chunk = pngs[i:i + 4]
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error']
        for p in chunk:
            cmd += ['-i', p]
        fc = ''.join(f'[{j}:v]' for j in range(len(chunk))) + f'vstack=inputs={len(chunk)}[v]'
        cmd += ['-filter_complex', fc, '-map', '[v]', f'{OUT}/fin{i//4}.png', '-y']
        subprocess.run(cmd, capture_output=True)
        print(f'fin{i//4}.png 完成')
