import subprocess
import platform
import time
import json
import smtplib
import threading
from email.message import EmailMessage
from datetime import datetime

EMAIL_LOG_FILE = "email_log.json"
LOG_FILE = "downtime.log"
failures = {}
os_type = platform.system().lower()
active_checks = set()  # Track which IPs are being handled in threads



def update_hosts_status(hosts):
    try:
        with open("hosts.json", "w") as f:
            json.dump({"hosts": hosts}, f, indent=4)
    except Exception as e:
        print("❌ Error updating hosts.json:", e)



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


def log_downtime(name, ip):
    now = datetime.now()
    log_entry = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {name} ({ip}) is DOWN (timestamp: {now.timestamp()})\n"
    with open(LOG_FILE, "a") as log:
        log.write(log_entry)
    print("📝 Logged downtime:", log_entry.strip())


def send_email(name, ip, config):
    msg = EmailMessage()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg['Subject'] = f"🚨🚨🚨Ping Alert: {name} is DOWN!"
    msg['From'] = config["sender"]
    msg['To'] = config["recipient"]
    msg.set_content(f"{name} ({ip}) was unreachable at {now}.\nPlease investigate immediately.")

    try:
        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["sender"], config["password"])
            server.send_message(msg)
        print("📧 Email sent to", config["recipient"])
    except Exception as e:
        print("❌ Failed to send email:", e)


# def send_alert(label, ip, email_config):
#     message = f"{label} ({ip}) is DOWN!"
#     print(f"🔔 ALERT: {message}")

#     # Native notification
#     if os_type == "darwin":
#         subprocess.run(['osascript', '-e', f'display notification "{message}" with title "Ping Alert"'])
#     elif os_type == "linux":
#         try:
#             subprocess.run(['notify-send', "Ping Alert", message])
#         except FileNotFoundError:
#             print("⚠️ 'notify-send' not found.")
#     elif os_type == "windows":
#         print("🟡 Windows notification not implemented.")

#     log_downtime(label, ip)
#     send_email(label, ip, email_config)


def send_alert(label, ip, email_config):
    global last_email_sent

    now_ts = time.time()
    last_sent = float(last_email_sent.get(ip, 0))
    time_since_last = now_ts - last_sent

    if time_since_last < EMAIL_INTERVAL:
        print(f"⏱️ Skipping email for {label} ({ip}) — last sent {int(time_since_last)}s ago")
        return

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

    # Update email log
    last_email_sent[ip] = now_ts
    save_email_log(last_email_sent)



def print_status(label, ip, is_up, fail_count):
    status_icon = "✅" if is_up else "🚨🚨🚨"
    print(f"{status_icon} {label} ({ip}) - {'UP' if is_up else f'DOWN (Failure #{fail_count})'}")


def retry_and_alert(ip, label, max_failures, interval_check, email_config):
    global failures, active_checks

    print(f"🧵 [Thread] Starting retry checks for {label} ({ip})")
    for i in range(max_failures):
        time.sleep(interval_check)
        if is_host_up(ip):
            print(f"✅ [Thread] {label} recovered on retry attempt {i+1}")
            failures[ip] = 0
            active_checks.discard(ip)
            return
        else:
            print(f"❌ [Thread] {label} still down (retry {i+1}/{max_failures})")

    print(f"🚨 [Thread] {label} confirmed DOWN after {max_failures} retries")
    send_alert(label, ip, email_config)
    failures[ip] = 0
    active_checks.discard(ip)



def load_email_log():
    try:
        with open(EMAIL_LOG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_email_log(data):
    with open(EMAIL_LOG_FILE, "w") as f:
        json.dump(data, f)

last_email_sent = load_email_log()

# 🔁 Main loop with live reload
while True:
    hosts = load_hosts()
    email_config, app_config = load_config()
    INTERVAL = app_config.get("interval", 60)
    MAX_FAILURES = app_config.get("max_failures", 1)
    INTERVAL_FAILURES_CHECK = app_config.get("interval_failures_check", 3)
    EMAIL_INTERVAL = app_config.get("email_interval", 3)

    for host in hosts:
        ip = host["ip"]
        label = host.get("label", ip)

        if ip not in failures:
            failures[ip] = 0

        if is_host_up(ip):
            failures[ip] = 0
            print_status(label, ip, True, 0)
            host["statusCurrent"] = 1
            active_checks.discard(ip)
        else:
            print_status(label, ip, False, failures[ip])
            host["statusCurrent"] = 0


            # If not already being handled in a thread, start the confirmation check
            if ip not in active_checks:
                active_checks.add(ip)
                thread = threading.Thread(
                    target=retry_and_alert,
                    args=(ip, label, MAX_FAILURES, INTERVAL_FAILURES_CHECK, email_config)
                )
                thread.daemon = True
                thread.start()
    update_hosts_status(hosts)

    print("-" * 50)
    time.sleep(INTERVAL)
