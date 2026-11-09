#!/usr/bin/env python3
"""终验：抓候选清单所有 URL 的台标，按 8 条一组拼图，供人工核对。"""
import os
import re
import subprocess
import sys

UA = 'okhttp/5.3.2'
OUT = '/tmp/final'
os.makedirs(OUT, exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'

TS = 'http://112.123.243.37:50085/tsfile/live'
TS2 = 'http://101.66.198.18:9901/tsfile/live'
TS3 = 'http://101.66.198.84:9901/tsfile/live'
TS4 = 'http://101.66.194.176:9901/tsfile/live'
TS5 = 'http://101.66.195.232:9901/tsfile/live'
TS6 = 'http://101.66.194.29:9901/tsfile/live'
TS7 = 'http://113.25.252.226:9901/tsfile/live'
TS8 = 'http://36.136.38.87:9901/tsfile/live'
HUB = 'http://113.57.140.161:10081/newlive/live/hls'
G = 'http://120.40.39.246:352/newlive/live/hls'
MISC = 'http://153.0.171.163:85/tsfile/live'
MISC2 = 'http://124.228.160.112:9901/tsfile/live'
MISC3 = 'http://120.198.95.220:9901/tsfile/live'
MISC4 = 'http://111.59.139.82:11888/tsfile/live'

Q = '?key=txiptv&playlive=0&authid=0'
Q1 = '?key=txiptv&playlive=1&authid=0'

# (标签, 频道猜测, url)
CANDS = [
    # ── 央视 tsfile 家族 ──
    ('a01', 'CCTV-1', f'{TS}/0001_1.m3u8{Q}'),
    ('a02', 'CCTV-2', f'{TS}/0002_1.m3u8{Q}'),
    ('a03', 'CCTV-3', f'{TS}/0003_1.m3u8{Q}'),
    ('a04', 'CCTV-4', f'{TS}/0004_1.m3u8{Q}'),
    ('a05', 'CCTV-5', f'{TS}/0005_1.m3u8{Q}'),
    ('a06', 'CCTV-6', f'{TS}/0007_1.m3u8{Q}'),
    ('a07', 'CCTV-7', f'{TS}/0008_1.m3u8{Q}'),
    ('a08', 'CCTV-8', f'{TS}/0009_1.m3u8{Q}'),
    ('a09', 'CCTV-9', f'{TS}/0010_1.m3u8{Q}'),
    ('a10', 'CCTV-10', f'{TS}/0011_1.m3u8{Q}'),
    ('a11', 'CCTV-11', f'{TS}/0012_1.m3u8{Q}'),
    ('a12', 'CCTV-12', f'{TS}/0013_1.m3u8{Q}'),
    ('a13', 'CCTV-13', f'{TS}/0014_1.m3u8{Q}'),
    ('a14', 'CCTV-14', f'{TS}/0015_1.m3u8{Q}'),
    ('a15', 'CCTV-15', f'{TS}/0016_1.m3u8{Q}'),
    ('a16', '江苏卫视', f'{TS}/0017_1.m3u8{Q}'),
    ('a17', '河北卫视', f'{TS}/0018_1.m3u8{Q}'),
    ('a18', '浙江卫视', f'{TS}/0019_1.m3u8{Q}'),
    # ── 央视 newlive ──
    ('b01', 'CCTV-1', f'{HUB}/1/live.m3u8'),
    ('b02', 'CCTV-2', f'{HUB}/2/live.m3u8'),
    ('b03', 'CCTV-3', f'{HUB}/3/live.m3u8'),
    ('b04', 'CCTV-4', f'{HUB}/4/live.m3u8'),
    ('b05', 'CCTV-5', f'{HUB}/5/live.m3u8'),
    ('b06', 'CCTV-6', f'{HUB}/6/live.m3u8'),
    ('b07', 'CCTV-7', f'{HUB}/7/live.m3u8'),
    ('b08', 'CCTV-8', f'{HUB}/8/live.m3u8'),
    ('b09', 'CCTV-9?', f'{HUB}/9/live.m3u8'),
    ('b10', 'CCTV-10', f'{HUB}/10/live.m3u8'),
    ('b11', 'CCTV-11', f'{HUB}/11/live.m3u8'),
    ('b12', 'CCTV-12', f'{HUB}/12/live.m3u8'),
    ('b13', 'CCTV-13', f'{HUB}/13/live.m3u8'),
    ('b14', 'CCTV-14?', f'{HUB}/14/live.m3u8'),
    ('b15', 'CCTV-15', f'{HUB}/15/live.m3u8'),
    ('b16', '?', f'{HUB}/16/live.m3u8'),
    ('b17', '?', f'{HUB}/17/live.m3u8'),
    ('b18', '?', f'{HUB}/18/live.m3u8'),
    ('b19', '?', f'{HUB}/19/live.m3u8'),
    ('b20', '?', f'{HUB}/20/live.m3u8'),
    ('b31', '?', f'{HUB}/31/live.m3u8'),
    # ── 第二台 newlive ──
    ('c16', '?', f'{G}/16/live.m3u8'),
    ('c17', '?', f'{G}/17/live.m3u8'),
    ('c18', '?', f'{G}/18/live.m3u8'),
    # ── 卫视 tsfile ──
    ('d01', '湖南卫视', f'{TS}/1002_1.m3u8{Q}'),
    ('d02', '?', f'{TS}/0122_1.m3u8{Q}'),
    ('d03', '?', f'{TS}/0123_1.m3u8{Q}'),
    ('d04', '?', f'{TS}/0124_1.m3u8{Q}'),
    ('d05', '?', f'{TS}/0125_1.m3u8{Q}'),
    ('d06', '深圳卫视', f'{TS}/0126_1.m3u8{Q}'),
    ('d07', '北京卫视', f'{TS}/0127_1.m3u8{Q}'),
    ('d08', '天津卫视', f'{TS}/0128_1.m3u8{Q}'),
    ('d09', '?', f'{TS}/0130_1.m3u8{Q}'),
    ('d10', '?', f'{TS}/0130_2.m3u8{Q}'),
    ('d11', '?', f'{TS}/0131_1.m3u8{Q}'),
    ('d12', '?', f'{TS}/0135_1.m3u8{Q}'),
    ('d13', '?', f'{TS}/0137_1.m3u8{Q}'),
    ('d14', '?', f'{TS}/0138_1.m3u8{Q}'),
    ('d15', '?', f'{TS}/0141_1.m3u8{Q}'),
    ('d16', '?', f'{TS}/0142_1.m3u8{Q}'),
    ('d17', '?', f'{TS}/0143_1.m3u8{Q}'),
    ('d18', '?', f'{TS}/0112_1.m3u8{Q}'),
    ('d19', '?', f'{TS}/0113_1.m3u8{Q}'),
    ('d20', '?', f'{TS}/0116_1.m3u8{Q}'),
    ('d21', '?', f'{TS}/0117_1.m3u8{Q}'),
    ('d22', '?', f'{TS}/0120_1.m3u8{Q}'),
    # ── 其他主机 ──
    ('e01', '?', f'{TS2}/0136_1.m3u8{Q}'),
    ('e02', '?', f'{TS3}/0123_1.m3u8{Q}'),
    ('e03', '?', f'{TS4}/0131_1.m3u8{Q}'),
    ('e04', '?', f'{TS4}/0138_1.m3u8{Q}'),
    ('e05', '?', f'{TS4}/0143_1.m3u8{Q}'),
    ('e06', '?', f'{TS5}/0119_1.m3u8{Q}'),
    ('e07', '?', f'{TS5}/0121_1.m3u8{Q}'),
    ('e08', '?', f'{TS5}/0138_1.m3u8{Q}'),
    ('e09', '?', f'{TS6}/0019_1.m3u8{Q}'),
    ('e10', '?', f'{TS7}/1046_1.m3u8{Q1}'),
    ('e11', '?', f'{TS8}/0135_1.m3u8{Q}'),
    ('e12', '河南卫视', f'{MISC4}/0139_1.m3u8{Q1}'),
    ('e13', 'CCTV-5+?', f'{MISC}/1015_1.m3u8{Q1}'),
    ('e14', 'CCTV-16?', f'{MISC2}/0016_1.m3u8{Q1}'),
    ('e15', '凤凰中文', f'{MISC3}/1036_1.m3u8{Q1}'),
    ('e16', '凤凰资讯', f'{MISC3}/1037_1.m3u8{Q1}'),
    ('e17', 'CCTV-1?', f'{MISC3}/1015_1.m3u8?key=txiptv&playlive=1&down=1'),
    ('e18', 'CCTV-3?', f'{MISC3}/1017_1.m3u8?key=txiptv&playlive=1&down=1'),
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


def main():
    only = set(sys.argv[1:])
    pngs = []
    meta = []
    for label, guess, url in CANDS:
        if only and label not in only:
            continue
        seg = first_seg(url)
        if not seg:
            print(f'✗ {label} 索引不通 {url}', flush=True)
            continue
        ts = f'{OUT}/{label}.ts'
        subprocess.run(['curl', '-s', '--max-time', '25', '-A', UA, '-o', ts, seg], capture_output=True)
        if not os.path.exists(ts) or os.path.getsize(ts) < 10000:
            print(f'✗ {label} 分片失败', flush=True)
            continue
        png = f'{OUT}/{label}.png'
        vf = (f"crop=iw*0.30:ih*0.14:0:0,scale=780:-1,pad=iw+340:ih:340:0:black,"
              f"drawtext=fontfile={FONT}:text='{label}':x=18:y=h/2-th/2:fontsize=50:fontcolor=yellow")
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '2',
                        '-i', ts, '-frames:v', '1', '-vf', vf, png, '-y'], capture_output=True)
        if os.path.exists(png):
            pngs.append(png)
            meta.append((label, guess))
            print(f'✓ {label} ({guess})', flush=True)
    for i in range(0, len(pngs), 8):
        chunk = pngs[i:i + 8]
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error']
        for p in chunk:
            cmd += ['-i', p]
        fc = ''.join(f'[{j}:v]' for j in range(len(chunk))) + f'vstack=inputs={len(chunk)}[v]'
        cmd += ['-filter_complex', fc, '-map', '[v]', f'{OUT}/F{i//8}.png', '-y']
        subprocess.run(cmd, capture_output=True)
        labels = ' '.join(m[0] for m in meta[i:i + 8])
        print(f'F{i//8}.png ← {labels}', flush=True)


if __name__ == '__main__':
    main()
