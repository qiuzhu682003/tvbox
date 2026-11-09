#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_tv_source.py — 生成电视端专用的聚合直播 m3u

把多个公开 m3u 源合并成一个干净快照，供电视端（Kodi / TVBox）直接订阅。

流程
----
1. 拉取各源 m3u
2. 解析成 (group, name, url) 列表
3. 内容感知探活（live_filter.probe：状态码 + 内容 + 真实分片）
4. 同名频道跨源合并，保留全部可用线路
5. 输出 m3u（带 x-tvg-url EPG）

用法
----
python3 build_tv_source.py \
  --out /Users/qiuzhu/tvbox/live-candidates/tv_m3u.txt \
  --epg http://192.168.3.248:8088/epg/epg.gz
"""
import argparse
import collections
import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from live_filter import probe  # noqa: E402

# ── 源定义 ──────────────────────────────────────────
# name, url, 分组名前缀（None 表示沿用源内分组）
SOURCES = [
    {
        'name': '虎牙',
        'url': 'https://sub.ottiptv.cc/huyayqk.m3u',
        'prefix': '虎牙',          # 虎牙组名是「一起看/原创」，加前缀避免和央视混
    },
    {
        'name': 'iptv4',
        'url': 'https://gh-proxy.com/raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u',
        'prefix': None,            # 沿用原分组名（央视频道/卫视频道/地方频道…）
    },
    {
        # CCSH live_lite —— 补齐 iptv4 缺的 CCTV1/2/4/7（+4K/8K）。
        # Windows 端「CCTV精选」快照就是从它全量探活后提取的。
        'name': 'CCSH',
        'url': 'https://gh-proxy.com/raw.githubusercontent.com/CCSH/IPTV/main/live_lite.m3u',
        'prefix': None,
    },
]

EPG_DEFAULT = 'http://192.168.3.248:8088/epg/epg.gz'


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')


def parse_m3u(text):
    """
    返回 [(group, name, url, attrs)]。

    attrs 保留原始 EXTINF 的全部属性（tvg-id / tvg-logo / tvg-chno…）——
    台标本地化和 EPG 对齐都依赖它们，丢了就得重新造。
    """
    out = []
    group = ''
    name = ''
    attrs = {}
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('#EXTINF'):
            attrs = dict(ATTR_RE.findall(line))
            m = re.search(r'group-title="([^"]*)"', line)
            group = m.group(1).strip() if m else group
            nm = re.search(r'tvg-name="([^"]*)"', line)
            if nm:
                name = nm.group(1).strip()
            else:
                tail = line.split(',')[-1].strip()
                name = tail if tail and not tail.startswith('#') else ''
        elif line.startswith('#'):
            continue
        else:
            out.append((group, name or group or '未命名', line, dict(attrs)))
            name = ''
    return out


def probe_all(items, workers=12, timeout=8.0):
    """并发探活。返回 [(group, name, url, attrs, ok, why)]"""
    def check(it):
        ok, why = probe(it[2], timeout=timeout)
        return (it[0], it[1], it[2], it[3], ok, why)

    t0 = time.time()
    res = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(check, items), 1):
            res.append(r)
            if i % 100 == 0:
                print(f'  probed {i}/{len(items)} ({time.time()-t0:.0f}s)', flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--epg', default=EPG_DEFAULT)
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--timeout', type=float, default=8.0)
    ap.add_argument('--report', default='')
    args = ap.parse_args()

    # 文件锁：防止多个构建并发跑互相覆盖产物
    lock_path = os.path.abspath(args.out) + ".lock"
    lock_fd = None
    try:
        import fcntl
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (ImportError, BlockingIOError):
        if lock_fd is not None:
            os.close(lock_fd)
        print(f"❌ 已有构建在跑（锁文件 {lock_path}），退出")
        return 1

    all_items = []
    for s in SOURCES:
        print(f"拉取 {s['name']} …", flush=True)
        try:
            text = fetch(s['url'])
        except Exception as e:
            print(f"  ❌ {s['name']}: {type(e).__name__} {e}")
            continue
        items = parse_m3u(text)
        if s['prefix']:
            items = [(f"{s['prefix']}·{g}", n, u, a) for g, n, u, a in items]
        print(f"  ✅ {s['name']}: {len(items)} 条")
        all_items += items

    # 同一 URL 去重（两个源常有重叠）——保留属性更全的那条
    seen = {}
    for it in all_items:
        prev = seen.get(it[2])
        if prev is None:
            seen[it[2]] = it
        elif len(it[3]) > len(prev[3]):
            seen[it[2]] = it
    dedup = list(seen.values())
    print(f"合并后 {len(dedup)} 条（去重 {len(all_items)-len(dedup)}）", flush=True)

    print("探活中 …", flush=True)
    res = probe_all(dedup, args.workers, args.timeout)

    alive = [r for r in res if r[4]]
    dead = [r for r in res if not r[4]]
    print(f"探活完成: 活 {len(alive)} / 死 {len(dead)}")

    # 同名频道跨源合并 → 一个频道多线路
    chan = collections.OrderedDict()
    for g, n, u, a, ok, why in alive:
        key = n
        slot = chan.setdefault(key, {'group': g, 'urls': [], 'attrs': {}})
        slot['urls'].append(u)
        # 属性取最全的（tvg-id / tvg-logo）
        if len(a) > len(slot['attrs']):
            slot['attrs'] = a

    lines = [f'#EXTM3U x-tvg-url="{args.epg}"']
    lines.append('# 电视端聚合直播源 · 由 build_tv_source.py 生成')
    lines.append(f'# 生成时间 {time.strftime("%Y-%m-%d %H:%M:%S")}  '
                 f'频道 {len(chan)} / 线路 {len(alive)}')
    for name, info in chan.items():
        grp = info['group'] or '未分组'
        attrs = dict(info['attrs'])
        attrs['tvg-name'] = name
        attrs['group-title'] = grp
        # 丢掉更新时间伪频道
        if '更新时间' in grp or '更新时间' in name:
            continue
        attr_str = ''.join(f' {k}="{v}"' for k, v in attrs.items())
        lines.append(f'#EXTINF:-1{attr_str},{name}')
        lines.extend(info['urls'])

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or '.', exist_ok=True)
    # 原子写：先写 .tmp 再 rename，避免读方看到半截文件
    tmp_path = args.out + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    os.replace(tmp_path, args.out)
    print(f"written: {args.out}  ({os.path.getsize(args.out):,} B, {len(chan)} 频道)")

    if args.report:
        rep = {
            'generated': time.strftime('%Y-%m-%d %H:%M:%S'),
            'sources': [s['url'] for s in SOURCES],
            'total_lines': len(res),
            'alive_lines': len(alive),
            'dead_lines': len(dead),
            'channels': len(chan),
            'dead_reason': dict(collections.Counter(r[5] for r in dead)),
            'dead_sample': [{'name': r[1], 'url': r[2], 'why': r[5]} for r in dead[:50]],
        }
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        print(f"report: {args.report}")


if __name__ == '__main__':
    main()
