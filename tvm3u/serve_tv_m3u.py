#!/usr/bin/env python3
"""电视端直播清单服务（给 Kodi 用）。

在 iptv-api 生成的清单基础上做三件事，然后喂给电视：

1. 台标本地化：把 tvg-logo 指向本机的 /logo/<tvg-id>.png（iptv-api 的 logo 目录里
   已经有 CCTV-1.png 这类文件，nginx 已在 :8088/logo/ 提供）。电视从公网拉台标
   会很慢，且 imgur 那批在电视上是 TLS 握手失败（Kodi 日志里的 SSL error 35）。
2. 分组清理：把 iptv-api 的兜底分组「♻️未匹配频道」改成「🌍其它/国际」，
   并把本地精选源（local.txt 里以「台·」「华语·」等前缀的）单独拆成「📺台港海外」。
3. 线路去重：同一个 tvg-id 的多条线路默认只保留第一条（iptv-api 已按测速排序，
   第一条就是最快且可用的），可用 ?lines=all 保留全部并标注线路号。

另外按 XMLTV 的 channel id 对齐 tvg-id，让节目单能匹配上。

用法:
    python3 serve_tv_m3u.py            # 默认监听 8001
    curl http://127.0.0.1:8001/tv.m3u
    curl http://127.0.0.1:8001/tv.json  # 看统计
"""
import gzip
import io
import json
import os
import re
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

UPSTREAM_M3U = "http://192.168.3.248:8088/ipv4/m3u"
UPSTREAM_EPG = "http://192.168.3.248:8088/epg/epg.gz"
LOGO_BASE = "http://192.168.3.248:8088/logo/"
RADIO_M3U = os.path.join(os.path.dirname(os.path.abspath(__file__)), "radio_cnr.m3u")
PORT = 8001
CACHE_TTL = 300

# ── 探活快照（2026-11-09 新增）────────────────────────
# 由 ~/tvbox/build_tv_source.py 生成：虎牙 + iptv4 两源合并，
# 逐条内容感知探活（状态码 + 内容 + 真实分片）后剔除死链。
#
# 为什么不用 UPSTREAM_M3U：iptv-api 的 /ipv4/m3u 抽样实测真活率仅 10%
# —— 索引 206 但分片全 404（上游 CDN 改了目录结构）。
# 虎牙 93% / iptv4 70%，实测远好于 iptv-api。
CURATED_M3U = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tv_source.m3u")

GROUP_RENAME = {
    # 电视上 Kodi 用的字体没有 emoji 字形，📺 会显示成豆腐块 □，所以分组名一律去掉 emoji
    "🕘️更新时间": "更新时间",
    "📺央视频道": "央视频道",
    "📡卫视频道": "卫视频道",
    "☘️广东频道": "广东频道",
    "♻️未匹配频道": "其它/国际",
    # 探活快照里的虎牙分组（带 · 前缀）
    "虎牙·一起看": "虎牙一起看",
    "虎牙·原创": "虎牙原创",
    "虎牙·4K频道": "虎牙4K",
}
LOCAL_PREFIXES = ("台·", "华语·", "港·", "澳·")
ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')

_lock = threading.Lock()
_cache = {"m3u": None, "m3u_at": 0, "epg_ids": None, "epg_at": 0, "logo_ok": {}}


def http_get(url, timeout=25, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "ignore")


def get_epg_ids():
    """从 XMLTV 里取出所有 channel id，用于对齐 tvg-id。"""
    with _lock:
        if _cache["epg_ids"] and time.time() - _cache["epg_at"] < 3600:
            return _cache["epg_ids"]
    try:
        raw = http_get(UPSTREAM_EPG, timeout=40, binary=True)
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        text = raw.decode("utf-8", "ignore")
        ids = set(re.findall(r'<channel id="([^"]+)"', text))
    except Exception as e:
        print(f"[warn] EPG 拉取失败: {e}", flush=True)
        ids = set()
    with _lock:
        _cache["epg_ids"] = ids
        _cache["epg_at"] = time.time()
    return ids


def normalize_id(s):
    """
    tvg-id 规范化：CCTV8 -> CCTV-8，CCTV5+ -> CCTV-5+
    （本地 logo 文件名和 XMLTV channel id 都用带横线的形式）
    """
    if not s:
        return ""
    m = re.match(r"^(CGTN|CCTV|CETV)([0-9]+)(\+?)$", s.strip())
    if m:
        return f"{m.group(1)}-{m.group(2)}{m.group(3)}"
    return s.strip()


def logo_exists(tvg_id):
    """检查本机 /logo/ 里有没有这个台标（带缓存，避免每次刷都探一遍）。"""
    if not tvg_id:
        return False
    with _lock:
        hit = _cache["logo_ok"].get(tvg_id)
    if hit is not None:
        return hit
    ok = False
    try:
        url = LOGO_BASE + urllib.parse.quote(normalize_id(tvg_id)) + ".png"
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=8) as r:
            ok = r.status == 200 and int(r.headers.get("Content-Length", 0)) > 200
    except Exception:
        ok = False
    with _lock:
        _cache["logo_ok"][tvg_id] = ok
    return ok


def parse_m3u(text):
    """解析成 (attrs, name, url) 列表。"""
    out = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            attrs = dict(ATTR_RE.findall(line))
            name = line.split(",", 1)[1] if "," in line else ""
            url = ""
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and not lines[j].startswith("#"):
                url = lines[j].strip()
                i = j
            out.append((attrs, name.strip(), url))
        i += 1
    return out


def parse_radio_m3u():
    """读本地电台清单 radio_cnr.m3u（fanmingming/live，已带 radio=\"true\"、按省分组）。"""
    out = []
    try:
        text = open(RADIO_M3U, encoding="utf-8", errors="ignore").read()
    except OSError:
        return out
    for attrs, name, url in parse_m3u(text):
        if not url:
            continue
        attrs.setdefault("radio", "true")
        out.append((attrs, name, url))
    return out


def build(lines_mode="1", include_radio=True):
    base = None
    with _lock:
        if _cache["m3u"] and time.time() - _cache["m3u_at"] < CACHE_TTL:
            base = _cache["m3u"]
    if base is None:
        # 优先本地探活快照；没有或读失败则回落上游
        if os.path.exists(CURATED_M3U):
            try:
                with open(CURATED_M3U, encoding="utf-8", errors="ignore") as f:
                    base = f.read()
                print(f"[info] 使用探活快照 {CURATED_M3U} ({len(base)} B)", flush=True)
            except OSError as e:
                print(f"[warn] 快照读取失败，回落上游: {e}", flush=True)
                base = None
        if base is None:
            base = http_get(UPSTREAM_M3U, timeout=40)
        with _lock:
            _cache["m3u"] = base
            _cache["m3u_at"] = time.time()

    epg_ids = get_epg_ids()
    entries = parse_m3u(base)

    header = f'#EXTM3U x-tvg-url="{UPSTREAM_EPG}"\n'
    out = [header]
    stats = {
        "总条目": len(entries),
        "唯一 tvg-id": len({a.get("tvg-id", "") for a, _, _ in entries}),
        "台标本地化": 0,
        "台标保留外网": 0,
        "按节目单对齐 tvg-id": 0,
        "丢弃重复线路": 0,
        "分组": {},
    }
    seen = {}
    idx = 0
    for attrs, name, url in entries:
        if not url:
            continue
        group = attrs.get("group-title", "")
        # 过滤 iptv-api 的「更新时间」伪频道（把更新时间戳当频道名，电视上没法播）
        if "更新时间" in group:
            continue
        new_group = GROUP_RENAME.get(group, group)
        if group == "♻️未匹配频道" and name.startswith(LOCAL_PREFIXES):
            new_group = "台港海外"
        if new_group != group:
            attrs["group-title"] = new_group
        tvg_id = attrs.get("tvg-id", "")

        # 按 XMLTV 对齐 tvg-id，让节目单能匹配
        # （源里的 tvg-id 常是 CCTV8，XMLTV 用 CCTV-8；先规范化再比对）
        if tvg_id:
            norm = normalize_id(tvg_id)
            if norm != tvg_id and norm in epg_ids:
                attrs["tvg-id"] = norm
                stats["按节目单对齐 tvg-id"] += 1
                tvg_id = norm
            elif tvg_id not in epg_ids and name in epg_ids:
                attrs["tvg-id"] = name
                stats["按节目单对齐 tvg-id"] += 1
                tvg_id = name
            elif tvg_id not in epg_ids and normalize_id(name) in epg_ids:
                attrs["tvg-id"] = normalize_id(name)
                stats["按节目单对齐 tvg-id"] += 1
                tvg_id = attrs["tvg-id"]

        # 台标本地化
        if tvg_id and logo_exists(tvg_id):
            attrs["tvg-logo"] = LOGO_BASE + urllib.parse.quote(normalize_id(tvg_id)) + ".png"
            stats["台标本地化"] += 1
        elif attrs.get("tvg-logo"):
            stats["台标保留外网"] += 1

        # 线路去重
        key = attrs.get("tvg-id") or name
        line_no = seen.get(key, 0)
        seen[key] = line_no + 1
        if lines_mode == "1" and line_no > 0:
            stats["丢弃重复线路"] += 1
            continue
        label = name if line_no == 0 else f"{name} (线路{line_no + 1})"

        attr_str = "".join(f' {k}="{v}"' for k, v in attrs.items())
        out.append(f"#EXTINF:-1{attr_str},{label}")
        out.append(url)
        stats["分组"][new_group] = stats["分组"].get(new_group, 0) + 1
        idx += 1

    # ---- 电台（radio="true"，Kodi 的「电台」菜单从同一个 M3U 里按 radio 标志取）----
    radio_out = 0
    radio_seen_url = set()
    if include_radio:
        for attrs, name, url in parse_radio_m3u():
            if url in radio_seen_url:
                continue
            radio_seen_url.add(url)
            g = attrs.get("group-title", "")
            attr_str = "".join(f' {k}="{v}"' for k, v in attrs.items())
            out.append(f"#EXTINF:-1{attr_str},{name}")
            out.append(url)
            stats["分组"][f"[电台]{g}" if g else "[电台]"] = \
                stats["分组"].get(f"[电台]{g}" if g else "[电台]", 0) + 1
            radio_out += 1
    stats["电台条目"] = radio_out
    stats["输出条目"] = idx + radio_out
    return "\n".join(out) + "\n", stats


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path)
        q = parse_qs(p.query)
        mode = (q.get("lines", ["1"])[0] or "1").lower()
        if p.path in ("/tv.m3u", "/tv.m3u8", "/m3u"):
            body, stats = build(mode)
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            return
        if p.path == "/tv.json":
            _, stats = build(mode)
            data = json.dumps(stats, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.client_address[0], fmt % args), flush=True)


if __name__ == "__main__":
    import urllib.parse  # noqa: F401  (logo_exists 里用到)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
