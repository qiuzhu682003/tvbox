#!/usr/bin/env python3
"""抓直播首帧 → 裁全宽顶栏（含左右两侧台标）→ 叠标签 → 拼图。

输出：/tmp/logos2/<批次>.png，每张最多 4 条，左侧有 drawtext 标签。
"""
import os
import re
import subprocess
import sys

UA = 'okhttp/5.3.2'
OUT = '/tmp/logos2'
os.makedirs(OUT, exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'

HUB = 'http://113.57.140.161:10081/newlive/live/hls'
HUB2 = 'http://120.40.39.246:352/newlive/live/hls'
TS = 'http://112.123.243.37:50085/tsfile/live'
TS2 = 'http://101.66.198.18:9901/tsfile/live'
TS3 = 'http://101.66.198.84:9901/tsfile/live'
TS4 = 'http://111.59.139.82:11888/tsfile/live'

ITEMS = [
    # (标签, m3u8)
    ('h1', f'{HUB}/1/live.m3u8'),
    ('h2', f'{HUB}/2/live.m3u8'),
    ('h3', f'{HUB}/3/live.m3u8'),
    ('h4', f'{HUB}/4/live.m3u8'),
    ('h5', f'{HUB}/5/live.m3u8'),
    ('h6', f'{HUB}/6/live.m3u8'),
    ('h7', f'{HUB}/7/live.m3u8'),
    ('h8', f'{HUB}/8/live.m3u8'),
    ('h10', f'{HUB}/10/live.m3u8'),
    ('h11', f'{HUB}/11/live.m3u8'),
    ('h12', f'{HUB}/12/live.m3u8'),
    ('h13', f'{HUB}/13/live.m3u8'),
    ('h14', f'{HUB}/14/live.m3u8'),
    ('h15', f'{HUB}/15/live.m3u8'),
    ('h16', f'{HUB}/16/live.m3u8'),
    ('h17', f'{HUB}/17/live.m3u8'),
    ('h31', f'{HUB}/31/live.m3u8'),
    ('h18', f'{HUB}/18/live.m3u8'),
    ('h19', f'{HUB}/19/live.m3u8'),
    ('h20', f'{HUB}/20/live.m3u8'),
    ('g1', f'{HUB2}/1/live.m3u8'),
    ('g4', f'{HUB2}/4/live.m3u8'),
    ('g6', f'{HUB2}/6/live.m3u8'),
    ('g15', f'{HUB2}/15/live.m3u8'),
    ('g16', f'{HUB2}/16/live.m3u8'),
    ('g17', f'{HUB2}/17/live.m3u8'),
    ('t0001', f'{TS}/0001_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0002', f'{TS}/0002_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0003', f'{TS}/0003_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0004', f'{TS}/0004_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0005', f'{TS}/0005_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0007', f'{TS}/0007_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0008', f'{TS}/0008_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0009', f'{TS}/0009_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0010', f'{TS}/0010_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0011', f'{TS}/0011_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0012', f'{TS}/0012_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0013', f'{TS}/0013_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0014', f'{TS}/0014_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0015', f'{TS}/0015_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0016', f'{TS}/0016_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0017', f'{TS}/0017_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0018', f'{TS}/0018_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0019', f'{TS}/0019_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0020', f'{TS}/0020_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0022', f'{TS}/0122_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0023', f'{TS}/0123_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0024', f'{TS}/0124_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0025', f'{TS}/0125_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0126', f'{TS}/0126_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0127', f'{TS}/0127_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0128', f'{TS}/0128_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0130_1', f'{TS}/0130_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0130_2', f'{TS}/0130_2.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0135', f'{TS}/0135_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0137', f'{TS}/0137_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0138', f'{TS}/0138_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0139', f'{TS}/0139_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0141', f'{TS}/0141_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0142', f'{TS}/0142_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0143', f'{TS}/0143_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0112', f'{TS}/0112_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0113', f'{TS}/0113_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0116', f'{TS}/0116_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t0117', f'{TS}/0117_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t1000', f'{TS}/1000_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t1001', f'{TS}/1001_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t1002', f'{TS}/1002_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('t1015a', 'http://153.0.171.163:85/tsfile/live/1015_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('t1016a', 'http://124.228.160.112:9901/tsfile/live/0016_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('f1036', 'http://120.198.95.220:9901/tsfile/live/1036_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('f1037', 'http://120.198.95.220:9901/tsfile/live/1037_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('f0136', f'{TS2}/0136_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('f0123', f'{TS3}/0123_1.m3u8?key=txiptv&playlive=0&authid=0'),
    ('f0139', f'{TS4}/0139_1.m3u8?key=txiptv&playlive=1&authid=0'),
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


def grab(label, url):
    seg = first_segment(url)
    if not seg:
        print(f'  ✗ {label}: 索引不通', flush=True)
        return None
    ts = f'{OUT}/{label}.ts'
    subprocess.run(['curl', '-s', '--max-time', '25', '-A', UA, '-o', ts, seg],
                   capture_output=True)
    if not os.path.exists(ts) or os.path.getsize(ts) < 10000:
        print(f'  ✗ {label}: 分片拉取失败', flush=True)
        return None
    png = f'{OUT}/{label}.png'
    # 全宽顶栏 15%，左右都覆盖到；再叠左侧标签
    vf = (f"crop=iw:ih*0.15:0:0,scale=1100:-1,"
          f"pad=iw+220:ih:220:0:black,"
          f"drawtext=fontfile={FONT}:text='{label}':x=20:y=h/2-th/2:fontsize=54:fontcolor=yellow")
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '2',
                    '-i', ts, '-frames:v', '1', '-vf', vf, png, '-y'],
                   capture_output=True)
    if not os.path.exists(png):
        print(f'  ✗ {label}: 抽帧失败', flush=True)
        return None
    print(f'  ✓ {label}', flush=True)
    return png


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    items = [(l, u) for l, u in ITEMS if not only or l in only or l[0] in only]
    for start in range(0, len(items), 4):
        chunk = items[start:start + 4]
        pngs = []
        for label, url in chunk:
            p = grab(label, url)
            if p:
                pngs.append(p)
        if not pngs:
            continue
        idx = start // 4
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error']
        for p in pngs:
            cmd += ['-i', p]
        fc = ''.join(f'[{i}:v]' for i in range(len(pngs))) + f'vstack=inputs={len(pngs)}[v]'
        cmd += ['-filter_complex', fc, '-map', '[v]', f'{OUT}/grp{idx:02d}.png', '-y']
        subprocess.run(cmd, capture_output=True)
        print(f'grp{idx:02d}.png 完成', flush=True)


if __name__ == '__main__':
    main()
