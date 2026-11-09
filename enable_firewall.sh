#!/bin/bash
# 开启 macOS 应用防火墙，仅放行 TVBox 聚合器 (node@22 → :5678)
# 用法：sudo bash ~/tvbox/enable_firewall.sh
# 或在「系统设置 → 网络 → 防火墙」手动开启后，本脚本用于补齐放行规则。

FW=/usr/libexec/ApplicationFirewall/socketfilterfw
NODE_REAL=/opt/homebrew/Cellar/node@22/22.23.4/bin/node
NODE_LINK=/opt/homebrew/opt/node@22/bin/node

echo "=== BEFORE ==="
$FW --getglobalstate
$FW --getblockall
$FW --getstealthmode

echo
echo "=== 1) 放行 node@22（TVBox :5678） ==="
$FW --add "$NODE_REAL"    && echo "  added: $NODE_REAL"
$FW --add "$NODE_LINK"    && echo "  added: $NODE_LINK"

echo
echo "=== 2) 收紧过宽的旧放行规则（当前无进程在用） ==="
# 这三条允许「任何」该解释器进程监听入站端口，等于把整个语言运行时暴露在内网
for app in /usr/bin/python3 /usr/bin/ruby; do
  if $FW --listapps | grep -q "^$app"; then
    $FW --remove "$app" && echo "  removed: $app"
  else
    echo "  skip (not present): $app"
  fi
done

echo
echo "=== 3) 开启防火墙 ==="
$FW --setglobalstate on
$FW --setblockall off

echo
echo "=== AFTER ==="
$FW --getglobalstate
echo "--- allowed apps ---"
$FW --listapps

echo
echo "=== VERIFY node permitted ==="
$FW --getappblocked "$NODE_REAL"
$FW --getappblocked "$NODE_LINK"

echo
echo "=== DONE ==="
