#!/usr/bin/env python3
"""
Run the task reminder daily at 15:30 Asia/Ho_Chi_Minh.
This script imports the project's main function and schedules it.
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import os
from dotenv import load_dotenv

load_dotenv()

# ensure venv python path includes repo src
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from main import main

sched = BlockingScheduler(timezone='Asia/Ho_Chi_Minh')
# Run daily at 15:30
trigger = CronTrigger(hour=15, minute=30)

@sched.scheduled_job(trigger)
def run_job():
    print('Running scheduled Jira reminder...')
    try:
        main(days=1, past_days=1)  # +-1 day window
    except Exception as e:
        print('Scheduled job failed:', e)

if __name__ == '__main__':
    print('Starting scheduler (Asia/Ho_Chi_Minh) - will run daily at 15:30')
    sched.start()
