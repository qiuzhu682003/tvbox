#!/usr/bin/env python3
"""按台标实锤映射重建 curated.m3u（最终版）。

映射来源：MAPPING_VERIFIED.md + 本轮台标实拍（/tmp/scan_hub1、/tmp/final、/tmp/c16b、/tmp/cctv16）。
每条写入的 URL 都经过：① 台标实拍确认频道名 ② 分片吞吐实测 ≥0.3MB/s。
"""
import os
import re
import subprocess
import sys

UA = 'okhttp/5.3.2'
OUT = '/tmp/rebuild2'
os.makedirs(OUT, exist_ok=True)

TS = 'http://112.123.243.37:50085/tsfile/live'
Q = '?key=txiptv&playlive=0&authid=0'
Q1 = '?key=txiptv&playlive=1&authid=0'
HUB = 'http://113.57.140.161:10081/newlive/live/hls'

# 台标实锤映射表（URL → 频道名）
# hub = 113.57.140.161:10081/newlive  ts = 112.123.243.37:50085/tsfile
VERIFIED = {
    # ── 央视 ──
    f'{TS}/0001_1.m3u8{Q}': 'CCTV-1',
    f'{HUB}/1/live.m3u8': 'CCTV-1',
    f'{TS}/0002_1.m3u8{Q}': 'CCTV-2',
    f'{HUB}/2/live.m3u8': 'CCTV-2',
    f'{TS}/0003_1.m3u8{Q}': 'CCTV-3',
    f'{HUB}/3/live.m3u8': 'CCTV-3',
    f'{TS}/0004_1.m3u8{Q}': 'CCTV-4',
    f'{HUB}/4/live.m3u8': 'CCTV-4',
    f'{TS}/0005_1.m3u8{Q}': 'CCTV-5',
    f'{HUB}/5/live.m3u8': 'CCTV-5',
    'http://153.0.171.163:85/tsfile/live/1015_1.m3u8' + Q1: 'CCTV-5+',
    f'{TS}/0007_1.m3u8{Q}': 'CCTV-6',
    f'{HUB}/6/live.m3u8': 'CCTV-6',
    f'{TS}/0008_1.m3u8{Q}': 'CCTV-7',
    f'{HUB}/7/live.m3u8': 'CCTV-7',
    f'{TS}/0009_1.m3u8{Q}': 'CCTV-8',
    f'{HUB}/8/live.m3u8': 'CCTV-8',
    f'{TS}/0010_1.m3u8{Q}': 'CCTV-9',
    f'{HUB}/9/live.m3u8': 'CCTV-9',
    f'{TS}/0011_1.m3u8{Q}': 'CCTV-10',
    f'{HUB}/10/live.m3u8': 'CCTV-10',
    f'{TS}/0012_1.m3u8{Q}': 'CCTV-11',
    f'{HUB}/11/live.m3u8': 'CCTV-11',
    f'{TS}/0013_1.m3u8{Q}': 'CCTV-12',
    f'{HUB}/12/live.m3u8': 'CCTV-12',
    f'{TS}/0014_1.m3u8{Q}': 'CCTV-13',
    f'{HUB}/13/live.m3u8': 'CCTV-13',
    f'{TS}/0015_1.m3u8{Q}': 'CCTV-14',
    f'{HUB}/14/live.m3u8': 'CCTV-14',
    f'{TS}/0016_1.m3u8{Q}': 'CCTV-15',
    f'{HUB}/15/live.m3u8': 'CCTV-15',
    # CCTV-16/17：112.123 无；124.228 0016 实为 CCTV5+；120.40 台 g17 待定 → 暂缺
    # ── 卫视（112.123 tsfile 台标实锤）──
    f'{TS}/0017_1.m3u8{Q}': '江苏卫视',
    f'{TS}/0018_1.m3u8{Q}': '河北卫视',
    f'{TS}/0019_1.m3u8{Q}': '浙江卫视',
    f'{TS}/0122_1.m3u8{Q}': '东方卫视',
    f'{TS}/0123_1.m3u8{Q}': '山东卫视',
    f'{TS}/0124_1.m3u8{Q}': '东方卫视',
    f'{TS}/0125_1.m3u8{Q}': '宁夏卫视',
    f'{TS}/0126_1.m3u8{Q}': '深圳卫视',
    f'{TS}/0127_1.m3u8{Q}': '北京卫视',
    f'{TS}/0128_1.m3u8{Q}': '天津卫视',
    f'{TS}/0130_1.m3u8{Q}': '安徽卫视',
    f'{TS}/0130_2.m3u8{Q}': '贵州卫视',
    f'{TS}/0131_1.m3u8{Q}': '上海卫视',
    f'{TS}/0135_1.m3u8{Q}': '广东卫视',
    f'{TS}/0137_1.m3u8{Q}': '重庆卫视',
    f'{TS}/0138_1.m3u8{Q}': '江西卫视',
    f'{TS}/0141_1.m3u8{Q}': '西藏卫视',
    f'{TS}/0142_1.m3u8{Q}': '黑龙江卫视',
    f'{TS}/0143_1.m3u8{Q}': '新疆卫视',
    f'{TS}/0112_1.m3u8{Q}': '兵团卫视',
    f'{TS}/0113_1.m3u8{Q}': '东南卫视',
    f'{TS}/0116_1.m3u8{Q}': '吉林卫视',
    f'{TS}/0117_1.m3u8{Q}': '云南卫视',
    f'{TS}/0120_1.m3u8{Q}': '山西卫视',
    f'{TS}/1000_1.m3u8{Q}': '深圳卫视',
    f'{TS}/1001_1.m3u8{Q}': '湖北卫视',
    f'{TS}/1002_1.m3u8{Q}': '湖南卫视',
    'http://111.59.139.82:11888/tsfile/live/0139_1.m3u8' + Q1: '河南卫视',
    'http://101.66.198.84:9901/tsfile/live/0123_1.m3u8' + Q: '四川卫视',
    'http://101.66.198.18:9901/tsfile/live/0136_1.m3u8' + Q: '陕西卫视',
    # ── 卫视（113.57 newlive 台标实锤，编号随机）──
    f'{HUB}/16/live.m3u8': '广东卫视',
    f'{HUB}/17/live.m3u8': '浙江卫视',
    f'{HUB}/18/live.m3u8': '江苏卫视',
    f'{HUB}/19/live.m3u8': '湖南卫视',
    f'{HUB}/22/live.m3u8': '北京卫视',
    f'{HUB}/23/live.m3u8': '重庆卫视',
    f'{HUB}/31/live.m3u8': '东方卫视',
    # ── 凤凰 ──
    'http://120.198.95.220:9901/tsfile/live/1036_1.m3u8' + Q1: '凤凰中文',
    'http://120.198.95.220:9901/tsfile/live/1037_1.m3u8' + Q1: '凤凰资讯',
}

GROUP = {
    'CCTV': '精选',
    '凤凰': '新闻财经',
}


def group_of(name):
    if name.startswith('CCTV'):
        return '精选'
    if name.startswith('凤凰'):
        return '新闻财经'
    return '卫视'


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


def speed(url):
    idx = fetch(url)
    if not idx.strip().startswith('#EXTM3U'):
        return None, 'no-idx'
    seg = None
    for line in idx.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            seg = absolute(url, line)
            break
    if not seg:
        return None, 'no-seg'
    r = subprocess.run(['curl', '-s', '-o', '/dev/null',
                        '-w', '%{http_code}|%{size_download}|%{time_total}',
                        '--max-time', '20', '-A', UA, seg], capture_output=True, text=True)
    p = r.stdout.split('|')
    if len(p) < 3:
        return None, 'ERR'
    code = p[0]
    size = int(p[1]) if p[1].isdigit() else 0
    t = float(p[2]) if p[2] else 0
    return (size / t if t > 0 else 0), code


def main():
    MIN = 300 * 1024
    lines = ['#EXTM3U']
    rows = []
    by_ch = {}
    for url, ch in VERIFIED.items():
        by_ch.setdefault(ch, []).append(url)

    for ch in sorted(by_ch, key=lambda c: (group_of(c) != '精选', c)):
        g = group_of(ch)
        kept = []
        for url in by_ch[ch]:
            bps, code = speed(url)
            ok = bps is not None and code == '200' and bps >= MIN
            rows.append((g, ch, code, bps, ok, url))
            if ok:
                kept.append((url, bps))
        # 同一频道内按速度降序
        kept.sort(key=lambda x: -x[1])
        for url, bps in kept:
            lines.append(f'#EXTINF:-1 tvg-name="{ch}" group-title="{g}",{ch}')
            lines.append(url)

    path = f'{OUT}/curated.m3u'
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    dead = [(g, c, code, bps, u) for g, c, code, bps, ok, u in rows if not ok]
    print(f'{"分组":8s}{"频道":14s}{"码":6s}{"MB/s":>8s}  URL')
    print('-' * 100)
    for g, c, code, bps, ok, u in rows:
        s = f'{bps/1024/1024:.2f}' if bps else '-'
        mark = '✅' if ok else '❌剔除'
        print(f'{g:8s}{c:14s}{str(code):6s}{s:>8s} {mark} {u[:58]}')
    print()
    print(f'输出: {path}')
    print(f'频道数 {len(by_ch)}  线路数 {sum(1 for l in lines if l and not l.startswith("#"))}  剔除 {len(dead)}')


if __name__ == '__main__':
    main()
