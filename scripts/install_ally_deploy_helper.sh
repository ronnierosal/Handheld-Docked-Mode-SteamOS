#!/bin/sh
# One-time, interactive-root installation only.  Run on the Ally via sudo.
set -eu
umask 077
# SteamOS images may not contain /usr/local/libexec yet.  Create the complete
# fixed path before setting permissions; BusyBox install does not reliably
# create absent parent directories with -d on every supported image.
mkdir -p /usr/local/libexec /etc/handheld-dock-mode
chmod 0755 /usr/local /usr/local/libexec /etc/handheld-dock-mode
install -m 0755 /home/deck/Downloads/ally_hdm_deploy_helper.py /usr/local/libexec/hdm-deploy-plugin
install -m 0644 /home/deck/Downloads/hdm-deploy-public-key.pem /etc/handheld-dock-mode/deploy-public-key.pem
cat >/etc/sudoers.d/hdm-deploy-plugin <<'EOF'
# Developer-only HDM package installer.  The binary accepts only signed,
# fixed-name archives in /home/deck/Downloads and makes no session changes.
deck ALL=(root) NOPASSWD: /usr/local/libexec/hdm-deploy-plugin HDM-update-*.zip HDM-update-*.zip.sig
EOF
chmod 0440 /etc/sudoers.d/hdm-deploy-plugin
visudo -cf /etc/sudoers.d/hdm-deploy-plugin
echo '{"state":"installed","component":"hdm-deploy-helper"}'
