#!/usr/bin/env python3
"""串行逐条实测 curated.m3u 的真实分片吞吐。

判定标准（对齐 aggregator channel-probe.ts 的思路）：
  索引可达 → 解析真实分片（含一层子索引）→ 实测下载吞吐
  死线：索引不通 / 分片 0 字节 / 吞吐 < 100 KB/s（电视端会转圈）
"""
import re
import subprocess
import sys
import time

UA = 'okhttp/5.3.2'
M3U = '/Users/qiuzhu/tvbox/aggregator/data/local/curated.m3u'
DEAD_BPS = 100 * 1024  # 100KB/s 以下视为不可用
SLOW_BPS = 400 * 1024  # 400KB/s 以下视为勉强


def clean(s):
    return ''.join(ch for ch in s if ord(ch) >= 0x20)


def fetch(url, max_time=12):
    try:
        r = subprocess.run(
            ['curl', '-s', '--max-time', str(max_time), '-A', UA, url],
            capture_output=True, text=True, errors='replace')
        return r.stdout
    except Exception:
        return ''


def absolute(base, ref):
    if ref.startswith('http://') or ref.startswith('https://'):
        return ref
    if ref.startswith('//'):
        return 'http:' + ref
    m = re.match(r'(https?://[^/]+)(/.*)?', base)
    if not m:
        return ref
    host = m.group(1)
    if ref.startswith('/'):
        return host + ref
    path = m.group(2) or '/'
    return host + path.rsplit('/', 1)[0] + '/' + ref


def real_segments(index_text, base):
    """返回真实分片 URL 列表（跳过一次子索引）。"""
    segs = []
    for line in index_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        segs.append(absolute(base, clean(line)))
    if not segs:
        return []
    # 若首条像子索引（是 m3u8），下钻一层
    first = segs[0]
    if '.m3u8' in first.split('?')[0]:
        sub = fetch(first, 10)
        if sub.strip().startswith('#EXTM3U'):
            deeper = []
            for line in sub.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                deeper.append(absolute(first, clean(line)))
            if deeper:
                return deeper
    return segs


def probe(url):
    """→ dict(idx, code, bytes, sec, bps)"""
    idx = fetch(url, 12)
    if not idx.strip().startswith('#EXTM3U'):
        return {'idx': 'no-idx', 'code': '-', 'bytes': 0, 'sec': 0.0, 'bps': 0.0}
    segs = real_segments(idx, url)
    if not segs:
        return {'idx': 'idx-ok/no-seg', 'code': '-', 'bytes': 0, 'sec': 0.0, 'bps': 0.0}
    seg = segs[0]
    try:
        r = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}|%{size_download}|%{time_total}',
             '--max-time', '20', '-A', UA, seg],
            capture_output=True, text=True, errors='replace')
        p = r.stdout.split('|')
        code = p[0]
        size = int(p[1]) if len(p) > 1 and p[1].isdigit() else 0
        t = float(p[2]) if len(p) > 2 and p[2] else 0.0
    except Exception:
        return {'idx': 'idx-ok', 'code': 'ERR', 'bytes': 0, 'sec': 0.0, 'bps': 0.0}
    bps = size / t if t > 0 else 0.0
    return {'idx': 'idx-ok', 'code': code, 'bytes': size, 'sec': t, 'bps': bps}


def main():
    lines = [l.strip() for l in open(M3U, encoding='utf-8').read().split('\n') if l.strip()]
    entries = []
    name = None
    for l in lines:
        if l.startswith('#EXTINF'):
            name = l.split(',', 1)[1] if ',' in l else '?'
        elif not l.startswith('#'):
            entries.append((name or '?', l))
    print(f'共 {len(entries)} 条线路，串行实测中…\n', flush=True)
    print(f'{"频道":14s}{"索引":13s}{"分片":6s}{"大小KB":>9s}{"MB/s":>8s}  线路', flush=True)
    print('-' * 118, flush=True)
    dead, slow, ok = [], [], []
    t0 = time.time()
    for i, (nm, url) in enumerate(entries, 1):
        r = probe(url)
        bps = r['bps']
        if r['code'] == '200' and bps >= SLOW_BPS:
            flag = '✅'
            ok.append((nm, url, bps))
        elif r['code'] == '200' and bps >= DEAD_BPS:
            flag = '⚠️'
            slow.append((nm, url, bps))
        else:
            flag = '❌'
            dead.append((nm, url, r))
        print(f'{nm[:13]:14s}{r["idx"]:13s}{flag}{str(r["code"]):5s}{r["bytes"]/1024:9.0f}'
              f'{bps/1024/1024:8.2f}  {url[:52]}', flush=True)
    print('-' * 118, flush=True)
    print(f'✅ 达标(>=0.4MB/s) {len(ok)}   ⚠️ 勉强(0.1-0.4MB/s) {len(slow)}   ❌ 死线 {len(dead)}'
          f'   耗时 {time.time()-t0:.0f}s', flush=True)
    if dead:
        print('\n死线明细：', flush=True)
        for nm, url, r in dead:
            print(f'  ❌ {nm:14s} idx={r["idx"]:12s} code={r["code"]:5s} {url}', flush=True)
    if slow:
        print('\n勉强明细：', flush=True)
        for nm, url, bps in slow:
            print(f'  ⚠️ {nm:14s} {bps/1024/1024:.2f}MB/s {url}', flush=True)


if __name__ == '__main__':
    main()
