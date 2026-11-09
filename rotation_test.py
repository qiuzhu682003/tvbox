#!/usr/bin/env python3
"""频道轮换实验：固定 URL，间隔采样多次，看同一 URL 播的频道会不会变。

用法：python3 rotation_test.py <间隔秒> <次数> <标签:url> ...
输出：/tmp/rot/<标签>_<序号>.png
"""
import os
import re
import subprocess
import sys
import time

UA = 'okhttp/5.3.2'
OUT = '/tmp/rot'
os.makedirs(OUT, exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'


def fetch_text(url, timeout=12):
    r = subprocess.run(['curl', '-s', '--max-time', str(timeout), '-A', UA, url],
                       capture_output=True, text=True, errors='replace')
    return r.stdout


def first_seg(url):
    idx = fetch_text(url)
    if not idx.strip().startswith('#EXTM3U'):
        return None
    for line in idx.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            if line.startswith('http'):
                return line
            return url.rsplit('/', 1)[0] + '/' + line
    return None


def main():
    gap = int(sys.argv[1])
    times = int(sys.argv[2])
    targets = []
    for a in sys.argv[3:]:
        label, url = a.split('=', 1)
        targets.append((label, url))

    for i in range(times):
        ts_tag = time.strftime('%H%M')
        for label, url in targets:
            seg = first_seg(url)
            if not seg:
                print(f'[{ts_tag}] {label}: 索引不通', flush=True)
                continue
            ts = f'{OUT}/{label}.ts'
            subprocess.run(['curl', '-s', '--max-time', '25', '-A', UA, '-o', ts, seg],
                           capture_output=True)
            if not os.path.exists(ts) or os.path.getsize(ts) < 10000:
                print(f'[{ts_tag}] {label}: 分片失败', flush=True)
                continue
            png = f'{OUT}/{label}_{i}_{ts_tag}.png'
            vf = (f"crop=iw:ih*0.15:0:0,scale=1100:-1,pad=iw+260:ih:260:0:black,"
                  f"drawtext=fontfile={FONT}:text='{label}  {ts_tag}':x=20:y=h/2-th/2:"
                  f"fontsize=52:fontcolor=yellow")
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '2',
                            '-i', ts, '-frames:v', '1', '-vf', vf, png, '-y'],
                           capture_output=True)
            print(f'[{ts_tag}] {label}: {png}', flush=True)
        if i < times - 1:
            time.sleep(gap)


if __name__ == '__main__':
    main()
