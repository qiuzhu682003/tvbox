# QZTV 源清单（点播 + 直播）

> 快照时间：2026-11-09 15:36 · 数据直接读自 `C:\Users\qiuzhu\AppData\Roaming\QZTV\`
> 应用版本：QZTV（基于 xiugou-tv v1.0.5 定制）

---

## 一、点播（配置源）

### 1.1 已配置的仓（2 个）

| 仓名 | 地址 | 状态 |
|---|---|---|
| **聚合·静态** | `https://gh-proxy.com/raw.githubusercontent.com/qiuzhu682003/tvbox/main/tvbox.json` | ✅ 当前生效 · 229 站点 · 3794 直播频道 · 最后使用 11-09 15:30 |
| **聚合·iMac** | `http://192.168.3.62:5678` | ⚪ 待命 · 需在家局域网 · 最后使用 11-06 23:35（当时不通） |

> 两个仓可在「设置 → 配置源管理」一键切换。「聚合·静态」每天 05:00 由 GitHub Actions 自动重新聚合。

### 1.2 当前加载内容（聚合·静态）

**站点：229 个**

| 站点类型 | 数量 | 含义 |
|---|---|---|
| type 3 | **218** | jar / JS 爬虫站（需 companion 的 JVM 运行时） |
| type 1 | 10 | 苹果 CMS JSON 直连 |
| type 0 | 1 | 苹果 CMS XML 直连 |

> **89% 是 type 3** —— 这就是当初选 xiugou-tv 而非其他桌面播放器的决定性原因（只有它内置 JVM 跑 jar）。

**站点样例**（前 12，可见命名规整度）
```
🐼┃QQ频道：肥猫宝贝┃      csp_Douban       🏜┃潮流┃APP「feimao」   csp_AppRJ
🐼┃豆瓣┃预告              csp_YGP          🐼┃肥猫┃APP「feimao」   csp_AppQi
🐼┃配置┃中心「feimao」     csp_Config       🍚┃干饭┃APP「feimao」   csp_AppDrama2
🐼┃网盘┃应用              csp_PanMarket    📀┃光盘┃APP「feimao」   csp_AppQi
🎮┃游戏┃直播              csp_Alllive      😌┃行动┃APP「feimao」   csp_AppDrama2
⚡┃闪电┃优汐「feimao」      csp_Duopan
🖍︎┃蜡笔┃影视「feimao」     csp_Duopan
```

**配置内直播：38 组 / 3794 频道**（`lives` 字段；QZTV 默认**不加载**这批，见 2.4）

```
「综合」央视频道 29    「Kimentanm」央视IPV4 28    「虎牙一起看」4K频道 2
「综合」卫视频道 17    「Kimentanm」卫视IPV4 36    「综合」咪视界 40
「综合」睛彩频道 4     「Kimentanm」4K8K频道 11    「综合」历年春晚 14
「综合」轮播 8        「Kimentanm」历年春晚 44
```

### 1.3 已知限制

- **需要扫码/登录的站用不了**：部分站（网盘类、夸克/UC 等）要求扫码授权，未登录时无法出片。用户验收时的"不能用的都是需要扫码的"即此。
- **jar 站首次加载慢**：10–30 秒（companion 在做 dex2jar 转换），之后秒开。

---

## 二、直播源

### 2.1 三个源合计 1664 频道

| # | 源名 | 频道 | 类型 | 刷新 | EPG |
|---|---|---|---|---|---|
| 1 | **聚合直播** | 430 | 远程 m3u（iptv4） | 源每 6h 更新，QZTV 启动时拉 | ✅ CCSH e.xml |
| 2 | **虎牙直播源** | 998 | 远程 m3u（ottiptv.cc） | 服务端保活，清单每日更新 | ❌ 无 |
| 3 | **CCTV精选** | 236 | **本地快照**（不刷新） | 手动重跑脚本 | ✅ CCSH e.xml |

### 2.2 源 1：聚合直播（iptv4）

```
location: https://gh-proxy.com/raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u
epg:      https://gh-proxy.com/raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/e.xml
```

**430 频道 / 12 组**

| 分组 | 频道 | 分组 | 频道 |
|---|---|---|---|
| 地方频道 | **232** | 央视频道 | 19 |
| 电影频道 | 80 | 儿童频道 | 9 |
| 卫视频道 | 29 | 音乐频道 | 4 |
| 纪录频道 | 28 | 体育频道 | 3 |
| 春晚频道 | 22 | 数字频道 | 2 |
| 解说频道 | 1 | 更新时间 | 1 |

**特点**：台标 + EPG 匹配最好；地方频道覆盖广（232 个）。
**⚠ 缺**：没有 CCTV1 / CCTV2 / CCTV4 / CCTV7（只有 CCTV3/5/5+/8/12/13/15/16/17 + 剧场类）。

### 2.3 源 2：虎牙直播源（ottiptv.cc）

```
location: https://sub.ottiptv.cc/huyayqk.m3u
```

**998 频道 / 4 组**

| 分组 | 频道 |
|---|---|
| 一起看 | **753** |
| 原创 | 242 |
| 4K频道 | 2 |
| 列表更新时间 | 1 |

**特点**：**服务端保活，主机连通率 100%**（与 IPTV 的衰减型源完全不同物种）。
**价值**：影视轮播厅、赛事转播、4K 测试片；CCTV5 锁死或没有的赛事这里常有。
**⚠ 注意**：是虎牙直播间转推，不是传统频道；台名是主播/房间名。

### 2.4 源 3：CCTV精选（快照源，本次新建）

```
location: null          ← 快照源，不参与自动刷新
epg:      https://gh-proxy.com/raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/e.xml
来源:     ccsh_lite 全量探活后提取的可用子集
```

**236 频道 / 9 组**

| 分组 | 频道 | 分组 | 频道 |
|---|---|---|---|
| 电影 | 51 | 央视频道 | **38** |
| 港澳台 | 46 | 电视剧 | 35 |
| 卫视频道 | 42 | 解说频道 | 11 |
| 体育频道 | 8 | NewTV | 4 |
| 综艺频道 | 1 | | |

**央视频道组（38 个，补齐了 iptv4 缺的台）**
```
CCTV1  CCTV2  CCTV3  CCTV4  CCTV5  CCTV5+  CCTV6  CCTV7  CCTV8  CCTV9
CCTV10 CCTV11 CCTV12 CCTV13 CCTV14 CCTV15 CCTV16 CCTV17
CCTV4K  CCTV8K  CETV1  CETV2  CETV4
风云剧场 兵器科技 第一剧场 央视台球 风云足球 高尔夫网球 世界地理
风云音乐 女性时尚 怀旧剧场 央视文化精品 卫生健康 电视指南 老故事 发现之旅
```

> **这是补上 CCTV1/2/4/7 的唯一来源** —— iptv4 没有这些台，删掉这个源会导致它们消失。

### 2.5 已移除：ccsh_lite（原 3408 条线路）

| | 原始 | 探活后 |
|---|---|---|
| 频道名 | 474 | 236（50%） |
| 线路 | 3408 | 236（每频道保留 1 条可用） |

**移除原因**：474 频道里一半是死链，列表臃肿；且含大量运营商 IPTV 地址（`cmvideo.cn` / `chinamobile`）在民用宽带上 403 或 TCP 超时，**整族不可用**。
**保留方式**：可用子集已提取为「CCTV精选」；原始数据备份在 `live_sources.json.bak-curated-20261109-103958`。

### 2.6 不加载：配置内直播（3794 频道）

聚合配置自带 38 组 / 3794 频道，QZTV **默认跳过**（`_includeConfiguredLives = false`）。

**原因**：实测这批主机可达率仅 36%，绝大多数是死链。想恢复改 `lib/core/live/live_repository.dart` 里的常量并重新构建。

---

## 三、QZTV 的直播可靠性机制（三层）

| 层 | 机制 | 说明 |
|---|---|---|
| **1. 源层** | 精选源替代原始源 | 3408 条死链混杂 → 236 个实测可用 |
| **2. 起播层** | 线路探活选线 | 起播前并发探测最多 6 条备线（状态码 + **内容**双重判定），直接选中可用线；代价约 +2.6s |
| **3. 失败层** | 自动换线 | 起播失败自动切下一条线路（最多 3 次），提示"已自动切换到线路 N" |

**跨源合并**：不同源的同名频道（如 iptv4 的 CCTV1 与 CCTV精选的 CCTV1）会合并为一条多线路频道，线路下拉可手动切换。

**已知无解**：运营商 IPTV 整族（`cmvideo.cn` 等）在民用宽带上死——403 加任何请求头都无效，只能过滤。

---

## 四、维护动作

| 场景 | 操作 |
|---|---|
| CCTV精选 累积死链 | 重跑 `H:\ZCodeProject\xiugou-tv\build_ccsh_curated.py`（约 110s）→ 再跑 `install_curated.py` |
| 换/加直播源 | 直播页 → 导入直播源 → 填 m3u 地址 |
| 想用通用探活工具 | `python3 probe_live.py --url <m3u> -o clean.m3u --report r.json`（已推到 tvbox 仓库） |
| 切换点播仓 | 设置 → 配置源管理 → 点目标仓 |
| 恢复配置内直播 | 改 `live_repository.dart` 的 `_includeConfiguredLives` 为 `true` → 重新构建 |
| 想恢复 ccsh_lite | 用 `live_sources.json.bak-curated-20261109-103958` 覆盖 |

---

## 五、数据文件位置

```
C:\Users\qiuzhu\AppData\Roaming\QZTV\
  config_sources.json      配置源列表（双仓）
  current_config.json      当前加载的完整配置（229 站点，含 rawContent）
  live_sources.json        直播源（3 个源 / 1664 频道 / 528KB）
  live_last.json           上次播放的频道
  history.json             播放历史
  player_settings.json     播放器设置
```

> 与官方修狗TV（`Roaming\XiugouTV`）完全隔离，两版可并存。
