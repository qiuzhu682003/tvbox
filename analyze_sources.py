#!/usr/bin/env python3
"""按上游源归类站点，评估每个源的规模/速度/成人含量，
为「换高质量源 + 屏蔽成人源」提供决策依据。"""
import json, collections, re

CFG = '/tmp/cur.json'
d = json.load(open(CFG))
sites = d.get('sites', [])

# 站点名里带 「源名」 的分组标记，如：xxx 「tvyuan」 [1.9s]
src_re = re.compile(r'「([^」]+)」')
no_src = re.compile(r'^(?:\[([^\]]*)\]\s*)?(.+?)\s*$')

by_src = collections.defaultdict(list)
for s in sites:
    name = str(s.get('name', ''))
    m = src_re.search(name)
    src = m.group(1) if m else '(无标记)'
    by_src[src].append(s)

ADULT = ['黄AV', '番号', '成人', '伦理', '三级', '自慰', '偷拍', '约炮', '裸', '无码',
         '有码', '小电影', '重口', '福利姬', '色情', '情色', '萝莉', '少妇', '熟女',
         '丝袜', '诱惑', '御姐', '黑丝', '白丝', '制服', '春堂', '搜视', 'souav',
         'jvid', 'mdx', 't28', '里番', 'jav', 'porn', 'sex', '精品']


def adult_hits(sites_):
    n = 0
    examples = []
    for s in sites_:
        blob = ' '.join(str(s.get(k, '')) for k in ('key', 'name', 'api')).lower()
        for k in ADULT:
            if k.lower() in blob:
                n += 1
                examples.append((s.get('key', ''), str(s.get('name', ''))[:58]))
                break
    return n, examples


print(f"{'上游源':16s}{'站点数':>8s}{'成人':>6s}{'占比':>8s}")
print('-' * 44)
total_adult = 0
for src, ss in sorted(by_src.items(), key=lambda kv: -len(kv[1])):
    an, _ = adult_hits(ss)
    total_adult += an
    pct = an / len(ss) * 100 if ss else 0
    print(f"{src:16s}{len(ss):>8d}{an:>6d}{pct:>7.1f}%")

print(f"\n合计: {len(sites)} 站点, 成人命中 {total_adult}")

print("\n" + "=" * 70)
print("各源成人站点明细")
print("=" * 70)
for src, ss in sorted(by_src.items(), key=lambda kv: -len(kv[1])):
    an, ex = adult_hits(ss)
    if not an:
        continue
    print(f"\n【{src}】{an} 个成人站点:")
    for k, n in ex:
        print(f"   {k[:20]:22s} {n}")

# 无源标记的站点（可能是 type:3 本地爬虫，通常质量差）
print("\n" + "=" * 70)
print("按 type 分布（type=3 是本地爬虫，质量通常最差）")
print("=" * 70)
t = collections.Counter(s.get('type') for s in sites)
for ty, n in sorted(t.items(), key=lambda kv: -kv[1]):
    ss = [s for s in sites if s.get('type') == ty]
    an, _ = adult_hits(ss)
    print(f"  type={ty}: {n} 个, 成人 {an}")
