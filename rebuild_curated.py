#!/usr/bin/env python3
"""按台标实锤结果重建 curated.m3u。

原则：
1. 只写台标实拍验证过的 URL → 频道名的映射；
2. 每个频道至少 1 条实测吞吐 ≥0.3MB/s 的线；
3. 死线（404/索引不通/实测 <0.1MB/s）不写。
"""
import os
import re
import subprocess
import sys

UA = 'okhttp/5.3.2'
OUT = '/tmp/rebuild'
os.makedirs(OUT, exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'

TS = 'http://112.123.243.37:50085/tsfile/live'
Q = '?key=txiptv&playlive=0&authid=0'
Q1 = '?key=txiptv&playlive=1&authid=0'
HUB = 'http://113.57.140.161:10081/newlive/live/hls'
G = 'http://120.40.39.246:352/newlive/live/hls'

# (分组, 频道名, [(标签, url), ...])  —— 全部为台标实锤
PLAN = [
    ('精选', 'CCTV-1', [
        ('a01', f'{TS}/0001_1.m3u8{Q}'),
        ('b01', f'{HUB}/1/live.m3u8'),
    ]),
    ('精选', 'CCTV-2', [
        ('a02', f'{TS}/0002_1.m3u8{Q}'),
        ('b02', f'{HUB}/2/live.m3u8'),
    ]),
    ('精选', 'CCTV-3', [
        ('a03', f'{TS}/0003_1.m3u8{Q}'),
        ('b03', f'{HUB}/3/live.m3u8'),
    ]),
    ('精选', 'CCTV-4', [
        ('a04', f'{TS}/0004_1.m3u8{Q}'),
        ('b04', f'{HUB}/4/live.m3u8'),
    ]),
    ('精选', 'CCTV-5', [
        ('a05', f'{TS}/0005_1.m3u8{Q}'),
        ('b05', f'{HUB}/5/live.m3u8'),
    ]),
    ('精选', 'CCTV-5+', [
        ('e13', 'http://153.0.171.163:85/tsfile/live/1015_1.m3u8' + Q1),
    ]),
    ('精选', 'CCTV-6', [
        ('a06', f'{TS}/0007_1.m3u8{Q}'),
        ('b06', f'{HUB}/6/live.m3u8'),
    ]),
    ('精选', 'CCTV-7', [
        ('a07', f'{TS}/0008_1.m3u8{Q}'),
        ('b07', f'{HUB}/7/live.m3u8'),
    ]),
    ('精选', 'CCTV-8', [
        ('a08', f'{TS}/0009_1.m3u8{Q}'),
        ('b08', f'{HUB}/8/live.m3u8'),
    ]),
    ('精选', 'CCTV-9 纪录', [
        ('a09', f'{TS}/0010_1.m3u8{Q}'),
        ('b09', f'{HUB}/9/live.m3u8'),
    ]),
    ('精选', 'CCTV-10 科教', [
        ('a10', f'{TS}/0011_1.m3u8{Q}'),
        ('b10', f'{HUB}/10/live.m3u8'),
    ]),
    ('精选', 'CCTV-11 戏曲', [
        ('a11', f'{TS}/0012_1.m3u8{Q}'),
        ('b11', f'{HUB}/11/live.m3u8'),
    ]),
    ('精选', 'CCTV-12 社会与法', [
        ('a12', f'{TS}/0013_1.m3u8{Q}'),
        ('b12', f'{HUB}/12/live.m3u8'),
    ]),
    ('精选', 'CCTV-13 新闻', [
        ('a13', f'{TS}/0014_1.m3u8{Q}'),
        ('b13', f'{HUB}/13/live.m3u8'),
    ]),
    ('精选', 'CCTV-14 少儿', [
        ('a14', f'{TS}/0015_1.m3u8{Q}'),
    ]),
    ('精选', 'CCTV-15 音乐', [
        ('a15', f'{TS}/0016_1.m3u8{Q}'),
        ('b15', f'{HUB}/15/live.m3u8'),
    ]),
    ('精选', 'CCTV-16 少儿', [
        ('e14', 'http://124.228.160.112:9901/tsfile/live/0016_1.m3u8' + Q1),
    ]),
    ('精选', 'CCTV-17 农业', [
        ('c17', f'{G}/17/live.m3u8'),
    ]),
    ('卫视', '湖南卫视', [
        ('d01', f'{TS}/1002_1.m3u8{Q}'),
        ('b19', f'{HUB}/19/live.m3u8'),
    ]),
    ('卫视', '东方卫视', [
        ('a18', f'{TS}/0019_1.m3u8{Q}'),
        ('b31', f'{HUB}/31/live.m3u8'),
    ]),
    ('卫视', '浙江卫视', [
        ('d02', f'{TS}/0122_1.m3u8{Q}'),
        ('b17', f'{HUB}/17/live.m3u8'),
    ]),
    ('卫视', '江苏卫视', [
        ('a16', f'{TS}/0017_1.m3u8{Q}'),
        ('b18', f'{HUB}/18/live.m3u8'),
    ]),
    ('卫视', '河北卫视', [
        ('a17', f'{TS}/0018_1.m3u8{Q}'),
    ]),
    ('卫视', '北京卫视', [
        ('d07', f'{TS}/0127_1.m3u8{Q}'),
    ]),
    ('卫视', '天津卫视', [
        ('d08', f'{TS}/0128_1.m3u8{Q}'),
    ]),
    ('卫视', '上海卫视', [
        ('d11', f'{TS}/0131_1.m3u8{Q}'),
    ]),
    ('卫视', '山东卫视', [
        ('d05', f'{TS}/0125_1.m3u8{Q}'),
    ]),
    ('卫视', '安徽卫视', [
        ('d09', f'{TS}/0130_1.m3u8{Q}'),
    ]),
    ('卫视', '重庆卫视', [
        ('d13', f'{TS}/0137_1.m3u8{Q}'),
    ]),
    ('卫视', '广东卫视', [
        ('d12', f'{TS}/0135_1.m3u8{Q}'),
        ('b16', f'{HUB}/16/live.m3u8'),
    ]),
    ('卫视', '深圳卫视', [
        ('d06', f'{TS}/0126_1.m3u8{Q}'),
    ]),
    ('卫视', '海南卫视', [
        ('d14', f'{TS}/0141_1.m3u8{Q}'),
    ]),
    ('卫视', '贵州卫视', [
        ('d10', f'{TS}/0130_2.m3u8{Q}'),
    ]),
    ('卫视', '辽宁卫视', [
        ('d16', f'{TS}/0142_1.m3u8{Q}'),
    ]),
    ('卫视', '河南卫视', [
        ('e12', 'http://111.59.139.82:11888/tsfile/live/0139_1.m3u8' + Q1),
    ]),
    ('卫视', '云南卫视', [
        ('d21', f'{TS}/0117_1.m3u8{Q}'),
    ]),
    ('卫视', '东南卫视', [
        ('d19', f'{TS}/0113_1.m3u8{Q}'),
    ]),
    ('卫视', '吉林卫视', [
        ('d20', f'{TS}/0116_1.m3u8{Q}'),
    ]),
    ('卫视', '黑龙江卫视', [
        ('d17', f'{TS}/0143_1.m3u8{Q}'),
    ]),
    ('卫视', '西藏卫视', [
        ('d15', f'{TS}/0141_1.m3u8{Q}'),
    ]),
    ('卫视', '兵团卫视', [
        ('d18', f'{TS}/0112_1.m3u8{Q}'),
    ]),
    ('卫视', '山西卫视', [
        ('d22', f'{TS}/0120_1.m3u8{Q}'),
    ]),
    ('卫视', '四川卫视', [
        ('e02', 'http://101.66.198.84:9901/tsfile/live/0123_1.m3u8' + Q),
    ]),
    ('卫视', '陕西卫视', [
        ('e01', 'http://101.66.198.18:9901/tsfile/live/0136_1.m3u8' + Q),
    ]),
    ('新闻财经', '凤凰中文', [
        ('e15', 'http://120.198.95.220:9901/tsfile/live/1036_1.m3u8' + Q1),
    ]),
    ('新闻财经', '凤凰资讯', [
        ('e16', 'http://120.198.95.220:9901/tsfile/live/1037_1.m3u8' + Q1),
    ]),
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


def speed(url):
    seg = first_seg(url)
    if not seg:
        return None, 'no-idx'
    r = subprocess.run(['curl', '-s', '-o', '/dev/null',
                        '-w', '%{http_code}|%{size_download}|%{time_total}',
                        '--max-time', '20', '-A', UA, seg], capture_output=True, text=True)
    p = r.stdout.split('|')
    if len(p) < 3:
        return None, 'ERR'
    code, size, t = p[0], (int(p[1]) if p[1].isdigit() else 0), (float(p[2]) if p[2] else 0)
    return (size / t if t > 0 else 0), code


def main():
    out_lines = ['#EXTM3U']
    report = []
    for group, ch, lines in PLAN:
        kept = []
        for label, url in lines:
            bps, code = speed(url)
            ok = bps is not None and code == '200' and bps >= 300 * 1024
            report.append((group, ch, label, code, bps, ok, url))
            if ok:
                kept.append((label, url))
        if not kept:
            report.append((group, ch, '—', '全部剔除', None, False, ''))
            continue
        for label, url in kept:
            out_lines.append(f'#EXTINF:-1 tvg-name="{ch}" group-title="{group}",{ch}')
            out_lines.append(url)

    path = '/tmp/rebuild/curated.m3u'
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines) + '\n')

    print(f'{"分组":10s}{"频道":16s}{"标签":7s}{"码":6s}{"MB/s":>8s}  判定')
    print('-' * 84)
    for group, ch, label, code, bps, ok, url in report:
        s = f'{bps/1024/1024:.2f}' if bps else '-'
        mark = '✅' if ok else ('❌' if label != '—' else '⚠️全剔')
        print(f'{group:10s}{ch:16s}{label:7s}{str(code):6s}{s:>8s}  {mark}')
    print()
    print(f'候选文件: {path}')
    n_ch = len({c for _, c, _, _, _, _, _ in report})
    print(f'输出频道数: {n_ch}  线路数: {sum(1 for l in out_lines if l and not l.startswith("#"))}')


if __name__ == '__main__':
    main()
