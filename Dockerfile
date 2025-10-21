# Base image
FROM python:3.10-slim

# Đặt thư mục làm việc
WORKDIR /app

# Copy file dependency và cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code
COPY . .

# Cài cron
RUN apt-get update && apt-get install -y cron

# Copy file cron config vào container
COPY cronjob /etc/cron.d/jira_alert_cron

# Set quyền thực thi cho cron file
RUN chmod 0644 /etc/cron.d/jira_alert_cron

# Apply cron job
RUN crontab /etc/cron.d/jira_alert_cron

# Khởi động cron và giữ container luôn chạy
CMD ["cron", "-f"]
