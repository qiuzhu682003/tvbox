#!/usr/bin/env python3
"""评估候选 TVBox 源：规模、成人源占比、站点类型分布。
用于挑选"高质量 + 干净"的替换源。"""
import json, subprocess, re, collections, sys

UA = 'okhttp/3.12.0'

CANDIDATES = [
    ('tvyuan-简洁', 'https://tv.cc0cd.cc.cd/jj'),
    ('tvyuan-全量', 'https://raw.githubusercontent.com/25175/tvyuan/master/tvbox_full.json'),
    ('tvyuan-多仓', 'https://raw.githubusercontent.com/25175/tvyuan/master/tvbox_multi.json'),
    ('gaoops-主线', 'https://tvbox-public.gaoops.top/'),
    ('gaoops-gitlab', 'https://gitlab.com/gao777520/tvbox-config/raw/main/tvbox.json'),
    ('无邪多仓', 'https://gh-proxy.com/https://raw.githubusercontent.com/wxrjck/-YSC-/refs/heads/main/wx.json'),
    ('俊佬', 'http://home.jundie.top:81/top98.json'),
    ('道长', 'https://gitlab.com/duomv/dzhipy/-/raw/main/index.json'),
    ('高天流云', 'https://gh-proxy.com/https://raw.githubusercontent.com/gaotianliuyun/gao/master/js.json'),
    ('香雅晴', 'https://gh-proxy.com/https://raw.githubusercontent.com/xyq254245/xyqonlinerule/main/XYQTVBox.json'),
    ('王二小', 'http://tvbox.王二小放牛娃.top'),
    ('摸鱼儿', 'http://我不是.摸鱼儿.top'),
]

ADULT = ['🔞', '黄AV', 'AV资源', '番号', '成人', '伦理', '三级', '自慰', '偷拍', '约炮',
         '裸聊', '福利', '色情', '情色', '无码', '有码', '小电影', '重口', '福利姬',
         '萝莉', '少妇', '熟女', '丝袜', '诱惑', '御姐', '黑丝', '制服', '春堂',
         '搜视', '里番', '18禁', '禁漫', 'JAV', 'jav', 'porn', 'Porn', 'sex', 'Sex',
         'pgxdy', 'msnii', 'xrbsp', 'soav', 'souav', 'mdx', 't28', 'jvid',
         '媚', '爆乳', '美腿', '翘臀', '绅士', '偷窥', '福利区']

GOOD = ['央视', 'CCTV', '卫视', '4K', '蓝光', '高清', '豆瓣', '时光', '追剧', '热播',
        '电影', '电视剧', '综艺', '动漫', '纪录片', '少儿', '新闻', '体育', '秒播']


def fetch(url):
    try:
        r = subprocess.run(['curl', '-s', '-L', '--max-time', '30', '-A', UA, url],
                           capture_output=True, text=True, errors='replace')
        return r.stdout
    except Exception:
        return ''


def analyze(name, url):
    raw = fetch(url)
    if not raw.strip():
        print(f"{name:16s} ❌ 拉取失败/空")
        return None
    try:
        d = json.loads(raw)
    except Exception:
        print(f"{name:16s} ❌ 非 JSON (前80字: {raw[:80]!r})")
        return None
    sites = d.get('sites', []) or []
    parses = d.get('parses', []) or []
    lives = d.get('lives', []) or []
    n_ad = 0
    ad_names = []
    for s in sites:
        blob = ' '.join(str(s.get(k, '')) for k in ('key', 'name', 'api'))
        if any(k.lower() in blob.lower() for k in ADULT):
            n_ad += 1
            ad_names.append(str(s.get('name', ''))[:44])
    t = collections.Counter(s.get('type') for s in sites)
    print(f"{name:16s} ✅ sites={len(sites):4d} parses={len(parses):3d} lives={len(lives):4d} "
          f"成人={n_ad:3d} type3={t.get(3,0):4d}")
    if ad_names:
        print(f"{'':16s}    成人样本: {ad_names[:5]}")
    return d


if __name__ == '__main__':
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name, url in CANDIDATES:
        if only and only not in name:
            continue
        analyze(name, url)
        print()
