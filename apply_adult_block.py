#!/usr/bin/env python3
"""
生成并应用「屏蔽成人/擦边源」的正则黑名单规则。

原则：
1. 用【精确词组】而非宽泛词，避免误杀正常片源（MTV音乐、919体育、人人影视…）
2. 先用 /admin/blacklist/regex/test 预览命中，再决定是否写入
3. 每条规则单独写入，便于日后单独调整/删除
"""
import json, subprocess, urllib.request, sys

TOKEN = open('/tmp/tvbox_admin_token.txt').read().strip()
BASE = 'http://127.0.0.1:5678'

# ── 规则集：每条 = (说明, 字段, 正则) ──────────────────────
# 精确成人词组，避免误伤
RULES = [
    ('符号标记', 'name', r'🔞'),
    ('AV类', 'name', r'AV资源|AV电影|AV视频|黄AV|看AV'),
    ('番号类', 'name', r'番号'),
    ('成人直白', 'name', r'成人\d*|成人站|成人视频|成人影片'),
    ('伦理三级', 'name', r'伦理片|三级片|三八级|伦理'),
    ('自慰偷拍', 'name', r'自慰|偷拍|偷窥|裸聊|裸播'),
    ('约炮福利', 'name', r'约炮|福利姬|福利区|福利资源|发福利'),
    ('色情情色', 'name', r'色情|情色|黄色片|毛片'),
    ('无码有码', 'name', r'无码|有码|高清无码'),
    ('小电影重口', 'name', r'小电影|重口味|重口'),
    ('萝莉少妇', 'name', r'萝莉|少妇|熟女|御姐'),
    ('丝袜诱惑', 'name', r'丝袜诱惑|黑丝诱惑|制服诱惑|爆乳|翘臀|媚'),
    ('特定站名', 'name', r'春堂|搜视|里番|禁漫|18禁'),
    ('英文', 'name', r'\bporn\b|\bsex\b|\bjav\b|\bhentai\b|\bav\b'),
    # api 域名维度（站点名干净但域名露馅的）
    ('成人域名', 'api', r'pgxdy|msnii|xrbsp|soav|souav|jvid|mdx\.com|t28\.|javlib|avdod|91porn'),
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


print("=" * 72)
print("预览：每条规则会命中哪些站点")
print("=" * 72)
total = set()
apply_list = []
for label, field, pattern in RULES:
    res = api('/admin/blacklist/regex/test', 'POST', {'pattern': pattern, 'field': field})
    matched = res.get('matched', []) if isinstance(res, dict) else []
    if not matched:
        print(f"  {label:14s} 0 命中 —— 跳过")
        continue
    names = [m.get('name', '')[:46] for m in matched[:5]]
    print(f"  {label:14s} {len(matched):3d} 命中: {names}")
    for m in matched:
        total.add(m.get('name', ''))
    apply_list.append((label, field, pattern, len(matched)))

print()
print(f"合计唯一站点: {len(total)}")

if '--apply' not in sys.argv:
    print("\n（预览模式。加 --apply 才会真正写入）")
    sys.exit(0)

print("\n写入规则…")
for label, field, pattern, n in apply_list:
    res = api('/admin/blacklist/regex', 'POST',
               {'pattern': pattern, 'field': field, 'enabled': True})
    ok = 'ok' if res.get('success') or res.get('id') or res.get('rule') else res
    print(f"  {label:14s} [{field}] {n:3d} 命中 -> {ok}")

print("\n完成。重新拉配置验证…")
