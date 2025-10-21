# jira_client.py
import os
import json
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

JIRA_URL = os.getenv('JIRA_URL')
JIRA_USER = os.getenv('JIRA_USER')
JIRA_TOKEN = os.getenv('JIRA_TOKEN')
import zoneinfo


def get_soon_due_tasks(days=1, past_days=0):
	"""
	Lấy danh sách các task Jira có deadline trong khoảng từ (today - past_days)
	đến (today + days). Trả về list dict: [{key, summary, due_date, assignee, leader_email, project}, ...]
	Các tham số:
	- days: số ngày vào tương lai (mặc định 1)
	- past_days: số ngày trước hôm nay để bao gồm deadlines cũ (mặc định 0)
	"""
	# Tính khoảng ngày
	now = datetime.now(timezone.utc)
	start_date = (now - timedelta(days=past_days)).strftime("%Y-%m-%d")
	due_before = (now + timedelta(days=days)).strftime("%Y-%m-%d")

	# dùng ngày hôm nay ở UTC để làm ranh
	today = now.strftime("%Y-%m-%d")

	# JQL: lấy issue có duedate trong khoảng start_date..due_before và chưa Done
	jql = (
		f'status != Done '
		f'AND duedate >= "{start_date}" '
		f'AND duedate <= "{due_before}"'
	)

	url = f"{JIRA_URL}/rest/api/2/search"

	headers = {"Content-Type": "application/json"}

	auth = (JIRA_USER, JIRA_TOKEN)

	params = {
		"jql": jql,
		# include project so we can show project.name in emails
		"fields": "key,summary,duedate,assignee,status,project"
	}

	resp = requests.get(url, headers=headers, params=params, auth=auth)
	
	if resp.status_code == 403:
		try:
			body = resp.json()
			msg = body.get('message') or str(body)
		except Exception:
			msg = resp.text
		if 'Basic Authentication has been disabled' in msg or 'Basic authentication' in msg:
			print('Basic auth disabled on Jira instance — retrying with Bearer token')
			head = headers.copy()
			head['Authorization'] = f'Bearer {JIRA_TOKEN}'
			resp = requests.get(url, headers=head, params=params)

	resp.raise_for_status()

	issues = resp.json().get('issues', [])

	JIRA_LEADER = os.getenv('JIRA_LEADER') or os.getenv('JIRA_USER')
	tasks = []
	for issue in issues:
		fields = issue['fields']
		# Giả sử leader là assignee (có thể sửa lại nếu có custom field leader)
		assignee = fields['assignee']
		leader_email = JIRA_LEADER if JIRA_LEADER else (assignee['emailAddress'] if assignee else None)
		# Project name (human friendly) if available
		project = None
		if 'project' in fields and fields['project']:
			project = fields['project'].get('name') or fields['project'].get('key')
		# Normalize due_date into UTC+7 display (Jira duedate is date-only YYYY-MM-DD)
		due_raw = fields.get('duedate')
		due_display = None
		if due_raw:
			try:
				# parse date-only string, assume midnight UTC then convert to UTC+7
				dt = datetime.strptime(due_raw, "%Y-%m-%d")
				dt = dt.replace(tzinfo=timezone.utc)
				local_tz = timezone(timedelta(hours=7))
				dt_local = dt.astimezone(local_tz)
				# show date and time in local timezone and label timezone as UTC+7
				due_display = dt_local.strftime("%Y-%m-%d %H:%M") + " UTC+7"
			except Exception:
				due_display = due_raw
		else:
			due_display = None

		tasks.append({
			'key': issue['key'],
			'summary': fields.get('summary'),
			'due_date': due_display,
			'assignee': assignee['displayName'] if assignee else None,
			'leader_email': leader_email,
			'project': project,
		})
	return tasks
