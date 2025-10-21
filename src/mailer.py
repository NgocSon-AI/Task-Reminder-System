# mailer.py
import os
import smtplib
import socket
import traceback
import ssl
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

EMAIL_HOST = os.getenv('EMAIL_HOST')
if EMAIL_HOST:
	# strip accidental whitespace/newlines from .env
	EMAIL_HOST = EMAIL_HOST.strip()
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
# Nếu EMAIL_DRY_RUN=true (mặc định) sẽ không gửi thật mà chỉ in preview
EMAIL_DRY_RUN = os.getenv('EMAIL_DRY_RUN', 'true').lower() in ('1', 'true', 'yes')
# Bật debug để in SMTP protocol dialog và tracebacks
EMAIL_DEBUG = os.getenv('EMAIL_DEBUG', 'false').lower() in ('1', 'true', 'yes')
#print("EMAIL_DRY_RUN:", EMAIL_DRY_RUN)
if EMAIL_DEBUG:
	print("EMAIL_DEBUG: enabled (SMTP protocol will be printed)")

# Fail early with a helpful message when EMAIL_HOST is not configured and we're not in dry-run.
if not EMAIL_HOST:
	if EMAIL_DRY_RUN:
		print("WARNING: EMAIL_HOST is not set. Running in dry-run mode so no real email will be sent.")
	else:
		raise RuntimeError("EMAIL_HOST is not configured. Set EMAIL_HOST in your .env to your SMTP server host (e.g. smtp.example.com)")
def _build_email_message(to_email, task):
	subject = f"[Jira] Task {task['key']} sắp đến deadline!"
	body = f"""
Xin chào,

Task sau sắp đến deadline:
- Mã: {task['key']}
- Tiêu đề: {task['summary']}
- Deadline: {task['due_date']}
- Người phụ trách: {task['assignee']}

Vui lòng kiểm tra và nhắc nhở thành viên thực hiện đúng tiến độ.

Trân trọng,
Task Reminder System
"""
	# include project if available
	project = task.get('project')
	if project:
		# insert project line after title
		body = body.replace('\n - Deadline:', f"\n - Dự án: {project}\n - Deadline:")
	msg = MIMEText(body)
	msg['Subject'] = subject
	msg['From'] = EMAIL_USER
	msg['To'] = to_email
	return msg

def send_leader_warning_email(to_email, task):
	"""Gửi email cảnh báo leader về task sắp đến deadline.

	Nếu `EMAIL_DRY_RUN` bật thì sẽ in ra thay vì gửi để tránh gửi nhầm.
	"""
	msg = _build_email_message(to_email, task)
	if EMAIL_DRY_RUN:
		print('--- DRY RUN: Email preview ---')
		print('To:', to_email)
		print('Subject:', msg['Subject'])
		print(msg.get_payload())
		# dry-run -> signal caller that no real send happened
		return False

	# Use unified sender with retry/fallback
	try:
		_send_via_smtp(msg, to_email)
		return True
	except Exception as e:
		print('Failed to send email:', e)
		return False


def send_leader_summary_email(to_email, tasks):
	"""
	Gửi một email tóm tắt (một email) liệt kê nhiều task tới leader.
	tasks: list of dicts with keys key, summary, due_date, assignee
	"""
	subject = f"[Jira] Tóm tắt {len(tasks)} task sắp đến deadline"
	lines = [
		"Xin chào,",
		"",
		"Dưới đây là danh sách task sắp đến deadline:",
		"",
	]
	# Group tasks by project so we print project name once
	grouped = {}
	for t in tasks:
		proj = t.get('project') or 'Unknown Project'
		grouped.setdefault(proj, []).append(t)

	for proj, tlist in grouped.items():
		lines.append(f"Dự án: {proj}")
		for t in tlist:
			assignee = t.get('assignee') or 'Unassigned'
			lines.append(f"  - {t.get('key')}: {t.get('summary')} (due: {t.get('due_date')}) - {assignee}")
		lines.append("")
	lines.append("")
	lines.append("Vui lòng kiểm tra và nhắc nhở thành viên thực hiện đúng tiến độ.")
	lines.append("")
	lines.append("Trân trọng,\nTask Reminder System")

	body = "\n".join(lines)
	# indicate timezone
	body = "(Times shown in UTC+7)\n\n" + body
	msg = MIMEText(body)
	msg['Subject'] = subject
	msg['From'] = EMAIL_USER
	msg['To'] = to_email

	if EMAIL_DRY_RUN:
		print('--- DRY RUN: Summary Email preview ---')
		print('To:', to_email)
		print('Subject:', subject)
		print(body)
		# dry-run -> signal caller that no real send happened
		return False

	# Use unified sender with retry/ fallback
	try:
		_send_via_smtp(msg, to_email)
		return True
	except Exception as e:
		print('Failed to send summary email:', e)
		return False


def _send_via_smtp(msg, to_email):
	"""Try to send msg to to_email.

	Strategy:
	- If port is 465, try SMTP_SSL first.
	- Otherwise try SMTP with STARTTLS.
	- If first attempt fails, try the other method as fallback.
	"""
	def _tcp_check(host, port, timeout=5):
		"""Quick TCP connect check to surface network/connect errors early."""
		try:
			s = socket.create_connection((host, port), timeout)
			s.close()
			return True, None
		except Exception as e:
			return False, e

	def attempt_ssl():
		try:
			if EMAIL_DEBUG:
				print(f"[SMTP DEBUG] attempting SSL connect to {EMAIL_HOST}:{EMAIL_PORT}")
			# Use an SSL context and let SMTP_SSL handle the TLS handshake with proper server_hostname
			ctx = ssl.create_default_context()
			server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, timeout=10, context=ctx)
			server.set_debuglevel(1 if EMAIL_DEBUG else 0)
			server.ehlo()
			server.login(EMAIL_USER, EMAIL_PASS)
			server.sendmail(EMAIL_USER, [to_email], msg.as_string())
			try:
				server.quit()
			except Exception:
				# ensure socket is closed
				try:
					server.close()
				except Exception:
					pass
			return True, None
		except Exception as e:
			if EMAIL_DEBUG:
				print("[SMTP DEBUG] SSL attempt traceback:\n", traceback.format_exc())
			return False, e

	def attempt_starttls(port_override=None):
		try:
			port = port_override or EMAIL_PORT
			if EMAIL_DEBUG:
				print(f"[SMTP DEBUG] attempting STARTTLS connect to {EMAIL_HOST}:{port}")
			# Use an SSL context and pass it to starttls()
			ctx = ssl.create_default_context()
			server = smtplib.SMTP(EMAIL_HOST, port, timeout=10)
			server.set_debuglevel(1 if EMAIL_DEBUG else 0)
			server.ehlo()
			server.starttls(context=ctx)
			server.ehlo()
			server.login(EMAIL_USER, EMAIL_PASS)
			server.sendmail(EMAIL_USER, [to_email], msg.as_string())
			try:
				server.quit()
			except Exception:
				try:
					server.close()
				except Exception:
					pass
			return True, None
		except Exception as e:
			if EMAIL_DEBUG:
				print("[SMTP DEBUG] STARTTLS attempt traceback:\n", traceback.format_exc())
			return False, e

	# If dry run, already handled before calling this helper.
	# Quick TCP check to provide clearer network-level errors before attempting SMTP protocol flows.
	tcp_ok, tcp_err = _tcp_check(EMAIL_HOST, EMAIL_PORT)
	if not tcp_ok and EMAIL_DEBUG:
		print(f"[SMTP DEBUG] TCP connect to {EMAIL_HOST}:{EMAIL_PORT} failed: {tcp_err}")

	# Decide order
	first_try_ssl = EMAIL_PORT == 465
	if first_try_ssl:
		ok, err = attempt_ssl()
		if ok:
			return
		# fallback to STARTTLS on 587
		ok2, err2 = attempt_starttls(587)
		if ok2:
			return
		print('Failed to send email via SSL and STARTTLS. Errors:')
		print('SSL error:', repr(err))
		if EMAIL_DEBUG and err is not None:
			print(traceback.format_exc())
		print('STARTTLS error:', repr(err2))
		if EMAIL_DEBUG and err2 is not None:
			print(traceback.format_exc())
		raise err2 or err
	else:
		ok, err = attempt_starttls()
		if ok:
			return
		# fallback to SSL on 465
		ok2, err2 = attempt_ssl()
		if ok2:
			return
		print('Failed to send email via STARTTLS and SSL. Errors:')
		print('STARTTLS error:', repr(err))
		if EMAIL_DEBUG and err is not None:
			print(traceback.format_exc())
		print('SSL error:', repr(err2))
		if EMAIL_DEBUG and err2 is not None:
			print(traceback.format_exc())
		raise err2 or err
