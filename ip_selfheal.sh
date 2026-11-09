#!/bin/bash
# ─────────────────────────────────────────────────────────────
# TVBox 聚合器 IP 自愈脚本
#
# 背景：BASE_URL 写死了 iMac 内网 IP。若 IP 变化（Wi-Fi 私有地址
# 随机化 / 路由器重分配），JAR 代理地址会指向死 IP，电视点播全挂。
#
# 本脚本检测 en1 实际 IP 与 .env 中 BASE_URL 是否一致：
#   一致 → 什么都不做，退出 0
#   不一致 → 改写 .env 的 BASE_URL → 重启服务 → 触发一次 refresh
#
# 由 launchd 每 60 秒调用一次（见 cc.qiuzhu.tvbox.ipselfheal.plist）
# ─────────────────────────────────────────────────────────────

set -uo pipefail

AGG_DIR="/Users/qiuzhu/tvbox/aggregator"
ENV_FILE="$AGG_DIR/.env"
PORT="5678"
IFACE="en1"
LOG="/Users/qiuzhu/tvbox/ipselfheal.log"
TOKEN_FILE="/tmp/tvbox_admin_token.txt"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# ── 1. 取当前实际 IP ──────────────────────────────────────
CURRENT_IP=""
if [ -x /opt/homebrew/opt/node@22/bin/node ]; then
  CURRENT_IP=$(/opt/homebrew/opt/node@22/bin/node -e "
const os=require('os');
const nfs=os.networkInterfaces();
for (const n of Object.keys(nfs)) {
  for (const i of nfs[n]||[]) {
    if (i.family==='IPv4' && !i.internal) { console.log(i.address); process.exit(0); }
  }
}
" 2>/dev/null)
fi
[ -z "$CURRENT_IP" ] && CURRENT_IP="$(ipconfig getifaddr "$IFACE" 2>/dev/null)"

if [ -z "$CURRENT_IP" ]; then
  log "WARN: 取不到 IP（可能网络断开），跳过"
  exit 0
fi

# ── 2. 取 .env 里记录的 IP ────────────────────────────────
ENV_IP="$(grep -E '^BASE_URL=' "$ENV_FILE" 2>/dev/null | head -1 | sed -E 's#.*://([^:/]+).*#\1#')"

if [ "$CURRENT_IP" = "$ENV_IP" ]; then
  # 状态正常，不写日志避免刷屏
  exit 0
fi

log "检测到 IP 变化: $ENV_IP -> ${CURRENT_IP}，开始自愈"

# ── 3. 改写 .env 的 BASE_URL ─────────────────────────────
if [ -z "$ENV_IP" ]; then
  log "ERROR: .env 中解析不到 BASE_URL_IP，人工介入"
  exit 1
fi

cp "$ENV_FILE" "$ENV_FILE.bak.$(date +%Y%m%d%H%M%S)"
/usr/bin/sed -i '' -E "s#^BASE_URL=.*#BASE_URL=http://${CURRENT_IP}:${PORT}#" "$ENV_FILE"

NEW_IP="$(grep -E '^BASE_URL=' "$ENV_FILE" | sed -E 's#.*://([^:/]+).*#\1#')"
if [ "$NEW_IP" != "$CURRENT_IP" ]; then
  log "ERROR: .env 改写失败（仍为 ${NEW_IP}）"
  exit 1
fi
log ".env 已更新为 BASE_URL=http://${CURRENT_IP}:${PORT}"
# ── 4. 重启服务（让它读到新的 BASE_URL）──────────────────
UID_NUM="$(id -u)"
if launchctl kickstart -k "gui/${UID_NUM}/cc.qiuzhu.tvbox" 2>/dev/null; then
  log "服务已重启 (kickstart)"
else
  log "WARN: kickstart 失败，尝试 load"
  launchctl load "$HOME/Library/LaunchAgents/cc.qiuzhu.tvbox.plist" 2>/dev/null || true
fi

# ── 5. 等服务起来，再触发一次 refresh ───────────────────
for i in $(seq 1 20); do
  sleep 1
  if curl -s --max-time 3 "http://127.0.0.1:${PORT}/version" >/dev/null 2>&1; then
    log "服务已就绪（第 ${i}s）"
    break
  fi
done

TOKEN=""
[ -f "$TOKEN_FILE" ] && TOKEN="$(cat "$TOKEN_FILE")"
if [ -n "$TOKEN" ]; then
  RESP=$(curl -s --max-time 300 -X POST "http://127.0.0.1:${PORT}/refresh" \
         -H "Authorization: Bearer $TOKEN" 2>/dev/null)
  log "refresh 响应: ${RESP:-（无）}"
else
  log "WARN: 找不到 ADMIN_TOKEN，跳过 refresh（下次定时聚合会自动纠正）"
fi

log "自愈完成 ✅"
exit 0
