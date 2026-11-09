#!/usr/bin/env python3
"""
把成人直播源写入聚合器的 lives 黑名单（按源 URL 匹配）。
黑名单在 step 4.5 执行，早于 step 6.5 的直播展开 ——
所以屏蔽后这些源根本不会被下载（省掉 4 万+ 频道的抓取）。
"""
import json, urllib.request, sys

TOKEN = open('/tmp/tvbox_admin_token.txt').read().strip()
BASE = 'http://127.0.0.1:5678'

dropped = json.load(open('/tmp/live_dropped.json'))
print(f"待屏蔽成人直播源: {len(dropped)} 个，合计 {sum(d['channels'] for d in dropped)} 频道\n")


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


if '--apply' not in sys.argv:
    for d in dropped:
        print(f"  {d['channels']:6d} 频道  {d['name'][:24]:26s} {d['url'][:60]}")
    print("\n（预览模式，加 --apply 写入）")
    sys.exit(0)

for d in dropped:
    res = api('/admin/blacklist', 'POST', {'type': 'lives', 'id': d['url']})
    ok = res.get('success')
    print(f"  {'✅' if ok else '❌'} {d['name'][:22]:24s} {d['channels']:6d} 频道 -> {res}")

print("\n完成。现在重新聚合，让黑名单生效…")
