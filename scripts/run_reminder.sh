#!/bin/bash

# ========================================
# 🟢 Script kiểm tra cron và chạy thử main.py
# ========================================

# Thông tin đường dẫn
PYTHON_BIN="/home/ngocson/WorkSpace/Task-Reminder-System/.venv/bin/python"
SCRIPT_PATH="/home/ngocson/WorkSpace/Task-Reminder-System/src/main.py"
LOG_FILE="/home/ngocson/WorkSpace/Task-Reminder-System/logs/jira_alert.log"

# 1️⃣ Kiểm tra cron entry
echo "🕵️‍♂️ Kiểm tra cron hiện tại..."
crontab -l | grep "$SCRIPT_PATH" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Cron đã có entry cho main.py"
else
    echo "⚠️ Cron chưa có entry. Bạn có thể thêm:"
    echo "15 16 * * * $PYTHON_BIN $SCRIPT_PATH >> $LOG_FILE 2>&1"
fi

# 2️⃣ Chạy thử script Python
echo "🏃 Chạy thử main.py ngay bây giờ..."
$PYTHON_BIN $SCRIPT_PATH
