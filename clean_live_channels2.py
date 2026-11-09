#!/usr/bin/env python3
"""
更精确的直播频道成人过滤：
- 去掉会误杀正常影视/综艺的词（速度与激情、回家的诱惑、干就完了、bravo…）
- 保留明确成人词
输出过滤后的直播配置
"""
import json, re

SRC = '/tmp/cur_clean.json'
OUT = '/tmp/tvbox-live-clean.json'

# 明确成人特征（保留）
ADULT = [
    # 强信号
    '偷窥', '自慰', '做爱', '口交', '性爱', '裸聊', '裸播', '裸体', '全裸', '一丝不挂',
    'AV女优', 'AV主播', 'AV资源', 'AV影片', '日AV', '无码流出', '无码视频', '有码流出',
    '日本AV', '步兵番号', '番号', '里番', '本子', '福利姬', '痴女', '御姐诱惑', '调教',
    '露出', '露出癖', '偷情', '情趣', '色情频道', '成人频道', '成人视频', '成人影片',
    '小萝莉爱爱', '萝莉爱爱', '嫩模', '主播福利', '色情直播', '约炮', '一夜情',
    '制服诱惑', '丝袜诱惑', '巨乳', '爆乳', '奶子', '骚货', '骚年', '淫', '媚',
    '女优', '情涩', '小电影', '三级片', '伦理片', '18禁', '禁漫', 'R18', 'Hentai',
    'Pornhub', 'xvideos', 'xhamster', 'redtube', 'spankbang', 'onlyfans', 'Jable',
    'SupJav', 'MissAV', 'JavBus', 'JavDb', '麻豆传媒', '星辰传媒', '国产传媒', '蜜桃传媒',
    '麻豆视频', '麻豆电影', '素人', '无码资源', '有码资源', '重口', '小电影',
    '干柴烈火', '激情时刻', '性福时刻', '春色满园', '桃花运', '桃花岛', '春宵',
    '媚宅', '涩涩', '色播', '色猫', '色视频', '色情片', '大尺度', '香艳', '艳遇',
]

# 会误杀正常内容的词（出现这些就不算成人）
SAFE_IF_CONTAINS = [
    '速度与激情', '回家的诱惑', '干就完了', 'bravo', 'AVAZ', 'travel',
    '知识', '综艺', '科普', '纪实', '纪录片', '资讯', '体育', '赛事',
    '纯情', '青春', '动漫', '二次元', '剧场', '电影', '电视剧', '连续剧',
    'BBC', 'CCTV', '卫视', '新闻', '演播厅', '挑战', '达人', '脱口秀',
    '音乐现场', '演唱会', 'MV', '游戏', '电竞', '直播游戏',
]

# 直播源名级成人源（整组剔除）
ADULT_GROUPS = re.compile(
    r'成人|18\+|sex|porm|porn|fc2|麻豆|传媒|番号|伦理|三级|自拍|福利|'
    r'媚|丝袜|诱惑|无码|有码|偷拍|约炮|裸|骚|pron|jable|missav|'
    r'超碰|激情|艳|情趣|色情|av片', re.IGNORECASE)


def is_adult_channel(name, group):
    blob = f"{name} {group}"
    for s in SAFE_IF_CONTAINS:
        if s in blob:
            return False
    for a in ADULT:
        if a.lower() in blob.lower():
            return True
    return False


d = json.load(open(SRC))
lives = d.get('lives', [])

kept_groups = []
removed_ch = 0
removed_groups = 0
total = 0
samples = []

for g in lives:
    gname = str(g.get('group', ''))
    if ADULT_GROUPS.search(gname):
        removed_groups += 1
        removed_ch += len(g.get('channels', []))
        continue
    keep = []
    for c in g.get('channels', []):
        total += 1
        cn = str(c.get('name', ''))
        if is_adult_channel(cn, gname):
            removed_ch += 1
            if len(samples) < 25:
                samples.append((gname[:22], cn[:42]))
            continue
        keep.append(c)
    if keep:
        g2 = dict(g)
        g2['channels'] = keep
        kept_groups.append(g2)

print(f"直播组 {len(lives)} → {len(kept_groups)}  (整组剔除 {removed_groups})")
print(f"频道 {total} → 剩余 {total - removed_ch}  (剔除 {removed_ch})")
print("\n剔除样本:")
for g, n in samples:
    print(f"  {g:24s} {n}")

json.dump({'lives': kept_groups}, open(OUT, 'w'), ensure_ascii=False)
print(f"\n已写 {OUT}")
