#!/usr/bin/env python3
"""高清台标重抓：直接定位台标小区域，放大 4 倍，分组拼图。

思路：多数台标在画面顶部；先取 1920x1080 全帧，再裁 y=0..0.09*h、x=0..0.30*w，
放大到 1400 宽。若该区域无台标，则退化为整行顶栏。
"""
import os
import re
import subprocess
import sys

UA = 'okhttp/5.3.2'
OUT = '/tmp/hd'
os.makedirs(OUT, exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'


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


def shoot(label, url, vf=None):
    seg = first_seg(url)
    if not seg:
        return None
    ts = f'{OUT}/{label}.ts'
    if not (os.path.exists(ts) and os.path.getsize(ts) > 10000):
        subprocess.run(['curl', '-s', '--max-time', '25', '-A', UA, '-o', ts, seg], capture_output=True)
    if not os.path.exists(ts) or os.path.getsize(ts) < 10000:
        return None
    png = f'{OUT}/{label}.png'
    vf = vf or 'crop=iw*0.26:ih*0.11:0:0,scale=1400:-1'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '2',
                    '-i', ts, '-frames:v', '1', '-vf', vf, png, '-y'], capture_output=True)
    return png if os.path.exists(png) else None


def montage(items, out):
    pngs = []
    for label, url in items:
        p = shoot(label, url)
        if p:
            pngs.append((label, p))
    if not pngs:
        return
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error']
    for _, p in pngs:
        cmd += ['-i', p]
    fc = ''.join(f'[{i}:v]' for i in range(len(pngs))) + f'vstack=inputs={len(pngs)}[v]'
    cmd += ['-filter_complex', fc, '-map', '[v]', out, '-y']
    subprocess.run(cmd, capture_output=True)
    print(f'{out} ← {" ".join(l for l, _ in pngs)}', flush=True)


if __name__ == '__main__':
    # 从 final_check.py 的 CANDS 导入
    sys.path.insert(0, '/Users/qiuzhu/tvbox')
    from final_check import CANDS
    d = {lbl: u for lbl, _, u in CANDS}
    sets = {
        'HD0': ['a01', 'a02', 'a03', 'a04', 'a05', 'a06', 'a07', 'a08'],
        'HD1': ['a09', 'a10', 'a11', 'a12', 'a13', 'a14', 'a15', 'a16'],
        'HD2': ['a17', 'a18', 'b01', 'b02', 'b03', 'b04', 'b05', 'b06'],
        'HD3': ['b07', 'b08', 'b09', 'b10', 'b11', 'b12', 'b13', 'b14'],
        'HD4': ['b15', 'b16', 'b17', 'b18', 'b19', 'b20', 'b31', 'c16'],
    }
    only = sys.argv[1:]
    for name, labels in sets.items():
        if only and name not in only:
            continue
        montage([(l, d[l]) for l in labels], f'{OUT}/{name}.png')
