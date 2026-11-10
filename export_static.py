#!/usr/bin/env python3
"""从本地 tvbox-source-aggregator 导出可静态托管的 TVBox 配置。

聚合器输出里所有 Spider JAR 都被改写成 {BASE_URL}/jar/<key> 代理地址，
静态部署没有这个代理，因此按 SQLite 里的 jar:<key> 映射还原为原始 URL
（原始源为 gitee / gh-proxy / 源站自有域名，电视端直连可达）。
图片代理 pic 无静态等价物，直接删除。
"""
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

AGG_DIR = Path(os.environ.get("AGG_DIR", r"C:\Users\qiuzhu\ZCodeProject\tvbox-source-aggregator"))
SRC = Path(os.environ.get("SRC_JSON", AGG_DIR / "merged-config.json"))
DB = Path(os.environ.get("AGG_DB", AGG_DIR / "data" / "tvbox.db"))
OUT = Path(os.environ.get("OUT_JSON", Path(__file__).parent / "tvbox.json"))

# ── 直播源探活过滤（可选，用 PROBE_LIVE=1 开启）────────────
PROBE_LIVE = os.environ.get("PROBE_LIVE", "").strip() not in ("", "0", "false", "False")
PROBE_REPORT = Path(os.environ.get("PROBE_REPORT", str(Path(__file__).parent / "live_probe_report.json")))
PROBE_STATE = Path(os.environ.get("PROBE_STATE", str(Path(__file__).parent / "live_probe_state.json")))
PROBE_WHITELIST = Path(os.environ.get("PROBE_WHITELIST", str(Path(__file__).parent / "known_good.txt")))
PROBE_WORKERS = int(os.environ.get("PROBE_WORKERS", "16"))
PROBE_TIMEOUT = float(os.environ.get("PROBE_TIMEOUT", "6"))
PROBE_MAX_LINES = int(os.environ.get("PROBE_MAX_LINES", "6"))
PROBE_THRESHOLD = int(os.environ.get("PROBE_THRESHOLD", "3"))

# 聚合器把 JAR 收编为 "<base>/jar/<key>" 代理地址；key 为 16 位 urlToKey 或 32 位 md5。
# 静态化时按映射还原，host 部分不限（本机导出为局域网 IP，CI 里为 127.0.0.1）。
JAR_PROXY_PATTERN = re.compile(
    r"https?://(?:localhost|127\.0\.0\.1|[0-9]{1,3}(?:\.[0-9]{1,3}){3})(?::\d+)?/jar/([0-9a-f]{32}|[0-9a-f]{16})"
)


def load_jar_map() -> dict:
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT key, value FROM kv WHERE key LIKE 'jar:%'").fetchall()
    con.close()
    return {k.removeprefix("jar:"): v for k, v in rows}


def load_blacklist_patterns() -> list:
    bl = Path(__file__).parent / "blacklist.txt"
    if not bl.exists():
        print(f"WARN: blacklist file missing: {bl}", file=sys.stderr)
        return []
    pats = [re.compile(l, re.I) for l in bl.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]
    if not pats:
        print("WARN: blacklist is empty", file=sys.stderr)
    return pats


def main() -> int:
    raw = SRC.read_text(encoding="utf-8")
    jar_map = load_jar_map()
    if not jar_map:
        print("ERROR: jar mapping in SQLite is empty", file=sys.stderr)
        return 1

    replaced = 0
    unresolved = set()

    def sub(match: re.Match) -> str:
        nonlocal replaced
        key = match.group(1)
        origin = jar_map.get(key)
        if origin is None:
            unresolved.add(key)
            return match.group(0)
        replaced += 1
        return origin

    pattern = JAR_PROXY_PATTERN
    raw = pattern.sub(sub, raw)

    # 聚合后未再 refresh 时可能残留占位符形态
    raw = raw.replace("%7B%7BBASE_URL%7D%7D", "").replace("{BASE_URL}", "")

    cfg = json.loads(raw)
    pic = cfg.pop("pic", None)

    # 成人内容过滤（规则见 blacklist.txt，与 iMac 聚合器共用同一份）
    pats = load_blacklist_patterns()
    is_blocked = lambda t: any(p.search(t) for p in pats)
    sites_before = len(cfg.get("sites", []))
    lives_before = len(cfg.get("lives", []))
    blocked_sites = [s.get("name", "") for s in cfg.get("sites", []) if is_blocked(str(s.get("name", "")))]
    cfg["sites"] = [s for s in cfg.get("sites", []) if not is_blocked(str(s.get("name", "")))]
    cfg["lives"] = [g for g in cfg.get("lives", []) if not (isinstance(g, dict) and is_blocked(str(g.get("group", ""))))]

    # ── 直播分组名繁体→简体 ────────────────────────────────────
    # 上游部分源（如 Kimentanm，台湾）的分组名是繁体（「live」綜合/新聞/電影…）。
    # 电视端与 Windows 端的分组列表按名字展示/合并，混用繁体会显得杂乱。
    # 只覆盖实际出现的字符，零依赖（不引入 opencc）。
    TRAD_TO_SIMP = str.maketrans({
        "來": "来",
        "個": "个",
        "們": "们",
        "億": "亿",
        "將": "将",
        "對": "对",
        "導": "导",
        "廠": "厂",
        "廢": "废",
        "廣": "广",
        "廳": "厅",
        "應": "应",
        "會": "会",
        "權": "权",
        "歡": "欢",
        "沒": "没",
        "滅": "灭",
        "為": "为",
        "煙": "烟",
        "燈": "灯",
        "燒": "烧",
        "營": "营",
        "燦": "灿",
        "爐": "炉",
        "爛": "烂",
        "牽": "牵",
        "犧": "牺",
        "狀": "状",
        "獄": "狱",
        "獅": "狮",
        "獨": "独",
        "獻": "献",
        "現": "现",
        "環": "环",
        "產": "产",
        "畢": "毕",
        "當": "当",
        "疊": "叠",
        "癢": "痒",
        "發": "发",
        "眾": "众",
        "睜": "睁",
        "瞭": "了",
        "矚": "瞩",
        "磯": "矶",
        "礙": "碍",
        "禍": "祸",
        "禮": "礼",
        "稱": "称",
        "積": "积",
        "穩": "稳",
        "窮": "穷",
        "竊": "窃",
        "筆": "笔",
        "節": "节",
        "範": "范",
        "築": "筑",
        "簡": "简",
        "籃": "篮",
        "籌": "筹",
        "籤": "签",
        "籲": "吁",
        "粵": "粤",
        "糧": "粮",
        "系": "系",
        "紅": "红",
        "納": "纳",
        "純": "纯",
        "紙": "纸",
        "級": "级",
        "細": "细",
        "紹": "绍",
        "終": "终",
        "組": "组",
        "結": "结",
        "絕": "绝",
        "統": "统",
        "經": "经",
        "綠": "绿",
        "維": "维",
        "網": "网",
        "緊": "紧",
        "線": "线",
        "編": "编",
        "緩": "缓",
        "縣": "县",
        "縮": "缩",
        "總": "总",
        "繼": "继",
        "續": "续",
        "纖": "纤",
        "罰": "罚",
        "羅": "罗",
        "義": "义",
        "習": "习",
        "聖": "圣",
        "聞": "闻",
        "聯": "联",
        "聰": "聪",
        "職": "职",
        "聽": "听",
        "肅": "肃",
        "脅": "胁",
        "腦": "脑",
        "臉": "脸",
        "臺": "台",
        "與": "与",
        "興": "兴",
        "舉": "举",
        "舊": "旧",
        "艦": "舰",
        "萬": "万",
        "藝": "艺",
        "蘇": "苏",
        "蘭": "兰",
        "號": "号",
        "虧": "亏",
        "蝦": "虾",
        "蟲": "虫",
        "蟹": "蟹",
        "衆": "众",
        "補": "补",
        "裝": "装",
        "裡": "里",
        "製": "制",
        "複": "复",
        "見": "见",
        "規": "规",
        "視": "视",
        "親": "亲",
        "觀": "观",
        "計": "计",
        "訊": "讯",
        "記": "记",
        "設": "设",
        "許": "许",
        "訴": "诉",
        "診": "诊",
        "註": "注",
        "詞": "词",
        "試": "试",
        "詩": "诗",
        "話": "话",
        "該": "该",
        "詳": "详",
        "語": "语",
        "誠": "诚",
        "誤": "误",
        "說": "说",
        "誰": "谁",
        "調": "调",
        "談": "谈",
        "請": "请",
        "論": "论",
        "諸": "诸",
        "講": "讲",
        "謝": "谢",
        "識": "识",
        "議": "议",
        "護": "护",
        "讀": "读",
        "變": "变",
        "讓": "让",
        "讚": "赞",
        "豐": "丰",
        "貓": "猫",
        "買": "买",
        "賈": "贾",
        "賢": "贤",
        "賣": "卖",
        "賦": "赋",
        "質": "质",
        "賬": "账",
        "購": "购",
        "賽": "赛",
        "贏": "赢",
        "趕": "赶",
        "跡": "迹",
        "車": "车",
        "較": "较",
        "輔": "辅",
        "輝": "辉",
        "輪": "轮",
        "輸": "输",
        "轉": "转",
        "農": "农",
        "這": "这",
        "連": "连",
        "進": "进",
        "運": "运",
        "過": "过",
        "達": "达",
        "遞": "递",
        "遠": "远",
        "適": "适",
        "遲": "迟",
        "選": "选",
        "遺": "遗",
        "還": "还",
        "邊": "边",
        "郵": "邮",
        "鄉": "乡",
        "醫": "医",
        "鋼": "钢",
        "錄": "录",
        "錯": "错",
        "鍵": "键",
        "鎮": "镇",
        "鏡": "镜",
        "鐘": "钟",
        "鐵": "铁",
        "鑑": "鉴",
        "長": "长",
        "門": "门",
        "閃": "闪",
        "閉": "闭",
        "開": "开",
        "閒": "闲",
        "間": "间",
        "閱": "阅",
        "關": "关",
        "陰": "阴",
        "陳": "陈",
        "陸": "陆",
        "陽": "阳",
        "隊": "队",
        "階": "阶",
        "際": "际",
        "隨": "随",
        "險": "险",
        "隱": "隐",
        "隸": "隶",
        "雖": "虽",
        "雙": "双",
        "雜": "杂",
        "雞": "鸡",
        "離": "离",
        "難": "难",
        "雲": "云",
        "電": "电",
        "靈": "灵",
        "靜": "静",
        "韓": "韩",
        "響": "响",
        "頁": "页",
        "項": "项",
        "順": "顺",
        "須": "须",
        "預": "预",
        "領": "领",
        "頭": "头",
        "顆": "颗",
        "題": "题",
        "顏": "颜",
        "願": "愿",
        "類": "类",
        "顧": "顾",
        "顯": "显",
        "風": "风",
        "飛": "飞",
        "飯": "饭",
        "養": "养",
        "餘": "余",
        "館": "馆",
        "馬": "马",
        "驗": "验",
        "髒": "脏",
        "體": "体",
        "髮": "发",
        "鬥": "斗",
        "鬧": "闹",
        "魚": "鱼",
        "鮮": "鲜",
        "鯊": "鲨",
        "鯨": "鲸",
        "鰲": "鳌",
        "鱸": "鲈",
        "鳥": "鸟",
        "鳳": "凤",
        "鳴": "鸣",
        "鴨": "鸭",
        "鴻": "鸿",
        "鵝": "鹅",
        "鵬": "鹏",
        "鵰": "雕",
        "鶴": "鹤",
        "鷹": "鹰",
        "麗": "丽",
        "麥": "麦",
        "麵": "面",
        "麼": "么",
        "黃": "黄",
        "點": "点",
        "黨": "党",
        "齊": "齐",
        "齒": "齿",
        "龍": "龙",
        "龜": "龟",
    })

    def _simplify_group(g):
        if isinstance(g, dict) and isinstance(g.get("group", ""), str):
            fixed = g["group"].translate(TRAD_TO_SIMP)
            if fixed != g["group"]:
                g["group"] = fixed
        return g

    cfg["lives"] = [_simplify_group(g) for g in cfg["lives"]]

    # ── 直播源探活过滤 ──────────────────────────────────────
    # 只保留实测可用的频道；连续失败 N 次才丢弃（避免单次网络抖动误杀）。
    if PROBE_LIVE:
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from live_filter import filter_lives
            stats = filter_lives(
                cfg,
                workers=PROBE_WORKERS, timeout=PROBE_TIMEOUT,
                max_lines=PROBE_MAX_LINES, threshold=PROBE_THRESHOLD,
                state_path=str(PROBE_STATE),
                whitelist_path=str(PROBE_WHITELIST),
                report_path=str(PROBE_REPORT),
            )
            print(f"live probe: channels {stats['total']} alive {stats['alive']} "
                  f"pending {stats['kept_pending']} dropped {stats['dropped']} "
                  f"({stats['duration_s']}s)")
            for d in stats['dead'][:20]:
                print(f"  [dropped] {d['name'][:60]} (fail#{d['fails']})")
        except Exception as e:
            # 探活失败不能阻断导出 —— 宁可多几个死链，也不能没有产物
            print(f"WARN: live probe failed, skipped: {e}", file=sys.stderr)

    residual = [
        u for u in re.findall(r"https?://[^\"\\s]+", raw)
        if JAR_PROXY_PATTERN.search(u) or "localhost" in u
        or ("127.0.0.1" in u and "127.0.0.1:9978" not in u)
    ]

    OUT.write_text(json.dumps(cfg, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"sites={len(cfg.get('sites', []))} lives={len(cfg.get('lives', []))}")
    print(f"blacklist: sites {sites_before}->{len(cfg.get('sites', []))} (blocked {len(blocked_sites)})")
    for n in blocked_sites:
        print(f"  [blocked] {n[:70]}")
    print(f"blacklist: lives {lives_before}->{len(cfg.get('lives', []))}")
    print(f"jar rewritten={replaced} unresolved={sorted(unresolved) if unresolved else 'none'}")
    print(f"pic removed={pic!r}")
    print(f"residual local urls={residual if residual else 'none'}")
    print(f"written: {OUT} ({OUT.stat().st_size} bytes)")
    return 1 if unresolved or residual else 0


if __name__ == "__main__":
    sys.exit(main())
