#!/usr/bin/env python3
"""细看候选源的点播站点质量 + 直播源质量（直播是另一个待解决问题）"""
import json, subprocess, collections, re

UA = 'okhttp/3.12.0'

CAND = {
    '高天流云': 'https://gh-proxy.com/https://raw.githubusercontent.com/gaotianliuyun/gao/master/js.json',
    'gaoops': 'https://tvbox-public.gaoops.top/',
    '俊佬': 'http://home.jundie.top:81/top98.json',
    '香雅晴': 'https://gh-proxy.com/https://raw.githubusercontent.com/xyq254245/xyqonlinerule/main/XYQTVBox.json',
}


def fetch(url):
    r = subprocess.run(['curl', '-s', '-L', '--max-time', '30', '-A', UA, url],
                       capture_output=True, text=True, errors='replace')
    return r.stdout


for name, url in CAND.items():
    print("=" * 76)
    print(f"【{name}】")
    print("=" * 76)
    raw = fetch(url)
    try:
        d = json.loads(raw)
    except Exception as e:
        print(f"  JSON 解析失败: {e}")
        print(f"  原文尾部: ...{raw[-120:]!r}")
        print()
        continue

    sites = d.get('sites', []) or []
    lives = d.get('lives', []) or []
    print(f"  spider: {str(d.get('spider',''))[:70]}")
    print(f"  sites={len(sites)}  lives={len(lives)}  parses={len(d.get('parses',[]) or [])}")
    print(f"  直播组: {[g.get('group','?')[:26] for g in lives][:8]}")

    # 直播：每组取第一个频道的 URL 探测
    print("  直播抽样:")
    for g in lives[:6]:
        chs = g.get('channels', [])
        if not chs:
            continue
        u = chs[0].get('urls', [''])[0]
        try:
            r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                                '--max-time', '10', '-A', UA, u],
                               capture_output=True, text=True, errors='replace')
            code = r.stdout.strip()
        except Exception:
            code = 'ERR'
        flag = '✅' if code == '200' else '❌'
        print(f"    {flag} {g.get('group','?')[:24]:26s} {chs[0].get('name','')[:16]:18s} {code}")

    # 点播：展示前 10 个站点名
    print("  点播前10:")
    for s in sites[:10]:
        print(f"    {str(s.get('name',''))[:70]}")
    print()
