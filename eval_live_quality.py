#!/usr/bin/env python3
"""
对比各候选源的【直播】质量。
直播是当前最大痛点（转圈），所以重点看：
1) 直播组数量、频道总数
2) 抽样真实分片下载速度（这才是播放器体验）
"""
import json, subprocess, collections, random, concurrent.futures

UA = 'okhttp/3.12.0'


def fetch(url):
    try:
        r = subprocess.run(['curl', '-s', '-L', '--max-time', '30', '-A', UA, url],
                           capture_output=True, text=True, errors='replace')
        return r.stdout
    except Exception:
        return ''


def clean(s):
    return ''.join(ch for ch in s if ord(ch) >= 0x20)


def probe(url):
    """返回 (组, 频道, 索引ok?, 分片HTTP, 秒, KB/s)"""
    try:
        r = subprocess.run(['curl', '-s', '--max-time', '10', '-A', UA, url],
                           capture_output=True, text=True, errors='replace')
    except Exception:
        return ('', '', False, 'ERR', 0, 0)
    if not r.stdout.strip().startswith('#EXTM3U'):
        return ('', '', False, 'no-idx', 0, 0)
    seg = None
    for line in r.stdout.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            seg = clean(line)
            break
    if not seg:
        return ('', '', True, 'no-seg', 0, 0)
    try:
        r2 = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}|%{size_download}|%{time_total}',
             '--max-time', '20', '-A', UA, seg],
            capture_output=True, text=True, errors='replace')
    except Exception:
        return ('', '', True, 'ERR', 0, 0)
    p = r2.stdout.split('|')
    if len(p) < 3:
        return ('', '', True, 'ERR', 0, 0)
    size = int(p[1]) if p[1].isdigit() else 0
    t = float(p[2]) if p[2] else 0
    return ('', '', True, p[0], t, size / 1024 / t if t > 0 else 0)


CAND = {
    'tvyuan(当前)': 'https://tv.cc0cd.cc.cd',
    '高天流云': 'https://gh-proxy.com/https://raw.githubusercontent.com/gaotianliuyun/gao/master/js.json',
    'gaoops': 'https://tvbox-public.gaoops.top/',
    '俊佬': 'http://home.jundie.top:81/top98.json',
}

for name, url in CAND.items():
    raw = fetch(url)
    try:
        d = json.loads(raw)
    except Exception:
        print(f"【{name}】拉取失败\n")
        continue
    lives = d.get('lives', []) or []
    n_ch = sum(len(g.get('channels', [])) for g in lives)
    print(f"【{name}】直播组 {len(lives)}, 频道总数 {n_ch}")

    # 抽样：每组取第 1 个频道
    samples = []
    for g in lives[:14]:
        chs = g.get('channels', [])
        if not chs:
            continue
        c = chs[0]
        us = c.get('urls', [])
        if us:
            samples.append((g.get('group', '?')[:20], c.get('name', '')[:14], us[0]))

    if samples:
        with concurrent.futures.ThreadPoolExecutor(6) as ex:
            res = list(ex.map(lambda s: probe(s[2]), samples))
        for (g, cn, _), (_, _, idx, code, t, sp) in zip(samples, res):
            flag = '✅' if code == '200' else '❌'
            print(f"   {flag} {g:22s} {cn:15s} {str(code):7s} {t:5.1f}s {sp:7.0f}KB/s")
        ok = sum(1 for r in res if r[3] == '200')
        fast = sum(1 for r in res if r[3] == '200' and r[5] > 3000)
        print(f"   -> 可用 {ok}/{len(res)}, 其中快(>3000KB/s) {fast}")
    print()
