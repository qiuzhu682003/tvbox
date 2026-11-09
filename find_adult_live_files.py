#!/usr/bin/env python3
"""
找出【含成人频道的直播源文件】。
思路：逐个下载直播源文件，扫描频道名，算成人命中率。
命中率高的整源屏蔽（而不是逐个频道过滤）。
"""
import json, subprocess, re, concurrent.futures

UA = 'okhttp/3.12.0'

raw = subprocess.run(['curl', '-s', '--max-time', '40', '-A', UA, 'https://tv.cc0cd.cc.cd'],
                     capture_output=True, text=True, errors='replace').stdout
d = json.loads(raw)
lives = d.get('lives', [])

srcs = []
for g in lives:
    u = g.get('url') or g.get('api') or ''
    if u.startswith('http'):
        srcs.append({'name': g.get('name', '?'), 'url': u,
                     'ua': g.get('ua', ''), 'timeout': g.get('timeout', 15)})

ADULT = re.compile(
    r'偷窥|自慰|做爱|口交|性爱|裸聊|裸播|全裸|一丝不挂|强姦|强奸|调教|'
    r'露出|偷情|情趣|约炮|一夜情|AV女优|AV主播|AV资源|番号|里番|福利姬|'
    r'痴女|嫩模|素人|麻豆|传媒|三级片|伦理片|18禁|禁漫|Hentai|'
    r'Pornhub|xvideos|xhamster|redtube|Jable|SupJav|MissAV|JavBus|JavDb|'
    r'超碰|小萝莉爱爱|重口味|媚宅|涩涩|色播|色猫|大尺度|香艳|艳遇|情涩|'
    r'巨乳|爆乳|奶子|骚货|骚年|女优|色情片|偷拍|啪啪|猛操|狠操|强上|巨屌|'
    r'塞满|囚禁|无码|有码|SEX|Sex|sex|FC2|Porm|Pron|JAV|jav',
    re.IGNORECASE)

SAFE = re.compile(
    r'速度与激情|回家的诱惑|犯罪现场|赤裸惊情|生活娱乐|综合频道|新闻频道|'
    r'CCTV|卫视|少儿|购物|农业农村|骚火|白嫖|裸奔的蜗牛|漫威|粉丝福利|'
    r'茶杯狐|WebDav|bravo|travel|知识|综艺|科普|纪实|纪录片|资讯|体育|'
    r'赛事|青春|动漫|剧场|电影|电视剧|连续剧|BBC|新闻|挑战|达人|'
    r'脱口秀|音乐|演唱会|游戏|电竞|旅游|经济|军事|农业|戏曲',
    re.IGNORECASE)


def fetch_src(s):
    cmd = ['curl', '-s', '-L', '--max-time', str(max(int(s['timeout'] or 15), 20)),
           '-A', s['ua'] or UA, s['url']]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
        return s, r.stdout
    except Exception:
        return s, ''


with concurrent.futures.ThreadPoolExecutor(8) as ex:
    fetched = list(ex.map(fetch_src, srcs))

print(f"{'源名':26s}{'频道':>7s}{'成人':>7s}{'占比':>8s}  判定")
print('-' * 74)
block = []
for s, content in fetched:
    lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
    if len(lines) <= 1:
        continue
    names = []
    for l in lines:
        nm = l.split(',')[0].strip() if ',' in l else l[:40].strip()
        if nm and not nm.startswith('#'):
            names.append(nm)
    if not names:
        continue
    bad = 0
    for nm in names:
        if SAFE.search(nm):
            continue
        if ADULT.search(nm):
            bad += 1
    ratio = bad / len(names)
    if ratio > 0.02:
        print(f"{s['name'][:25]:26s}{len(names):>7d}{bad:>7d}{ratio*100:>7.1f}%  🔴 建议屏蔽")
        block.append({'name': s['name'], 'url': s['url'], 'channels': len(names),
                      'adult': bad, 'ratio': round(ratio, 4)})
    elif bad:
        print(f"{s['name'][:25]:26s}{len(names):>7d}{bad:>7d}{ratio*100:>7.1f}%  🟡 少量，靠频道过滤兜底")

print()
print(f"需整源屏蔽: {len(block)} 个，合计 {sum(b['channels'] for b in block)} 频道")
for b in block:
    print(f"  {b['channels']:7d} 频道  成人{b['adult']:6d} ({b['ratio']*100:.1f}%)  {b['name'][:24]:26s} {b['url'][:56]}")

json.dump(block, open('/tmp/live_block_files.json', 'w'), ensure_ascii=False, indent=1)
print("\n已存 /tmp/live_block_files.json")
