#!/usr/bin/env python3
"""
补充规则：清除 clun.top 采集源带来的成人站，以及其它漏网之鱼。
先预览再写入。
"""
import json, urllib.request, sys

TOKEN = open('/tmp/tvbox_admin_token.txt').read().strip()
BASE = 'http://127.0.0.1:5678'

RULES = [
    # clun.top 采集站（名字里带该域名的整批成人采集站）
    ('clun采集源', 'name', r'clun\.top'),
    # 常见成人站名/缩写（精确词组，避免误杀"芒果/滴滴"这类正常词）
    ('成人站名', 'name', r'JavBus|JavDb|javdb|SupJav|xojav|MissAV|123AV|Youavhub|'
                      r'owoav|91porn|Pornhub|RedTube|Hanime|Sukebei|Netflav|netflav|'
                      r'Jable|jable|XP天堂|女优色库|涩涩|色播|色猫|色南国|'
                      r'色资源|资源库|成人资源|麻豆|鸡坤|玉兔|大奶子|奶香|湿妹|'
                      r'乱伦|猎奇|玉蚌|玉兔含珠|玉兔|香蕉超清|黄果短剧|黄果剧场|'
                      r'黄豆短剧|恋丝影视|花都影院|小黄书|最色|聚优AV|'
                      r'大奶子|奶香|色情|性爱|肉视频|抖阴|骚|淫'),
    # 明确成人 api 域名（91系等）
    ('成人api', 'api', r'91md\.me|91mdd|adult|sexya|javzhibo|porn'),
]


def api(path, method='GET', body=None):
    req = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={'Authorization': 'Bearer ' + TOKEN,
                 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {'error': e.code, 'body': e.read().decode()[:200]}
    except Exception as e:
        return {'error': str(e)}


print("预览：")
total = set()
to_apply = []
for label, field, pattern in RULES:
    res = api('/admin/blacklist/regex/test', 'POST', {'pattern': pattern, 'field': field})
    matched = res.get('matched', []) if isinstance(res, dict) else []
    if not matched:
        print(f"  {label:14s} 0 命中 —— 跳过")
        continue
    names = [m.get('name', '')[:44] for m in matched[:4]]
    print(f"  {label:14s} {len(matched):3d} 命中: {names}")
    for m in matched:
        total.add(m.get('name', ''))
    to_apply.append((label, field, pattern, len(matched)))

print(f"\n合计唯一: {len(total)}")

if '--apply' not in sys.argv:
    print("\n（预览模式，加 --apply 写入）")
    sys.exit(0)

print("\n写入…")
for label, field, pattern, n in to_apply:
    res = api('/admin/blacklist/regex', 'POST',
               {'pattern': pattern, 'field': field, 'enabled': True})
    print(f"  {label:14s} [{field}] {n:3d} -> {'ok' if res.get('success') or res.get('id') else res}")
print("\n完成")
