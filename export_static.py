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
