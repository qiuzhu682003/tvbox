#!/usr/bin/env python3
"""把单组拼图两两合并成双组拼图，便于一次性人工核对台标。"""
import glob
import os
import subprocess
import sys

SRC = '/tmp/logos2'
DST = '/tmp/logos2/pair'
os.makedirs(DST, exist_ok=True)

groups = sorted(glob.glob(f'{SRC}/grp*.png'))
for i in range(0, len(groups), 2):
    pair = groups[i:i + 2]
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error']
    for p in pair:
        cmd += ['-i', p]
    fc = ''.join(f'[{j}:v]' for j in range(len(pair))) + f'vstack=inputs={len(pair)}[v]'
    cmd += ['-filter_complex', fc, '-map', '[v]', f'{DST}/pair{i//2:02d}.png', '-y']
    subprocess.run(cmd, capture_output=True)
    print(f'pair{i//2:02d}.png ← {[os.path.basename(p) for p in pair]}')
