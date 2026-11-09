#!/usr/bin/env python3
"""
评估候选源【点播质量】：采样各源的 type=1/0 站点，实际请求其 API，
检查是否返回真实的影视数据（而不是空/报错），并估算延迟。
type=3 本地爬虫质量另议（依赖 JAR，不在此测）。
"""
import json, subprocess, collections, random

UA = 'okhttp/3.12.0'

CAND = {
    '当前-肥猫': 'http://xn--z7x900a.net/',
    '当前-qistfty': 'https://gh-proxy.com/raw.githubusercontent.com/qist/tvbox/master/fty.json',
    '高天流云': 'https://gh-proxy.com/https://raw.githubusercontent.com/gaotianliuyun/gao/master/js.json',
    'gaoops': 'https://tvbox-public.gaoops.top/',
    '俊佬': 'http://home.jundie.top:81/top98.json',
    'tvyuan全量': 'https://raw.githubusercontent.com/25175/tvyuan/master/tvbox_full.json',
    'tvyuan当前': 'https://tv.cc0cd.cc.cd',
}


def fetch(url):
    try:
        r = subprocess.run(['curl', '-s', '-L', '--max-time', '30', '-A', UA, url],
                           capture_output=True, text=True, errors='replace')
        return r.stdout
    except Exception:
        return ''


def probe_site(s):
    """请求站点 API，看是否返回有效剧集列表"""
    api = str(s.get('api', '')).strip()
    if not api or not api.startswith('http'):
        return None
    key = str(s.get('key', ''))
    ext = str(s.get('ext', '') or '')
    url = api
    if 'provide/vod' in api and ext:
        url = f"{api}?ac=list&wd={key}&ext={ext}"
    try:
        r = subprocess.run(['curl', '-s', '--max-time', '12', '-A', UA, url],
                           capture_output=True, text=True, errors='replace')
        body = r.stdout
        if not body.strip():
            return ('空响应', 0)
        try:
            d = json.loads(body)
        except Exception:
            return ('非JSON', len(body))
        if isinstance(d, dict):
            if 'list' in d and isinstance(d['list'], list):
                return (f"{len(d['list'])}条剧集", len(body))
            if 'data' in d:
                return ('有data', len(body))
            return (f"键:{list(d.keys())[:3]}", len(body))
        if isinstance(d, list):
            return (f"{len(d)}条", len(body))
        return ('其他', len(body))
    except Exception as e:
        return ('ERR', 0)


for name, url in CAND.items():
    raw = fetch(url)
    try:
        d = json.loads(raw)
    except Exception:
        print(f"【{name}】拉取失败")
        continue
    sites = d.get('sites', []) or []
    # 只测 type 0/1（真实 API 站），type=3 是本地爬虫
    api_sites = [s for s in sites if s.get('type') in (0, 1) and str(s.get('api', '')).startswith('http')]
    print(f"【{name}】总 {len(sites)} 站, API型 {len(api_sites)} 个, 直播 {len(d.get('lives',[]) or [])}")
    if api_sites:
        random.seed(42)
        sample = random.sample(api_sites, min(6, len(api_sites)))
        ok = 0
        for s in sample:
            res = probe_site(s)
            if res is None:
                continue
            desc, size = res
            good = ('条剧集' in desc) or ('条' in desc)
            if good:
                ok += 1
            print(f"   {'✅' if good else '❌'} {str(s.get('name',''))[:40]:42s} {desc}")
        print(f"   -> 可用 {ok}/{len(sample)}")
    print()
