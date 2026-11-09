#!/usr/bin/env python3
"""验证假设：配置里缓存的直播 URL（含 token）已过期。
做法：现场重新抓一次 m3u8 索引，立刻测它的分片。"""
import subprocess, time

UA = 'okhttp/3.12.0'
SRC = 'http://120.76.248.139/live/bfgd/4200000489.m3u8'


def clean(s):
    return ''.join(ch for ch in s if ord(ch) >= 0x20)


def seg_of(url):
    r = subprocess.run(['curl', '-s', '--max-time', '10', '-A', UA, url],
                       capture_output=True, text=True, errors='replace')
    for line in r.stdout.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            return clean(line), r.stdout
    return None, r.stdout


def test_seg(seg, label):
    r2 = subprocess.run(
        ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}|%{size_download}|%{time_total}',
         '--max-time', '30', '-A', UA, seg],
        capture_output=True, text=True, errors='replace')
    p = r2.stdout.split('|')
    code = p[0] if p else '?'
    size = int(p[1]) if len(p) > 1 and p[1].isdigit() else 0
    t = float(p[2]) if len(p) > 2 and p[2] else 0
    sp = size / 1024 / t if t > 0 else 0
    print(f"  {label}: HTTP {code} | {size/1024:.0f}KB | {t:.1f}s | {sp:.0f}KB/s")
    return code


print("【A】配置里缓存的旧 URL（含早先的 token）")
seg_old, _ = seg_of(SRC)
if seg_old:
    print(f"  旧分片 URL: {seg_old[:90]}...")
    test_seg(seg_old, '旧分片')
else:
    print("  取不到分片")

print()
print("【B】现场重新抓索引后立刻测分片")
seg_new, content = seg_of(SRC)
if seg_new:
    print(f"  新分片 URL: {seg_new[:90]}...")
    test_seg(seg_new, '新分片')
else:
    print("  取不到分片")

print()
print("【C】结论依据")
if seg_old and seg_new:
    # 比较 token 是否变化
    import re
    tok_old = re.search(r'accesstoken=([^&]+)', seg_old)
    tok_new = re.search(r'accesstoken=([^&]+)', seg_new)
    print(f"  旧 token: {tok_old.group(1)[:40] if tok_old else '无'}")
    print(f"  新 token: {tok_new.group(1)[:40] if tok_new else '无'}")
    print(f"  token 是否相同: {'是（缓存未过期）' if (tok_old and tok_new and tok_old.group(1)==tok_new.group(1)) else '否（token 会轮换）'}")
