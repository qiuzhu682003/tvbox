# tvbox — 自聚合 TVBox 点播配置

多源聚合的 TVBox 点播配置，**每天北京时间 05:00 由 GitHub Actions 自动重新聚合并推送**。

## 电视端配置地址

TVBox 壳子「配置地址」处填：

```
https://gh-proxy.com/raw.githubusercontent.com/qiuzhu682003/tvbox/main/tvbox.json
```

（`gh-proxy.com` 为 GitHub raw 加速；若失效可换 `ghfast.top` 同路径。）

## 内容与来源

| 上游源 | 说明 |
|---|---|
| `https://tv.cc0cd.cc.cd` | tvyuan，1448 站自动测速排序，每小时更新 |
| `http://肥猫.net/` | 40 精选站 + jar + 直播 |
| `qist/tvbox fty.json` | 49 站（饭太硬镜像，走 gh-proxy） |
| `qist/tvbox jsm.json` | 153 站（OK影视适用，走 gh-proxy） |

聚合（去重 / 测速标注 / Spider JAR 收编）由 [tvbox-source-aggregator](https://gitee.com/tengxiaobao/tvbox-source-aggregator) v2.1.1 完成，源码 vendor 在 `aggregator/`。

## 静态化处理（export_static.py）

聚合器输出里所有 Spider JAR 被改写为 `<BASE_URL>/jar/<key>` 代理地址——静态托管没有这个代理，
本脚本按聚合器 SQLite 里的 `jar:<key>` 映射把它们**还原为原始 URL**（原始源均为国内可达：
gitee / gh-proxy / 源站自有域名），并删除图片代理 `pic` 字段。

## 本地手动刷新

```bash
# 1. 本地起聚合服务（在 tvbox-source-aggregator 目录）
npm run build:node && node dist/server.js
# 2. 用管理 API 加源后触发 POST /refresh（Bearer <ADMIN_TOKEN>）
# 3. 导出
curl -s http://127.0.0.1:5678/ -o ../tvbox-static/merged-config.json  # 放到聚合器目录
python export_static.py
git add tvbox.json && git commit -m refresh && git push
```

## 直播

直播源不依赖本配置，电视端单独填（已实测可用）：

- 点播+直播二合一：上方 tvbox.json（内含聚合的 1915 个直播分组）
- 纯直播推荐：`https://gh-proxy.com/raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u`（每 6h 更新）
- EPG：`https://gh-proxy.com/raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/e.xml`

### 直播源死链过滤（方法 + 工具）

聚合来的直播源里大量频道点不动——根因是「一个频道名下堆了 5–8 条线路，其中大部分已死」。

- **方法文档**：[LIVE_SOURCE_OPTIMIZATION.md](LIVE_SOURCE_OPTIMIZATION.md)
  含内容感知的判活标准、三条落地路径（聚合器 channel-probe / 静态导出过滤 / 本地快照源）、已知坑与验收标准。
- **工具**：[probe_live.py](probe_live.py)
  纯 Python3 标准库，无依赖。拉源→逐条探活→只输出实测可用的频道。

```bash
python3 probe_live.py --url 'https://.../live_lite.m3u'     --epg 'https://.../e.xml' -o clean.m3u --report report.json
```

实测：ccsh_lite（474 频道 / 3408 线路）→ 约 50% 频道可用，探活约 70–110 秒。

> 判活**不能只看 HTTP 状态码**：实测有线路返回 `HTTP 200 + sign error`（鉴权失败），
> 会被误判为可用线，播放时报 `Failed to recognize file format`。必须同时校验内容。
