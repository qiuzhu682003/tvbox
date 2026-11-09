#!/usr/bin/env python3
"""受控实验：同一条 newlive URL 在不同时刻抓帧，看台标/内容是否漂移。

用法：python3 drift_test.py <m3u8_url> [次数] [间隔秒]
输出：/tmp/drift/<序号>_<时间戳>.png
"""
import os
import re
import subprocess
import sys
import time

UA = 'okhttp/5.3.2'
OUT = '/tmp/drift'
os.makedirs(OUT, exist_ok=True)


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
    url = sys.argv[1]
    times = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    gap = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    print(f'目标: {url}')
    for i in range(times):
        seg = first_seg(url)
        if not seg:
            print(f'  [{i+1}] 索引不通')
        else:
            ts = f'{OUT}/{i+1}.ts'
            subprocess.run(['curl', '-s', '--max-time', '25', '-A', UA, '-o', ts, seg],
                           capture_output=True)
            sz = os.path.getsize(ts) if os.path.exists(ts) else 0
            png = f'{OUT}/{i+1}_{int(time.time())}.png'
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '2',
                            '-i', ts, '-frames:v', '1',
                            '-vf', 'crop=iw*0.26:ih*0.13:0:0,scale=900:-1', png, '-y'],
                           capture_output=True)
            print(f'  [{i+1}] seg={seg[-40:]} 分片{sz}B → {png}')
        if i < times - 1:
            time.sleep(gap)


if __name__ == '__main__':
    main()
