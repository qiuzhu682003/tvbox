#!/usr/bin/env python3
"""测试 403/不通的直播源在换 UA / 加 Referer 后能否救活。"""
import json, subprocess

BROWSER_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36')

d = json.load(open('/tmp/final_tv.json'))
targets = []
seen = set()
for g in d.get('lives', []):
    gn = g.get('group', '?')
    for c in g.get('channels', []):
        for u in c.get('urls', [])[:1]:
            if u in seen:
                continue
            seen.add(u)
            targets.append((f"{gn[:20]}/{c.get('name','')[:12]}", u))
            break
        else:
            continue
        break

UA_SETS = [
    ('okhttp', 'okhttp/3.12.0', None),
    ('browser', BROWSER_UA, None),
    ('browser+ref', BROWSER_UA, 'http://www.google.com/'),
    ('curl', 'curl/8.7.1', None),
]


def try_fetch(url, ua, ref):
    cmd = ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '12', '-A', ua]
    if ref:
        cmd += ['-e', ref]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
        return r.stdout.strip()
    except Exception:
        return 'ERR'


print(f"{'源':34s}" + ''.join(f"{n:14s}" for n, _, _ in UA_SETS))
print('-' * 90)
for lbl, u in targets[:14]:
    row = []
    for _, ua, ref in UA_SETS:
        row.append(try_fetch(u, ua, ref))
    print(f"{lbl:34s}" + ''.join(f"{c:14s}" for c in row))
