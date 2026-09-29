#!/usr/bin/env bash
# ==============================================================================
# CampusIQ - Next-Generation University Automation Platform Launcher
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

export PORT="${PORT:-5000}"
export N8N_WEBHOOK_URL="${N8N_WEBHOOK_URL:-https://n8n-tanmay.onrender.com/webhook/campusiq-notices}"
export ACADEMIC_DIR="${ACADEMIC_DIR:-/home/tanmay/Workspaces/Academics/College}"

echo "================================================================================"
echo "🎓 Starting CampusIQ Platform (Frontend + Backend + Automation Hub)"
echo "================================================================================"
echo "📍 Project Root    : $DIR"
echo "🌐 Local URL       : http://localhost:$PORT"
echo "📡 Render Notice   : $N8N_WEBHOOK_URL"
echo "📚 Academic Vault  : $ACADEMIC_DIR"
echo "================================================================================"

exec python3 server.py
