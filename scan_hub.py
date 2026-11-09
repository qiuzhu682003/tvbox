#!/usr/bin/env python3
"""系统扫描一台 newlive 主机的全部频道编号 → 台标，人工对照建立映射表。

用法：python3 scan_hub.py <base_url> <编号起> <编号止> <输出前缀>
"""
import os
import re
import subprocess
import sys

UA = 'okhttp/5.3.2'
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'


def fetch(url, t=8):
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


def main():
    base = sys.argv[1]
    lo, hi = int(sys.argv[2]), int(sys.argv[3])
    prefix = sys.argv[4]
    out = f'/tmp/scan_{prefix}'
    os.makedirs(out, exist_ok=True)
    pngs = []
    for n in range(lo, hi + 1):
        url = f'{base}/{n}/live.m3u8'
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
        ts = f'{out}/n{n}.ts'
        subprocess.run(['curl', '-s', '--max-time', '15', '-A', UA, '-o', ts, seg],
                       capture_output=True)
        if not os.path.exists(ts) or os.path.getsize(ts) < 10000:
            continue
        p = f'{out}/n{n}.png'
        vf = (f"crop=iw*0.42:ih*0.13:0:0,scale=1000:-1,pad=iw+200:ih:200:0:black,"
              f"drawtext=fontfile={FONT}:text='{prefix}{n}':x=12:y=h/2-th/2:fontsize=36:fontcolor=yellow")
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '2',
                        '-i', ts, '-frames:v', '1', '-vf', vf, p, '-y'], capture_output=True)
        if os.path.exists(p):
            pngs.append(p)
            print(f'✓ {prefix}{n}', flush=True)
    for i in range(0, len(pngs), 10):
        ch = pngs[i:i + 10]
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error']
        for p in ch:
            cmd += ['-i', p]
        fc = ''.join(f'[{j}:v]' for j in range(len(ch))) + f'vstack=inputs={len(ch)}[v]'
        cmd += ['-filter_complex', fc, '-map', '[v]', f'{out}/P{i//10}.png', '-y']
        subprocess.run(cmd, capture_output=True)
        print(f'P{i//10}.png ← {len(ch)} 条', flush=True)


if __name__ == '__main__':
    main()
