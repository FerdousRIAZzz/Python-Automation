"""
=============================================================================
FILE:    system_monitor.py
PURPOSE: Monitors CPU, Memory, Disk, and Network in real-time using Python.
         Sends an alert (email or console) when thresholds are breached.

         In DevOps, monitoring is everything — you can't fix what you can't see.
         This script is a lightweight version of what tools like Datadog,
         Prometheus, or Nagios do under the hood.

LIBRARY: psutil — a cross-platform Python library for system stats.
         Install with: pip install psutil

AUTHOR:  Your Name
=============================================================================
"""

import psutil          # Reads CPU, RAM, Disk, Network stats from the OS
import time            # Used for sleep() — pausing between checks
import datetime        # Used to timestamp each reading
import smtplib         # Built-in Python library for sending emails
import json            # Used to save alert history as a JSON file
import os              # File path operations
from email.mime.text import MIMEText  # Helps format the email body

# =============================================================================
# CONFIGURATION — Change these values to match your environment
# =============================================================================
THRESHOLDS = {
    "cpu":    80,   # Alert if CPU usage goes above 80%
    "memory": 80,   # Alert if RAM usage goes above 80%
    "disk":   85,   # Alert if Disk usage goes above 85%
}

# How often (in seconds) to check system stats
CHECK_INTERVAL = 10

# Where to save the alert history log (JSON format)
ALERT_LOG_FILE = "alert_history.json"

# Email config (optional — only needed if you want email alerts)
EMAIL_CONFIG = {
    "enabled":   False,                  # Set to True to enable email alerts
    "sender":    "your@gmail.com",
    "recipient": "admin@yourcompany.com",
    "password":  os.environ.get("EMAIL_PASSWORD", ""),  # Read from env variable — NEVER hardcode passwords!
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
}


# =============================================================================
# FUNCTION: get_cpu_usage
# Returns the current CPU usage percentage.
# interval=1 means psutil measures CPU over 1 second for accuracy.
# A single instant snapshot can be misleading — averaging over 1s is better.
# =============================================================================
def get_cpu_usage():
    return psutil.cpu_percent(interval=1)


# =============================================================================
# FUNCTION: get_memory_usage
# Returns memory stats as a dictionary.
# psutil.virtual_memory() gives total, available, used, and percent.
# We convert bytes to GB for human-readable output (1 GB = 1024^3 bytes).
# =============================================================================
def get_memory_usage():
    mem = psutil.virtual_memory()
    return {
        "total_gb":   round(mem.total / (1024 ** 3), 2),    # Convert bytes → GB
        "used_gb":    round(mem.used / (1024 ** 3), 2),
        "percent":    mem.percent
    }


# =============================================================================
# FUNCTION: get_disk_usage
# Checks disk usage for a given path (default: root "/").
# On Windows, use "C:\\" instead of "/".
# =============================================================================
def get_disk_usage(path="/"):
    disk = psutil.disk_usage(path)
    return {
        "total_gb": round(disk.total / (1024 ** 3), 2),
        "used_gb":  round(disk.used / (1024 ** 3), 2),
        "free_gb":  round(disk.free / (1024 ** 3), 2),
        "percent":  disk.percent
    }


# =============================================================================
# FUNCTION: get_network_stats
# Returns bytes sent and received since the last check.
# psutil.net_io_counters() gives cumulative totals — so we subtract the
# previous reading to get the delta (what changed in the last interval).
# =============================================================================
def get_network_stats(prev_stats=None):
    current = psutil.net_io_counters()
    if prev_stats is None:
        # First reading — no delta available yet
        return {
            "bytes_sent_mb": 0,
            "bytes_recv_mb": 0,
            "_raw": current   # Store raw for next comparison
        }

    # Calculate difference from last reading (delta)
    sent_delta = current.bytes_sent - prev_stats.bytes_sent
    recv_delta = current.bytes_recv - prev_stats.bytes_recv

    return {
        "bytes_sent_mb": round(sent_delta / (1024 ** 2), 2),  # Convert bytes → MB
        "bytes_recv_mb": round(recv_delta / (1024 ** 2), 2),
        "_raw": current
    }


# =============================================================================
# FUNCTION: send_email_alert
# Sends an email alert when a threshold is breached.
# Uses Python's built-in smtplib — no external library needed.
# TLS (Transport Layer Security) encrypts the email connection.
# =============================================================================
def send_email_alert(subject, body):
    if not EMAIL_CONFIG["enabled"]:
        return  # Email not configured, skip silently

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"]    = EMAIL_CONFIG["sender"]
        msg["To"]      = EMAIL_CONFIG["recipient"]

        # Connect to Gmail's SMTP server on port 587 (TLS)
        with smtplib.SMTP(EMAIL_CONFIG["smtp_host"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()                                           # Upgrade connection to encrypted TLS
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])  # Authenticate
            server.sendmail(EMAIL_CONFIG["sender"], EMAIL_CONFIG["recipient"], msg.as_string())

        print(f"  📧 Email alert sent to {EMAIL_CONFIG['recipient']}")

    except Exception as e:
        print(f"  [ERROR] Failed to send email: {e}")


# =============================================================================
# FUNCTION: log_alert
# Saves every alert to a JSON file so you have a history.
# JSON is a standard format — easy to read by humans and machines alike.
# =============================================================================
def log_alert(alert_type, value, threshold):
    alert = {
        "timestamp": datetime.datetime.now().isoformat(),  # ISO format: 2024-01-15T08:30:00
        "type":      alert_type,
        "value":     value,
        "threshold": threshold,
        "message":   f"{alert_type} usage at {value}% exceeded threshold of {threshold}%"
    }

    # Load existing alerts if the file exists, otherwise start fresh
    alerts = []
    if os.path.exists(ALERT_LOG_FILE):
        with open(ALERT_LOG_FILE, "r") as f:
            try:
                alerts = json.load(f)
            except json.JSONDecodeError:
                alerts = []  # File was corrupted or empty — start fresh

    alerts.append(alert)

    # Write the updated list back to the file
    with open(ALERT_LOG_FILE, "w") as f:
        json.dump(alerts, f, indent=2)  # indent=2 = pretty print with 2 spaces


# =============================================================================
# FUNCTION: check_thresholds
# Compares current stats against our defined thresholds.
# If any metric is too high, it triggers an alert.
# =============================================================================
def check_thresholds(cpu, memory, disk):
    alerts_triggered = []

    if cpu >= THRESHOLDS["cpu"]:
        msg = f"🚨 HIGH CPU: {cpu}% (threshold: {THRESHOLDS['cpu']}%)"
        print(f"  {msg}")
        log_alert("CPU", cpu, THRESHOLDS["cpu"])
        send_email_alert("⚠️ Server Alert: High CPU Usage", msg)
        alerts_triggered.append("cpu")

    if memory["percent"] >= THRESHOLDS["memory"]:
        msg = f"🚨 HIGH MEMORY: {memory['percent']}% (threshold: {THRESHOLDS['memory']}%)"
        print(f"  {msg}")
        log_alert("Memory", memory["percent"], THRESHOLDS["memory"])
        send_email_alert("⚠️ Server Alert: High Memory Usage", msg)
        alerts_triggered.append("memory")

    if disk["percent"] >= THRESHOLDS["disk"]:
        msg = f"🚨 HIGH DISK: {disk['percent']}% (threshold: {THRESHOLDS['disk']}%)"
        print(f"  {msg}")
        log_alert("Disk", disk["percent"], THRESHOLDS["disk"])
        send_email_alert("⚠️ Server Alert: High Disk Usage", msg)
        alerts_triggered.append("disk")

    if not alerts_triggered:
        print("  ✅ All systems normal.")

    return alerts_triggered


# =============================================================================
# FUNCTION: print_stats
# Prints a nicely formatted snapshot of current system stats.
# =============================================================================
def print_stats(cpu, memory, disk, network):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*55}")
    print(f"  📊 SYSTEM MONITOR — {now}")
    print(f"{'='*55}")
    print(f"  🖥️  CPU Usage    : {cpu}%")
    print(f"  🧠  Memory       : {memory['percent']}% ({memory['used_gb']} GB / {memory['total_gb']} GB)")
    print(f"  💾  Disk Usage   : {disk['percent']}% ({disk['used_gb']} GB used, {disk['free_gb']} GB free)")
    print(f"  🌐  Network      : ↑ {network['bytes_sent_mb']} MB sent | ↓ {network['bytes_recv_mb']} MB received")
    print(f"{'='*55}")


# =============================================================================
# MAIN — Entry point of the script.
# Runs in an infinite loop, checking stats every CHECK_INTERVAL seconds.
# Press Ctrl+C to stop.
# =============================================================================
def main():
    print("🚀 Python System Monitor Started")
    print(f"   Checking every {CHECK_INTERVAL} seconds. Press Ctrl+C to stop.\n")

    prev_net = None  # Will hold previous network reading for delta calculation

    # Infinite monitoring loop
    while True:
        try:
            # Gather all stats
            cpu     = get_cpu_usage()
            memory  = get_memory_usage()
            disk    = get_disk_usage()
            network = get_network_stats(prev_net)

            # Store raw network data for next iteration's delta calculation
            prev_net = network["_raw"]

            # Print stats to console
            print_stats(cpu, memory, disk, network)

            # Check if any thresholds are breached
            check_thresholds(cpu, memory, disk)

            # Wait before next check
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            # User pressed Ctrl+C — exit cleanly
            print("\n\n👋 Monitor stopped by user.")
            break

        except Exception as e:
            # Catch any unexpected errors and log them without crashing
            print(f"[ERROR] Unexpected error: {e}")
            time.sleep(CHECK_INTERVAL)


# This is Python's way of saying "only run main() if this file is run directly,
# not if it's imported by another script."
if __name__ == "__main__":
    main()
