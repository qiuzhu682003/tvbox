#!/usr/bin/env python3
"""终验：对已写入的 curated.m3u 逐条抓台标，输出拼图供人工核对。

用法：python3 verify_final_list.py [分批]
"""
import os
import re
import subprocess
import sys

UA = 'okhttp/5.3.2'
M3U = '/Users/qiuzhu/tvbox/aggregator/data/local/curated.m3u'
OUT = '/tmp/verify'
os.makedirs(OUT, exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'


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


def main():
    lines = [l.strip() for l in open(M3U, encoding='utf-8') if l.strip()]
    entries = []
    name = None
    for l in lines:
        if l.startswith('#EXTINF'):
            name = l.split(',', 1)[1] if ',' in l else '?'
        elif not l.startswith('#'):
            entries.append((name or '?', l))

    items = []
    for i, (nm, url) in enumerate(entries):
        idx = fetch(url)
        if not idx.strip().startswith('#EXTM3U'):
            print(f'✗ #{i} {nm}: 索引不通')
            continue
        seg = None
        for line in idx.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                seg = absolute(url, line)
                break
        if not seg:
            continue
        ts = f'{OUT}/v{i}.ts'
        subprocess.run(['curl', '-s', '--max-time', '18', '-A', UA, '-o', ts, seg],
                       capture_output=True)
        if not os.path.exists(ts) or os.path.getsize(ts) < 10000:
            print(f'✗ #{i} {nm}: 分片失败')
            continue
        p = f'{OUT}/v{i}.png'
        vf = (f"crop=iw*0.42:ih*0.13:0:0,scale=1000:-1,pad=iw+340:ih:340:0:black,"
              f"drawtext=fontfile={FONT}:text='{nm} #{i}':x=14:y=h/2-th/2:fontsize=38:fontcolor=yellow")
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '2',
                        '-i', ts, '-frames:v', '1', '-vf', vf, p, '-y'], capture_output=True)
        if os.path.exists(p):
            items.append((nm, i, p))
            print(f'✓ #{i} {nm}', flush=True)

    for k in range(0, len(items), 8):
        chunk = items[k:k + 8]
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error']
        for _, _, p in chunk:
            cmd += ['-i', p]
        fc = ''.join(f'[{j}:v]' for j in range(len(chunk))) + f'vstack=inputs={len(chunk)}[v]'
        cmd += ['-filter_complex', fc, '-map', '[v]', f'{OUT}/V{k//8}.png', '-y']
        subprocess.run(cmd, capture_output=True)
        print(f'V{k//8}.png ← {" ".join(n for n, _, _ in chunk)}', flush=True)


if __name__ == '__main__':
    main()
