#!/usr/bin/env python3
"""
在保留的直播源里，找出含成人频道名的频道并剔除。
做法：读取当前聚合后的 lives（已展开），按频道名/组名过滤成人内容，
写回一个自定义直播配置（tvbox-live-clean.json），供电视直接使用。
同时统计过滤效果。
"""
import json, re, collections

SRC = '/tmp/cur_clean.json'

ADULT_CH = re.compile(
    r'裸|骚|做爱|无码|有码|三级|伦理|自拍|约炮|福利|色情|私拍|偷拍|巨乳|奶子|'
    r'情涩|里番|番号|开房|自慰|激情|艳遇|情色|媚|诱惑|丝袜|制服|御姐|萝莉|'
    r'少妇|熟女|麻豆|传媒|18\+|成人|AV|av片|女优|露出|偷情|性感|魅惑|'
    r'Porn|porn|Sex|sex|18禁|禁漫|福利姬|HD麻豆|无码资源|有码资源|'
    r'红果|小黄书|涩涩|撸|射|干|插|肏|屄|逼|骚货|御姐诱惑|美腿诱惑',
    re.IGNORECASE)

# 白名单：这些是正常片名/台名，不能误杀
SAFE = re.compile(
    r'犯罪现场|赤裸惊情|生活娱乐|综合频道|新闻频道|电影频道|少儿频道|'
    r'购物频道|科教频道|军事频道|农业农村|奥林匹克|音乐频道|戏曲频道',
    re.IGNORECASE)

d = json.load(open(SRC))
lives = d.get('lives', [])
print(f"聚合后直播组: {len(lives)}")

total_ch = 0
bad_ch = 0
clean_groups = []
for g in lives:
    chs = g.get('channels', [])
    total_ch += len(chs)
    keep = []
    for c in chs:
        blob = ' '.join(str(c.get(k, '')) for k in ('name', 'group'))
        if ADULT_CH.search(blob) and not SAFE.search(blob):
            bad_ch += 1
            continue
        keep.append(c)
    if keep:
        g2 = dict(g)
        g2['channels'] = keep
        clean_groups.append(g2)

print(f"频道总数: {total_ch}  剔除成人频道: {bad_ch}  剩余: {total_ch - bad_ch}")

# 看看剔了哪些
removed = []
for g in lives:
    for c in g.get('channels', []):
        blob = ' '.join(str(c.get(k, '')) for k in ('name', 'group'))
        if ADULT_CH.search(blob) and not SAFE.search(blob):
            removed.append((g.get('group', '?')[:22], str(c.get('name', ''))[:40]))
print(f"\n剔除样本 (前 25):")
for g, n in removed[:25]:
    print(f"  {g:24s} {n}")

json.dump({'lives': clean_groups}, open('/tmp/tvbox-live-clean.json', 'w'),
          ensure_ascii=False)
print(f"\n已生成 /tmp/tvbox-live-clean.json ({len(clean_groups)} 组)")
