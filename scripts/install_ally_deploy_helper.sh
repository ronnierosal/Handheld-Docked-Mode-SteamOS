#!/bin/sh
# One-time, interactive-root installation only.  Run on the Ally via sudo.
set -eu
umask 077
# SteamOS makes /usr immutable.  Use HDM's existing root-owned /var/lib state
# directory instead of putting a privileged executable in a mutable location.
install -d -m 0700 /var/lib/handheld-dock-mode
install -m 0755 /home/deck/Downloads/ally_hdm_deploy_helper.py /var/lib/handheld-dock-mode/hdm-deploy-plugin
install -m 0644 /home/deck/Downloads/hdm-deploy-public-key.pem /var/lib/handheld-dock-mode/deploy-public-key.pem
cat >/etc/sudoers.d/hdm-deploy-plugin <<'EOF'
# Developer-only HDM package installer.  The binary accepts only signed,
# fixed-name archives in /home/deck/Downloads and makes no session changes.
deck ALL=(root) NOPASSWD: /var/lib/handheld-dock-mode/hdm-deploy-plugin HDM-update-*.zip HDM-update-*.zip.sig
EOF
chmod 0440 /etc/sudoers.d/hdm-deploy-plugin
visudo -cf /etc/sudoers.d/hdm-deploy-plugin
echo '{"state":"installed","component":"hdm-deploy-helper"}'
