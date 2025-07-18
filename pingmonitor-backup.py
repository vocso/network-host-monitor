import subprocess
import platform
import time
import json
import smtplib
from email.message import EmailMessage
from datetime import datetime

LOG_FILE = "downtime.log"
failures = {}
os_type = platform.system().lower()


def load_hosts():
    try:
        with open("hosts.json") as f:
            data = json.load(f)
            return data.get("hosts", [])
    except Exception as e:
        print("❌ Error loading hosts.json:", e)
        return []


def load_config():
    try:
        with open("config.json") as f:
            full_config = json.load(f)
            return full_config["email"], full_config["config"]
    except Exception as e:
        print("❌ Error loading config.json:", e)
        return {}, {"interval": 60, "max_failures": 1}


def is_host_up(ip):
    param = "-n" if os_type == "windows" else "-c"
    try:
        output = subprocess.check_output(["ping", param, "1", ip], stderr=subprocess.STDOUT)
        return "100% packet loss" not in output.decode().lower()
    except subprocess.CalledProcessError:
        return False


def log_downtime(label, ip):
    now = datetime.now()
    log_entry = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {label} ({ip}) is DOWN (timestamp: {now.timestamp()})\n"
    with open(LOG_FILE, "a") as log:
        log.write(log_entry)
    print("📝 Logged downtime:", log_entry.strip())


def send_email(label, ip, config):
    msg = EmailMessage()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg['Subject'] = f"🚨🚨🚨Ping Alert: {label} is DOWN!"
    msg['From'] = config["sender"]
    msg['To'] = config["recipient"]
    msg.set_content(f"{label} ({ip}) was unreachable at {now}.\nPlease investigate immediately.")

    try:
        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["sender"], config["password"])
            server.send_message(msg)
        print("📧 Email sent to", config["recipient"])
    except Exception as e:
        print("❌ Failed to send email:", e)


def send_alert(label, ip, email_config):
    message = f"{label} ({ip}) is DOWN!"
    print(f"🔔 ALERT: {message}")

    # Native notification
    if os_type == "darwin":
        subprocess.run(['osascript', '-e', f'display notification "{message}" with title "Ping Alert"'])
    elif os_type == "linux":
        try:
            subprocess.run(['notify-send', "Ping Alert", message])
        except FileNotFoundError:
            print("⚠️ 'notify-send' not found.")
    elif os_type == "windows":
        print("🟡 Windows notification not implemented.")

    log_downtime(label, ip)
    send_email(label, ip, email_config)


def print_status(label, ip, is_up, fail_count):
    status_icon = "✅" if is_up else "🚨🚨🚨"
    print(f"{status_icon} {label} ({ip}) - {'UP' if is_up else f'DOWN (Failure #{fail_count})'}")


# 🔁 Main loop with live reload
while True:
    hosts = load_hosts()
    email_config, app_config = load_config()
    INTERVAL = app_config.get("interval", 60)
    MAX_FAILURES = app_config.get("max_failures", 1)

    for host in hosts:
        ip = host["ip"]
        label = host.get("label", ip)

        # Initialize failure counter for new IPs
        if ip not in failures:
            failures[ip] = 0

        if is_host_up(ip):
            failures[ip] = 0
            print_status(label, ip, True, 0)
        else:
            failures[ip] += 1
            print_status(label, ip, False, failures[ip])
            if failures[ip] == MAX_FAILURES:
                send_alert(label, ip, email_config)

    print("-" * 50)
    time.sleep(INTERVAL)
