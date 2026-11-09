#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
live_filter.py — 直播源探活过滤器（供 export_static.py 调用）

用途
----
对 TVBox 配置里的 `lives` 分组做内容感知探活，只保留**实测可用**的频道。
可作为独立 CLI 跑，也可被 export_static.py import。

核心判活标准（只判 HTTP 状态码会误判）
----------------------------------------
1) HTTP 状态码必须在 [200, 400)；
2) **内容**不能是错误页：
   - 以 `#EXTM3U` / `#EXTINF` 开头 → HLS 清单，放行；
   - 以 `<` 开头 → HTML/XML 错误页，判死；
   - 短的可打印 ASCII 文本（<80 字节，如 `sign error`）→ 服务端错误消息，判死；
   - **MP4 文件**（首 12 字节含 `ftyp`）→ 点播文件冒充直播，判死；
   - 读不到内容（流式首块延迟）→ 放行，交给播放器；
   - 其余（二进制媒体流）→ 放行。

为什么必须探真实分片
-------------------
只读索引会漏掉「索引是活的、分片已经死了」的假流。
本模块对 .m3u8 会：解析索引 → 定位首个真实分片 → 实际下载该分片。
分片下载失败或过小 → 判死。

分级过滤（避免单次网络抖动误杀）
--------------------------------
探活失败 ≠ 死链。本模块维护**连续失败计数**（持久化到 state 文件）：
- 连续失败 < FAIL_THRESHOLD → 保留（只记一次失败）
- 连续失败 ≥ FAIL_THRESHOLD → 丢弃该频道
- 探活成功 → 计数清零

白名单
------
`known_good.txt` 里列出的频道名永不丢弃（人工验证过的）。

参数
----
--workers N     并发探活数（默认 16）
--timeout S     单次请求超时秒（默认 6）
--max-lines N   每频道最多探测几条线路（默认 6）
--threshold N   连续失败多少次才丢弃（默认 3）
--report PATH   JSON 报告输出路径
--state PATH    失败计数持久化文件（默认与 report 同目录）
--whitelist PATH 已知可用频道名单
--no-probe      跳过探活（只做其他过滤）
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
import urllib.parse
import urllib.request

# UA 与 TVBox / mpv 播放器生态一致，否则服务端放行策略与实际播放不一致
UA = 'okhttp/3.12.0'

# ── 域级黑名单（QZTV 起播选线同款认知）────────────────
# 以下前缀在民用宽带上必然 403 / TCP 超时：
#   cmvideo.cn / chinamobile / cmcc / unicom / telecom → 运营商 IPTV
#   100.1.   → 移动运营商 CGNAT 地址段
#   192.168. / 172.16. / 10. / 127.0.0.1 / localhost → 内网地址
# 遇到这些前缀时直接判死，不计入探测成本，也不进入等待重试
DEAD_DOMAINS = (
    'cmvideo.cn', 'chinamobile', 'cmcc', 'unicom', 'telecom',
    '100.1.', '192.168.', '172.16.', '10.',
    '127.0.0.1', 'localhost',
)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


# ─── 内容判别 ────────────────────────────────────────

def is_mp4(head: bytes) -> bool:
    """MP4/ISO 基础媒体容器：字节 4..8 == b'ftyp'。对直播场景是点播文件，判死。"""
    return len(head) >= 12 and head[4:8] == b'ftyp'


def is_ts(buf: bytes) -> bool:
    """MPEG-TS：188 字节对齐，首字节 0x47（sync byte）。"""
    end = min(4096, len(buf))
    for i in range(0, end, 188):
        if i < len(buf) and buf[i] == 0x47:
            return True
    return False


def classify_content(head: bytes) -> tuple:
    """返回 (是否可用, 说明)。"""
    if not head:
        return True, 'empty'
    t = head.decode('utf-8', 'replace').lstrip()
    if not t:
        return True, 'empty'
    if t.startswith('#EXTM3U') or t.startswith('#EXTINF'):
        return True, 'HLS'
    if t.startswith('<'):
        return False, 'HTML'
    if is_mp4(head):
        return False, 'MP4'
    printable = all(0x20 <= ord(c) < 0x7f for c in t[:200])
    if printable and len(t) < 80:
        return False, 'errmsg'
    return True, 'binary'


def first_media_line(idx_text: str, base_url: str):
    """取 m3u8 索引里第一个真实分片/子索引的绝对地址。"""
    for line in idx_text.split('\n'):
        t = line.strip()
        if not t or t.startswith('#'):
            continue
        try:
            return urllib.parse.urljoin(base_url, t)
        except Exception:
            return None
    return None


# ─── 探活 ────────────────────────────────────────────

def _get(url: str, timeout: float, want_bytes: int):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    req.add_header('Range', f'bytes=0-{want_bytes - 1}')
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.status, r.read(want_bytes)


def probe(url: str, timeout: float = 6.0, deep: bool = True):
    """
    返回 (是否可用, 说明)。

    deep=True 时对 .m3u8 会继续定位并下载真实分片 —— 这才能识别
    「索引活着但分片已死」的假流。
    """
    if any(d in url for d in DEAD_DOMAINS):
        return False, 'dead-domain'
    try:
        status, head = _get(url, timeout, 1024)
    except urllib.error.HTTPError as e:
        return False, f'HTTP {e.code}'
    except Exception as e:
        return False, type(e).__name__

    if status < 200 or status >= 400:
        return False, f'HTTP {status}'

    ok, why = classify_content(head)
    if not ok:
        return False, why

    # 只读索引不够：对 m3u8 必须探真实分片
    if deep and (why == 'HLS' or url.lower().split('?')[0].endswith('.m3u8')):
        try:
            idx_text = head.decode('utf-8', 'replace')
            seg = first_media_line(idx_text, url)
            depth = 0
            # 主索引 → 子索引（最多两级）
            while seg and seg.lower().split('?')[0].endswith('.m3u8') and depth < 2:
                st2, h2 = _get(seg, timeout, 4096)
                if st2 < 200 or st2 >= 400:
                    return False, f'segHTTP {st2}'
                seg = first_media_line(h2.decode('utf-8', 'replace'), seg)
                depth += 1
            if not seg:
                return False, 'no-seg'
            st3, buf3 = _get(seg, timeout, 64 * 1024)
            if st3 < 200 or st3 >= 400:
                return False, f'segHTTP {st3}'
            if len(buf3) < 1024:
                return False, f'seg-tiny({len(buf3)}B)'
            return True, 'HLS+seg'
        except urllib.error.HTTPError as e:
            return False, f'segHTTP {e.code}'
        except Exception as e:
            return False, type(e).__name__

    return True, why


# ─── TVBox lives 结构 ─────────────────────────────────

def iter_live_channels(cfg: dict):
    """
    遍历 cfg['lives']，产出 (分组索引, 频道索引, 频道 dict, [url,...])。

    兼容两种结构：
      A) lives: [{group, channels:[{name, urls:[...]}]}]
      B) lives: [{name, url}]                     —— 老式单源
    """
    lives = cfg.get('lives') or []
    for gi, grp in enumerate(lives):
        if not isinstance(grp, dict):
            continue
        if isinstance(grp.get('channels'), list):
            for ci, ch in enumerate(grp['channels']):
                if not isinstance(ch, dict):
                    continue
                urls = ch.get('urls')
                if isinstance(urls, str):
                    urls = [urls]
                if not urls:
                    continue
                yield gi, ci, ch, [str(u) for u in urls]
        elif grp.get('url'):
            yield gi, None, grp, [str(grp['url'])]


def channel_name(ch: dict) -> str:
    return str(ch.get('name') or ch.get('channel') or ch.get('title') or '')


def split_url_label(url: str):
    """TVBox 的 url 可能是 '真实地址$备注' 或 '真实地址#名称'。"""
    for sep in ('$', '#'):
        if sep in url:
            return url.split(sep, 1)[0].strip(), sep
    return url.strip(), None


# ─── 状态持久化 ───────────────────────────────────────

def load_state(path) -> dict:
    if path and os.path.exists(path):
        try:
            return json.load(open(path, encoding='utf-8'))
        except Exception:
            return {}
    return {}


def save_state(path, state: dict) -> None:
    if not path:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def load_whitelist(path) -> set:
    names = set()
    if path and os.path.exists(path):
        for line in open(path, encoding='utf-8', errors='replace'):
            line = line.strip()
            if line and not line.startswith('#'):
                names.add(line)
    return names


# ─── 主流程 ───────────────────────────────────────────

def filter_lives(cfg: dict, *, workers=16, timeout=6.0, max_lines=6,
                 threshold=3, state_path=None, whitelist_path=None,
                 report_path=None, verbose=True):
    """
    就地过滤 cfg['lives']。返回统计 dict。
    """
    state = load_state(state_path)
    whitelist = load_whitelist(whitelist_path)
    # 旧计数必须合并进本次计数器，否则每轮都从 1 开始，永远达不到阈值
    fail_counts = collections.Counter(state)

    channels = list(iter_live_channels(cfg))
    if not channels:
        return {'total': 0, 'alive': 0, 'dropped': 0}

    # 预取每个频道要探测的线路
    plan = []
    for gi, ci, ch, urls in channels:
        raw_urls = urls[:max_lines]
        real_urls = [split_url_label(u)[0] for u in raw_urls]
        plan.append((gi, ci, ch, urls, raw_urls, real_urls))

    def check(item):
        gi, ci, ch, urls, raw_urls, real_urls = item
        tried = []
        winner = None
        for ru, real in zip(raw_urls, real_urls):
            ok, why = probe(real, timeout)
            tried.append({'url': ru, 'real': real, 'ok': ok, 'why': why})
            if ok:
                winner = (ru, real)
                break
        return gi, ci, ch, urls, tried, winner

    t0 = time.time()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(check, plan):
            results.append(r)
            if verbose and len(results) % 50 == 0:
                print(f'  probed {len(results)}/{len(plan)} ({time.time() - t0:.0f}s)', flush=True)

    drop = {}          # (gi, ci) -> reason
    report_alive = []
    report_dead = []

    for gi, ci, ch, urls, tried, winner in results:
        name = channel_name(ch)
        key = name or (urls[0] if urls else '')
        if winner:
            fail_counts.pop(key, None)
            report_alive.append({'group': gi, 'name': name, 'url': winner[0],
                                 'url_count': len(urls), 'tried': tried})
        else:
            n = fail_counts.get(key, 0) + 1
            fail_counts[key] = n
            whitelisted = key in whitelist
            if n >= threshold and not whitelisted:
                drop[(gi, ci)] = f'fail#{n}'
                report_dead.append({'group': gi, 'name': name, 'fails': n,
                                    'whitelisted': whitelisted, 'tried': tried})
            else:
                # 未达阈值或白名单 → 保留
                report_alive.append({'group': gi, 'name': name, 'url': urls[0],
                                     'url_count': len(urls), 'kept': 'fail#%d' % n,
                                     'tried': tried})

    # 落地过滤
    lives = cfg.get('lives') or []
    new_lives = []
    for gi, grp in enumerate(lives):
        if not isinstance(grp, dict):
            continue
        if isinstance(grp.get('channels'), list):
            kept = []
            for ci, ch in enumerate(grp['channels']):
                if not isinstance(ch, dict):
                    continue
                if (gi, ci) in drop:
                    continue
                kept.append(ch)
            if kept:
                grp = dict(grp)
                grp['channels'] = kept
                new_lives.append(grp)
        else:
            if (gi, None) in drop:
                continue
            new_lives.append(grp)
    cfg['lives'] = new_lives

    # 持久化失败计数
    if state_path:
        save_state(state_path, dict(fail_counts))

    stats = {
        'total': len(channels),
        'alive': sum(1 for r in report_alive if 'kept' not in r),
        'kept_pending': sum(1 for r in report_alive if 'kept' in r),
        'dropped': len(drop),
        'duration_s': round(time.time() - t0, 1),
        'dead': report_dead,
        'alive_detail': report_alive,
    }
    if report_path:
        os.makedirs(os.path.dirname(os.path.abspath(report_path)) or '.', exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=1)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description='直播源探活过滤器')
    ap.add_argument('--config', required=True, help='TVBox 配置 json')
    ap.add_argument('--out', required=True, help='过滤后输出 json')
    ap.add_argument('--workers', type=int, default=16)
    ap.add_argument('--timeout', type=float, default=6.0)
    ap.add_argument('--max-lines', type=int, default=6)
    ap.add_argument('--threshold', type=int, default=3)
    ap.add_argument('--report', default='')
    ap.add_argument('--state', default='')
    ap.add_argument('--whitelist', default='')
    ap.add_argument('--no-probe', action='store_true')
    args = ap.parse_args()

    cfg = json.loads(open(args.config, encoding='utf-8').read())
    if args.no_probe:
        json.dump(cfg, open(args.out, 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(',', ':'))
        print('probe skipped')
        return 0

    stats = filter_lives(
        cfg,
        workers=args.workers, timeout=args.timeout, max_lines=args.max_lines,
        threshold=args.threshold, state_path=args.state or None,
        whitelist_path=args.whitelist or None, report_path=args.report or None,
    )
    json.dump(cfg, open(args.out, 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print(f"channels {stats['total']}  alive {stats['alive']}  "
          f"pending {stats['kept_pending']}  dropped {stats['dropped']}  "
          f"({stats['duration_s']}s)")
    print(f"written: {args.out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
