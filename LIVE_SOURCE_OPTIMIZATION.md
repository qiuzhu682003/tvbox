# 直播源死链优化方法（交接给家里 agent / iMac / 电视端）

> 背景：用户在 Windows 上用定制版 QZTV（基于 xiugou-tv v1.0.5）看直播。
> 直播源从聚合配置/第三方 m3u 拉来后，**大量频道点不动**。
> 本文档给出可迁移到任何端的做法、判定标准、现成工具与已知坑。

---

## 0. 一句话结论

**直播源质量问题的根因是"一个频道名下堆了 5–8 条线路，其中大部分已死"**，
不是源本身不可用。做法是：**内容感知的探活 → 只保留实测可用的频道**。

---

## 1. 核心：内容感知的探活判活标准

这是整套方法里唯一必须精确实现的部分。**只判 HTTP 状态码会误判**。

### 判定规则（两条同时满足才算可用）

1. **HTTP 状态码 ∈ [200, 400)**
2. **响应内容不是错误页**：

| 内容形态 | 判定 | 说明 |
|---|---|---|
| 以 `#EXTM3U` / `#EXTINF` 开头 | ✅ 可用 | 明确的 HLS 清单 |
| 以 `<` 开头 | ❌ 不可用 | HTML / XML 错误页 |
| 短的可打印 ASCII 文本（< 80 字节） | ❌ 不可用 | 服务端错误消息，如 `sign error` |
| 读不到内容（流式首块延迟） | ✅ 放行 | 不武断否决，交给播放器 |
| 其余（二进制等） | ✅ 可用 | 媒体流 |

### 为什么必须判内容（实测证据）

某线路 `http://38.75.136.137:98/gslb/dsdqca/cctv1hd.m3u8?auth=test20251009`
返回 **HTTP 200 + `sign error`**（鉴权失败，且经常超时）。
只判状态码 → 被当成可用线 → 播放时报 `Failed to recognize file format`。
同频道另外 7 条线路实测全部返回真正的 `#EXTM3U`，完全可以播。

### 为什么不能用 `Range: bytes=0-1`（坑）

只拿到 **2 字节**，HLS 清单退化成 `#E`，被"短文本"规则误判成错误消息 →
真线路全被判死（实测 7 条真 HLS 全被判 `errmsg:#E`）。
**必须用 `Range: bytes=0-1023`**（或不发 Range），读到足够内容才能判。

### 第三条判据（2026-11-09 实测补充）：必须探真实分片

前两条判据能识别「错误页」，但识别不了「**索引是活的、分片已经死了**」的假流。
`probe_live.py` 只读索引，**读到 `#EXTM3U` 就判活**，因此会漏掉这一类。

**本机实测（`tvbox.db` 的 79 频道 / 101 线路）**：

| 阶段 | 结果 |
|---|---|
| `probe_live.py` 探活（只读索引） | 78/79 频道"可用"（98.7%） |
| 深检（解析索引 → 下载首个真实分片） | **42/78 真能拉分片**（53.8%） |
| 假阳性 | **36 条** |

36 条假阳性里 **34 条是「历年春晚」**——URL 形如
`https://alimov2.a.kwimgs.com/upic/2022/01/31/15/BMjAyMjAxMzExNTU5N...`，
返回的是 **MP4 文件**（首字节 `\x00\x00\x00 ftypisom` = ISO MP4 容器头），
**不是直播流**。`probe_live.py` 判成「binary → 可用」放行。

**这是点播文件不是直播**：播放器打开后会播完就停，不会持续更新。
直播源必须是**持续产生活动分片**的流。

**判 MP4 的方法**（读首 12 字节）：
```python
def is_mp4(head: bytes) -> bool:
    return len(head) >= 12 and head[4:8] == b'ftyp'
```
MP4 → 判死（对直播场景）。TS → 首字节 0x47（188 字节对齐）→ 判活。

> 聚合器的 `channel-probe.ts` **已经做了这件事**（探真实分片 + 判 TS sync byte），
> 所以它比 `probe_live.py` 严格。工具选型时优先用聚合器那套。

### 为什么 UA 要和播放器一致

用 `okhttp/3.12.0`（mpv/TVBox 生态常见 UA）。用 Chrome UA 可能被服务器额外
拦截/放行，判活结果与实际播放不一致。

---

## 2. 现成工具（直接可用）

`probe_live.py` —— 纯 Python 3.8+ 标准库，无第三方依赖，跨平台（Windows/macOS/Linux 均可）。

```bash
# 远程源 -> 干净 m3u
python3 probe_live.py --url 'https://example.com/live.m3u' \
    --epg 'https://example.com/e.xml' \
    -o clean.m3u --report report.json

# 本地文件
python3 probe_live.py --file live_lite.m3u -o clean.m3u

# 只保留指定分组
python3 probe_live.py --url U --groups '央视频道,卫视频道' -o clean.m3u
```

参数：`--workers`（并发，默认 24）、`--timeout`（单条秒，默认 4.5）、
`--max-lines`（每频道最多探测几条，默认 8）、`--report`（JSON 报告，含死因分布）。

**实测参考**：ccsh_lite（474 频道 / 3408 条线路）→ 探活 67–107 秒 → 233–236 个可用（≈50%）。

---

## 3. 三条落地路径（按推荐度）

### 路径 A（最优，服务端）：iMac 聚合器开 channel-probe

聚合器自带频道探测能力，**每 12 小时自动跑**，只输出验证过的频道。
电视端和客户端都直接受益，不用每次手工筛。

- 现状：channel-probe **仅 Node / Docker 入口有**（纯 CF Worker 没有）
- 启用方式：iMac 上聚合器的管理接口
  - `GET  /admin/channel-probe/status`  → `{enabled, running, status}`
  - `PUT  /admin/channel-probe/toggle`  body `{"enabled": true}`
  - `POST /admin/channel-probe/trigger` （异步；运行中返回 409，未启用 400）
- 聚合器地址：**`http://192.168.3.248:5678`**（家里那台 iMac，主机名 `huxiweideiMac.local`）
  - ⚠️ 旧文档写的 `192.168.3.62:5678` **是错的**，那台机器不在当前局域网
- **判活标准已对齐（2026-11-09 核实）**：`aggregator/src/core/channel-probe.ts` 的
  `probeSingle()` 比 `probe_live.py` **更严格**，已实现：
  | 判据 | probe_live.py | 聚合器 channel-probe |
  |---|---|---|
  | HTTP 状态码 | ✅ | ✅ |
  | 判 `#EXTM3U`（拦 `sign error`） | ✅ | ✅ |
  | 判 TS sync byte 0x47 | ❌ | ✅ |
  | **探真实分片**（索引活但分片死 = 判死） | ❌ | ✅ |
  | 分片吞吐 ≥16KB 才算真流 | ❌ | ✅ |
  | 判 HTML 错误页 `<` | ✅ | ❌ **缺这条** |

  → `sign error` 假阳性在聚合器里**不会复现**（它要求索引含 `#EXTM3U`）。
  → 真正缺的是**非 .m3u8 后缀的 URL 返回 HTML 错误页**时仍被判 `tcp` 存活。
  → 但注意：聚合器的 `channel_speed_map` 判的是**测速**不是**死活**，
    `channel_probe_status` 记录的是「speedMs」而非「alive/fail」，两者语义不同。

### 路径 B（次优，产物层）：静态导出时过滤 ✅ 已实现

GitHub 静态聚合链路（`qiuzhu682003/tvbox`）每日 CI 跑一次并推送 `tvbox.json`，
电视端填的就是这个地址。在**导出步骤**加一道探活过滤，产物就是干净的。

- 位置：`export_static.py`（**在 repo 根**，CI 里被调用；旧文档写的 `tvbox-static/` 子目录不存在）
- 现状：它已经做了三件事——还原 jar 代理 URL、删 pic 字段、按 `blacklist.txt` 过滤
- ⚠️ **跨平台坑**：`export_static.py` 的默认路径写死了 Windows
  （`AGG_DIR = r"C:\Users\qiuzhu\ZCodeProject\tvbox-source-aggregator"`）。
  在 macOS 上必须显式传环境变量，否则直接读错路径：
  ```bash
  AGG_DIR=~/tvbox/aggregator \
  SRC_JSON=~/tvbox/aggregator/merged-config.json \
  AGG_DB=~/tvbox/aggregator/data/tvbox.db \
  OUT_JSON=~/tvbox/tvbox.json \
  python3 export_static.py
  ```

#### ✅ 已实现（2026-11-09）：探活过滤器 `live_filter.py`

新增独立模块 `~/tvbox/live_filter.py`，可被 `export_static.py` import，也可独立跑：

```bash
# 独立用法：对某份 TVBox 配置做探活过滤
python3 ~/tvbox/live_filter.py \
  --config ~/tvbox/tvbox.json \
  --out ~/tvbox/live-candidates/filtered.json \
  --report ~/tvbox/live-candidates/probe_report.json \
  --state ~/tvbox/live-candidates/probe_state.json \
  --whitelist ~/tvbox/known_good.txt \
  --workers 16 --timeout 6 --max-lines 6 --threshold 3
```

**判活标准**（与 §1 一致，内容感知 + 探真实分片）：
- HTTP 2xx + 内容含 `#EXTM3U` → HLS，继续探第一个真实分片
- 分片 ≤1KB → 判死（假流/索引活分片死）
- MP4（`ftyp`）、HTML（`<`）、`sign error` 等短文本 → 判死
- TS 流（0x47 同步字节）→ 放行

**分级过滤（避免误杀）**：连续失败 ≥ `--threshold`（默认 3）轮才丢弃该频道；
单次网络抖动只记一次，不立即丢。探活成功即清零计数。
白名单 `known_good.txt` 里的频道名**永不丢弃**（应对 CI 海外 vs 家庭内网差异）。

**`export_static.py` 接入**（已加）：环境变量开启，CI 里已开：

```yaml
PROBE_LIVE: "1"                    # 开关
PROBE_WORKERS: "24"                # 并发
PROBE_TIMEOUT: "6"                 # 单条超时
PROBE_MAX_LINES: "4"               # 每频道最多探几条线路
PROBE_THRESHOLD: "3"               # 连续失败几次丢弃
PROBE_REPORT: path/probe_report.json
PROBE_STATE:  path/probe_state.json    # 失败计数持久化
PROBE_WHITELIST: path/known_good.txt
```

探活失败时输出 `WARN: live probe failed, skipped`，**不阻断导出**——
宁可多几个死链，也不能没有产物。

**实测结果（79 频道 / 4 轮，2026-11-09）**：

| 轮次 | 探活通过 | 待定（失败 <3 次） | 丢弃 | state 最大计数 |
|---|---|---|---|---|
| 1 | 44 | 35 | 0 | 1 |
| 2 | 45 | 34 | 0 | 2 |
| **3** | 45 | **0** | **34** | 3 ← 达阈值，剔除 |
| 4 | 44 | 1 | 0 | 3 |

最终 44/79（55.7%）真活，与 §7 手工深检 42 条基本吻合（差 2 条是否时序波动）。

**CI 产物**：`live_probe_report.json` + `live_probe_state.json` 随 `tvbox.json` 一起提交，
本地可复核（CI 海外网络与家庭网络不同，报告里的死链不一定是家里也死）。

### 路径 C（兜底，本地）：一次性筛出快照源

改动最小、不碰在跑的链路：拉源 → 探活 → 生成干净 m3u → 手动导入。

- 本机已完成一次，结果见 `live-candidates/CCTV精选.m3u`（236 频道）
- Windows 端安装方式：改 `AppData\Roaming\QZTV\live_sources.json`，
  源条目形如 `{"id":"curated/ccsh","name":"CCTV精选","location":null,"epg":"...","channels":[...]}`
  —— **`location: null` 表示快照源不参与自动刷新**（1.0.5 的刷新逻辑会跳过 null location），
  但已落盘的 channels 立即可用
- iMac / 电视端等效做法：把干净 m3u 放到一个能访问的 URL，在 TVBox 里添加为直播源

---

## 4. 必须知道的坑

1. **iptv4 没有 CCTV1/2/4/7**。它只有 CCTV3/5/5+/8/12/13/15/16/17 + 剧场类（19 个央视频道）。
   CCTV1 的可用线路全靠 ccsh_lite。**所以不能直接删 ccsh_lite**，要先提取可用子集。
2. **运营商 IPTV 整族不可用**：`cmvideo.cn`（咪咕）、`chinamobile`、`itv.cn`
   ——在中国民用宽带上要么 403（鉴权拒绝，加任何请求头都无效）、
   要么 TCP 超时（IP 路由不通）。这类频道**换线路也救不了**，只能过滤掉或换源。
3. **写死的过期鉴权参数**：部分 URL 带 `?auth=test20251009` 这类硬编码 token，
   源作者更新清单时不同步 → 必然失效。表现为 200 + `sign error`。
4. **同名不同源要合并**：不同 m3u 里常有同名频道（iptv4 的 CCTV1 vs 虎牙的 CCTV1），
   合并成一条多线路频道后才有"换线"的意义。
   合并时**播放身份必须兼容**（请求头 / api / ext / 脚本身份 / 播放模式）；
   **EPG、时区等展示配置差异可以忽略**（以先出现者为准）。
5. **同源内合并与跨源合并是两回事**：上游原生只做同源合并（分组 key 含 source），
   跨源要额外做一层二级聚合，否则跨源换线用不上。
6. **直播没有自动换线**（上游 1.0.5）：上游的 SET-12 自动换线只作用于**点播**
   （`_startEpisodePlayback` 的候选链）。直播起播失败只弹提示，断流走退避重连。
   要给直播做自动换线得自己实现。
7. **起播失败 ≠ 断流**：起播失败（打不开）适合换线；播着断了是网络抖动，适合重连。
   两者要分开处理。
8. **探活有成本**：474 频道需 67–107 秒、约 3400 次请求。放进每次起播的同步路径
   会拖慢体验——正确做法是**后台预热/定期刷新**，把结果缓存起来用。

---

## 5. 验收标准

- 频道列表里每个台点得开（人工抽查 10–20 个，含央视频道、卫视频道各若干）
- 死链比例 < 5%
- 起播等待时间可接受（若用了起播前探活，通常 +1–3 秒）
- 探活误判率：随机抽 10 个被判"死"的频道人工复核，确认确实打不开
- 反向抽 10 个被判"活"的，确认确实能播（防止 `sign error` 类假阳性）

---

## 6. 参考数据（本机 2026-11-05 实测）

| 源 | 频道/线路 | 可用 | 说明 |
|---|---|---|---|
| iptv4（vbskycn） | 431 | 96% 主机可达 | 台标+EPG 最好；**无 CCTV1/2/4/7** |
| 虎牙一起看（sub.ottiptv.cc） | 1070 | 100% 连通 | 服务端保活，今晨仍在更新；含赛事/轮播/4K |
| ccsh_lite（CCSH） | 474 频道 / 3408 线路 | 50% 频道可用 | 央视频道 38、卫视 42、电影 52、港澳台 42 可用；其余为死链 |

死因分布（按线路，ccsh_lite）：URLError 378 / RemoteDisconnected 116 /
HTTP 404 64 / **HTTP 403 49** / ConnectionReset 23 / HTML 15 / **errmsg 9** /
HTTP 406 8 / Timeout 8。

---

## 7. 本机聚合器实测（2026-11-09，iMac `huxiweideiMac.local`）

对 `tvbox.db` 的 `channel_merged_tree`（6 组 / 79 频道 / 101 线路）实跑：

| 阶段 | 可用 | 比例 |
|---|---|---|
| `probe_live.py`（只读索引） | 78/79 频道 | 98.7% |
| 深检（探真实分片） | 42/78 | 53.8% |
| 假阳性 | 36 | 其中 34 是 MP4 点播文件 |

**活线路按 host 分布**（真实可播的 42 条）：
- `113.57.140.161:10081` / `120.198.95.220:9901` / `36.136.38.87:9901` 等 txiptv 系 — 16 条
- `alimov2.a.kwimgs.com` — 34 条（**全是 MP4 假阳性**）
- `english-livebkali.cgtn.com` — 2 条（CGTN，真活）
- `ali-m-l.cztv.com` / `event.pull.hebtv.com` / `8.138.7.223` / `59.39.89.130:60901` — 各 1 条

**结论**：聚合器里的源质量两极分化——
txiptv 系（带 `?key=txiptv`）和 CGTN/浙江/河北等地方台是真活的；
阿里 CDN 的「春晚」系列是 **MP4 点播文件冒充直播**，必须过滤。

> ⚠️ **`txiptv` 系源有运营商地域限制**，跨网/换宽带可能失效。
> 本机能播不代表电视端能播——电视端必须自己复测一遍。

### 交叉验证：聚合器自己测的结果

`channel_probe_status` 记录：`totalUrls: 2763, success: 98, failed: 2665`（3.5%）。
这个数字远低于本机深检的 53.8%，原因是：
- 聚合器测的是**全部 2763 条 URL**（含大量未合并的重复线路和历史死链）
- 本机测的是**合并去重后的 101 条**（`channel_merged_tree`）
- 聚合器的 `success` 判的是**测速成功**（拿到 speedMs），不是"能播"

**两个数字都不算错，但都不能直接当"可用率"用**——口径不同。
