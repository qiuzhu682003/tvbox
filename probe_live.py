#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_live.py — 直播源死链过滤工具（内容感知探活）

用途
----
给一个直播清单（m3u / txt / TVBox txt 格式），逐条线路探活，
只输出**实测可用**的频道，生成干净的 m3u。
适用场景：电视端 TVBox 源、iMac 聚合器产出、任何第三方直播清单。

核心判活标准（这是关键，只判 HTTP 状态码会误判）
------------------------------------------------
1) HTTP 状态码必须在 200–399；
2) **内容**不能是错误页：
   - 以 `#EXTM3U` / `#EXTINF` 开头 → 明确的 HLS 清单，可用；
   - 以 `<` 开头 → HTML/XML 错误页，不可用；
   - 短的可打印 ASCII 文本（<80 字节，如 `sign error`）→ 服务端错误消息，不可用；
   - 其余（媒体二进制）→ 可用；
   - 读不到内容（流式首块延迟）→ 不武断否决，交给播放器。

为什么必须判内容：实测某线路返回 HTTP 200 + `sign error`（鉴权失败），
只判状态码会当成可用线，播放时报 "Failed to recognize file format"。

为什么不能用 `Range: bytes=0-1`：只会拿到 2 字节，HLS 清单退化成 `#E`，
被"短文本"规则误杀，真线路全被判死。**必须用 bytes=0-1023**。

用法
----
  # 远程源
  python3 probe_live.py --url 'https://example.com/live.m3u' -o clean.m3u

  # 本地文件
  python3 probe_live.py --file live_lite.m3u -o clean.m3u

  # 指定 EPG、并发数、单条超时、只保留某些分组
  python3 probe_live.py --url U --epg E --workers 32 --timeout 4.5 \
      --groups '央视频道,卫视频道' -o clean.m3u

依赖：仅 Python 3.8+ 标准库，无第三方包。
"""
import argparse
import collections
import concurrent.futures
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

UA = 'okhttp/3.12.0'
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 各平台 IPTV 常见死因（仅用于报告分组，不影响判活）
DEAD_HINTS = (
    ('运营商IPTV-403', ('cmvideo.cn', 'chinamobile', 'itv.cn', 'wasu', 'iptv.cn')),
    ('运营商IPTV-不可达', ('cmvideo.cn', 'chinamobile', 'itv.cn')),
)


def probe(url, timeout=4.5):
    """返回 (是否可用, 说明)。判活标准见模块 docstring。"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        # 要读够内容才能判活，所以 Range 放宽到 1KB（bytes=0-1 只拿到 2 字节会误杀 HLS）
        req.add_header('Range', 'bytes=0-1023')
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            if r.status < 200 or r.status >= 400:
                return False, 'HTTP %s' % r.status
            head = r.read(1024)
            if not head:
                return True, 'empty'
            t = head.decode('utf-8', 'replace').lstrip()
            if not t:
                return True, 'empty'
            if t.startswith('#EXTM3U') or t.startswith('#EXTINF'):
                return True, 'HLS'
            if t.startswith('<'):
                return False, 'HTML'
            if all(0x20 <= ord(c) < 0x7f for c in t[:200]) and len(t) < 80:
                return False, 'errmsg'
            return True, 'binary'
    except urllib.error.HTTPError as e:
        return False, 'HTTP %s' % e.code
    except Exception as e:
        return False, type(e).__name__


def parse_m3u(text):
    """返回 [(group, name, url, logo)]，同名频道的多条线路各自成条（调用方再归并）。"""
    out = []
    group = name = logo = ''
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith('#EXTINF'):
            m = re.search(r'group-title="([^"]*)"', line)
            group = m.group(1) if m else ''
            lm = re.search(r'tvg-logo="([^"]*)"', line)
            logo = lm.group(1) if lm else ''
            t = line.split(',', 1)
            name = t[1].strip() if len(t) > 1 else ''
        elif line and not line.startswith('#') and name:
            out.append((group, name, line, logo))
            group = name = logo = ''
    return out


def parse_tvbox_txt(text):
    """TVBox 直播 txt：每行 `分组,url#名称` 或 `url#名称`。"""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        body, _, label = line.partition('#')
        body = body.strip()
        label = label.strip()
        group = ''
        if ',' in body:
            group, _, body = body.partition(',')
            group = group.strip()
            body = body.strip()
        for u in body.split(','):
            u = u.strip()
            if u.startswith(('http://', 'https://', 'rtmp://', 'rtsp://')):
                out.append((group, label or u, u, ''))
    return out


def load_source(args):
    if args.file:
        with open(args.file, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    with urllib.request.urlopen(
            urllib.request.Request(args.url, headers={'User-Agent': UA}),
            timeout=30, context=CTX) as r:
        return r.read().decode('utf-8', 'replace')


def main():
    ap = argparse.ArgumentParser(description='直播源死链过滤（内容感知探活）')
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--url', help='远程清单地址（m3u / txt）')
    src.add_argument('--file', help='本地清单文件')
    ap.add_argument('-o', '--out', default='clean.m3u', help='输出 m3u 路径')
    ap.add_argument('--epg', default='', help='写入清单的 x-tvg-url（EPG 地址）')
    ap.add_argument('--workers', type=int, default=24, help='并发探活数')
    ap.add_argument('--timeout', type=float, default=4.5, help='单条超时秒')
    ap.add_argument('--groups', default='', help='只保留这些分组（逗号分隔）')
    ap.add_argument('--report', default='', help='JSON 报告输出路径')
    ap.add_argument('--max-lines', type=int, default=8,
                    help='每个频道最多探测多少条线路')
    args = ap.parse_args()

    text = load_source(args)
    if '#EXTM3U' in text[:400] or '#EXTINF' in text:
        chans = parse_m3u(text)
    else:
        chans = parse_tvbox_txt(text)
    if not chans:
        print('清单解析为空', file=sys.stderr)
        return 2

    # 归并同名频道（同分组 + 同名）的多条线路
    merged = collections.OrderedDict()
    for g, n, u, logo in chans:
        key = (g or '未分组', n or u)
        e = merged.setdefault(key, {'urls': [], 'logo': logo})
        if u not in e['urls']:
            e['urls'].append(u)

    print('清单：%d 个频道 / %d 条线路，开始探活…' % (
        len(merged), sum(len(v['urls']) for v in merged.values())))

    want_groups = None
    if args.groups:
        want_groups = {g.strip() for g in args.groups.split(',') if g.strip()}

    def check(item):
        key, e = item
        pool = e['urls'][:args.max_lines]
        tried = []
        for u in pool:
            ok, why = probe(u, args.timeout)
            tried.append((u, ok, why))
            if ok:
                return key, e, u, tried
        return key, e, None, tried

    t0 = time.time()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(check, it) for it in merged.items()]
        for i, f in enumerate(concurrent.futures.as_completed(futs)):
            results.append(f.result())
            if (i + 1) % 50 == 0:
                print('  %d/%d（%.0fs）' % (i + 1, len(merged), time.time() - t0))

    alive, dead_channels = [], []
    for key, e, u, tried in results:
        if want_groups is not None and key[0] not in want_groups:
            continue
        if u:
            alive.append((key, e, u, tried))
        else:
            dead_channels.append((key, tried))

    lines = []
    if args.epg:
        lines.append('#EXTM3U x-tvg-url="%s"' % args.epg)
    else:
        lines.append('#EXTM3U')
    for (grp, name), e, u, _ in alive:
        lines.append('#EXTINF:-1 tvg-name="%s" tvg-logo="%s" group-title="%s",%s' % (
            name, e.get('logo') or '', grp.replace('"', "'"), name))
        lines.append(u)

    with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    total_ch = len(merged)
    ok_ch = len(alive)
    print('\n可用频道 %d / %d（%.0f%%）  ->  %s' % (
        ok_ch, total_ch, ok_ch * 100 // max(1, total_ch), args.out))

    # 死因归类报告
    reasons = collections.Counter()
    for key, tried in dead_channels:
        for u, ok, why in tried:
            reasons[why] += 1
    print('\n死因分布（按线路）：')
    for r, n in reasons.most_common(10):
        print('  %-16s %d' % (r, n))

    bygroup = collections.Counter(k[0] for k, _, _, _ in alive)
    print('\n可用频道按分组：')
    for g, n in bygroup.most_common():
        print('  %-14s %d' % (g, n))

    if args.report:
        rep = {
            'total_channels': total_ch,
            'alive_channels': ok_ch,
            'alive': [{'group': k[0], 'name': k[1], 'url': u} for k, _, u, _ in alive],
            'dead': [{'group': k[0], 'name': k[1],
                       'tried': [{'url': u, 'ok': ok, 'why': w} for u, ok, w in t]}
                      for k, t in dead_channels],
            'dead_reason_by_line': dict(reasons),
        }
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        print('\n报告:', args.report)


if __name__ == '__main__':
    sys.exit(main())
