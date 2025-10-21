# check_and_notify.py
"""
Script kiểm tra các task Jira sắp đến deadline và gửi email cảnh báo leader.
"""
import sys
import os
import argparse
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from jira_client import get_soon_due_tasks
from mailer import send_leader_warning_email, send_leader_summary_email


def main(days=1, past_days=0):
    tasks = get_soon_due_tasks(days=days, past_days=past_days)
    if not tasks:
        print("Không có task nào sắp đến deadline.")
        return
    # Group tasks by leader_email and send one summary email per leader
    grouped = {}
    for task in tasks:
        leader = task.get('leader_email')
        if not leader:
            print(f"Task {task['key']} không có leader_email, bỏ qua.")
            continue
        grouped.setdefault(leader, []).append(task)

    for leader_email, ts in grouped.items():
        sent = send_leader_summary_email(leader_email, ts)
        if sent:
            print(f"Đã gửi summary tới {leader_email} ({len(ts)} tasks)")
        else:
            print(f"Không gửi email tới {leader_email} (dry-run/failed).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check Jira due tasks and notify leaders')
    parser.add_argument('--days', type=int, default=1, help='lookahead days (default 1)')
    parser.add_argument('--past-days', type=int, default=0, help='include past N days (default 0)')
    args = parser.parse_args()
    main(days=args.days, past_days=args.past_days)
