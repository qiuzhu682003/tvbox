#!/usr/bin/env python3
"""抓直播首帧 + 裁台标 + 拼图，用于逐条核对「频道名 vs 实际画面」。

用法：python3 grab_logos.py
输出：/tmp/logos/batchX.png，每张最多 4 条，竖排（台标在左上角）。
"""
import os
import re
import subprocess
import sys

UA = 'okhttp/5.3.2'
OUT = '/tmp/logos'
os.makedirs(OUT, exist_ok=True)

HUB = 'http://113.57.140.161:10081/newlive/live/hls'
TS = 'http://112.123.243.37:50085/tsfile/live'

# (批次, 标签, m3u8 地址)
BATCHES = [
    ('A', 'newlive hls/1', f'{HUB}/1/live.m3u8'),
    ('A', 'newlive hls/2', f'{HUB}/2/live.m3u8'),
    ('A', 'newlive hls/3', f'{HUB}/3/live.m3u8'),
    ('A', 'newlive hls/4', f'{HUB}/4/live.m3u8'),
    ('B', 'newlive hls/5', f'{HUB}/5/live.m3u8'),
    ('B', 'newlive hls/6', f'{HUB}/6/live.m3u8'),
    ('B', 'newlive hls/7', f'{HUB}/7/live.m3u8'),
    ('B', 'newlive hls/8', f'{HUB}/8/live.m3u8'),
    ('C', 'newlive hls/10', f'{HUB}/10/live.m3u8'),
    ('C', 'newlive hls/11', f'{HUB}/11/live.m3u8'),
    ('C', 'newlive hls/12', f'{HUB}/12/live.m3u8'),
    ('C', 'newlive hls/13', f'{HUB}/13/live.m3u8'),
    ('D', 'newlive hls/14', f'{HUB}/14/live.m3u8'),
    ('D', 'newlive hls/15', f'{HUB}/15/live.m3u8'),
    ('D', 'newlive hls/16', f'{HUB}/16/live.m3u8'),
    ('D', 'newlive hls/17', f'{HUB}/17/live.m3u8'),
    ('E', 'newlive hls/31', f'{HUB}/31/live.m3u8'),
    ('E', 'tsfile 0010', f'{TS}/0010_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('E', 'tsfile 0017', f'{TS}/0017_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('E', 'tsfile 1002', f'{TS}/1002_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('F', 'tsfile 0124', f'{TS}/0124_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('F', 'tsfile 0127', f'{TS}/0127_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('F', 'tsfile 0130_1', f'{TS}/0130_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('F', 'tsfile 0130_2', f'{TS}/0130_2.m3u8?key=txiptv&playlive=0&authid=0'),
    ('G', 'tsfile 0135', f'{TS}/0135_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('G', 'tsfile 0122', f'{TS}/0122_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('G', 'tsfile 0128', f'{TS}/0128_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('G', 'tsfile 0123', f'{TS}/0123_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('H', 'tsfile 0141', f'{TS}/0141_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('H', 'tsfile 0142', f'{TS}/0142_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('H', 'tsfile 0125', f'{TS}/0125_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('H', 'tsfile 0116', f'{TS}/0116_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('I', 'tsfile 0117', f'{TS}/0117_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('I', 'tsfile 0126', f'{TS}/0126_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('I', 'tsfile 0112', f'{TS}/0112_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('I', 'tsfile 0137', f'{TS}/0137_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('J', 'tsfile 0113', f'{TS}/0113_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('J', 'tsfile 0018', f'{TS}/0018_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('J', 'tsfile 0120', f'{TS}/0120_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('J', 'tsfile 0143', f'{TS}/0143_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('K', 'tsfile 0001', f'{TS}/0001_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('K', 'tsfile 0003', f'{TS}/0003_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('K', 'tsfile 0004', f'{TS}/0004_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('K', 'tsfile 0005', f'{TS}/0005_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('L', 'tsfile 0007', f'{TS}/0007_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('L', 'tsfile 0008', f'{TS}/0008_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('L', 'tsfile 0009', f'{TS}/0009_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('L', 'tsfile 0011', f'{TS}/0011_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('M', 'tsfile 0012', f'{TS}/0012_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('M', 'tsfile 0013', f'{TS}/0013_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('M', 'tsfile 0014', f'{TS}/0014_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('M', 'tsfile 0015', f'{TS}/0015_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('N', 'tsfile 0016', f'{TS}/0016_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('N', 'tsfile 0019', f'{TS}/0019_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('N', 'tsfile 1000', f'{TS}/1000_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('N', 'tsfile 1001', f'{TS}/1001_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('O', '153.0 1015', 'http://153.0.171.163:85/tsfile/live/1015_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('O', '124.228 0016', 'http://124.228.160.112:9901/tsfile/live/0016_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('O', '120.198 1036', 'http://120.198.95.220:9901/tsfile/live/1036_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('O', '120.198 1037', 'http://120.198.95.220:9901/tsfile/live/1037_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('P', '111.59 0139', 'http://111.59.139.82:11888/tsfile/live/0139_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('P', '101.66 0136', 'http://101.66.198.18:9901/tsfile/live/0136_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('P', '101.66 0123', 'http://101.66.198.84:9901/tsfile/live/0123_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('P', '112.27 0138', 'http://112.27.5.218:9901/tsfile/live/faacts/0138_1.m3u8?key=txiptv&playlive=0&authid=0'),
]


def fetch_text(url, timeout=12):
    r = subprocess.run(['curl', '-s', '--max-time', str(timeout), '-A', UA, url],
                       capture_output=True, text=True, errors='replace')
    return r.stdout


def absolute(base, ref):
    if ref.startswith('http'):
        return ref
    if ref.startswith('//'):
        return 'http:' + ref
    m = re.match(r'(https?://[^/]+)(/.*)?', base)
    if not m:
        return ref
    host = m.group(1)
    if ref.startswith('/'):
        return host + ref
    return host + (m.group(2) or '/').rsplit('/', 1)[0] + '/' + ref


def first_segment(url):
    idx = fetch_text(url)
    if not idx.strip().startswith('#EXTM3U'):
        return None
    for line in idx.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            return absolute(url, line)
    return None


def grab(label, url, batch):
    seg = first_segment(url)
    if not seg:
        print(f'  ✗ {label}: 索引不通', flush=True)
        return None
    ts = f'/tmp/logos/{batch}_{label.replace(" ", "_").replace("/", "_")}.ts'
    r = subprocess.run(['curl', '-s', '--max-time', '25', '-A', UA, '-o', ts, seg],
                       capture_output=True, text=True)
    if not os.path.exists(ts) or os.path.getsize(ts) < 10000:
        print(f'  ✗ {label}: 分片拉取失败', flush=True)
        return None
    png = ts[:-3] + '.png'
    # 裁左上角台标区 + 放大
    vf = 'crop=iw*0.26:ih*0.13:0:0,scale=900:-1'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '2',
                    '-i', ts, '-frames:v', '1', '-vf', vf, png, '-y'],
                   capture_output=True)
    if not os.path.exists(png):
        print(f'  ✗ {label}: 抽帧失败', flush=True)
        return None
    print(f'  ✓ {label}: {os.path.getsize(png)}B', flush=True)
    return png


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    batches = {}
    for b, label, url in BATCHES:
        if only and b not in only:
            continue
        batches.setdefault(b, []).append((label, url))
    for b, items in batches.items():
        pngs = []
        for label, url in items:
            p = grab(label, url, b)
            if p:
                pngs.append(p)
        if not pngs:
            continue
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error']
        for p in pngs:
            cmd += ['-i', p]
        fc = ''.join(f'[{i}:v]' for i in range(len(pngs))) + f'vstack=inputs={len(pngs)}[v]'
        cmd += ['-filter_complex', fc, '-map', '[v]', f'{OUT}/batch{b}.png', '-y']
        subprocess.run(cmd, capture_output=True)
        print(f'batch{b}.png 完成（{len(pngs)} 条）', flush=True)


if __name__ == '__main__':
    main()
