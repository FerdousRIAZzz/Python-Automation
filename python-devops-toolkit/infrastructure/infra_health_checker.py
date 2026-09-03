"""
=============================================================================
FILE:    infra_health_checker.py
PURPOSE: Checks the health of servers, websites, and services from outside —
         like a scout doing recon before a mission.

         Tests:
           ✅ HTTP/HTTPS endpoint availability (is your website up?)
           ✅ Port connectivity (is the database port open?)
           ✅ DNS resolution (does the domain name resolve correctly?)
           ✅ SSL certificate expiry (is your HTTPS cert about to expire?)
           ✅ Response time measurement (how fast is the server?)

         This is exactly what uptime monitoring tools like Pingdom,
         UptimeRobot, or Grafana probes do — here you can see the internals.

LIBRARIES: All built-in Python! No pip install needed.
           socket, ssl, urllib — standard Python networking libraries.

AUTHOR:  Your Name
=============================================================================
"""

import socket        # Low-level networking — DNS lookups and port checks
import ssl           # SSL/TLS certificates — for checking HTTPS expiry
import urllib.request  # Making HTTP requests (built-in, no requests library needed)
import urllib.error
import json          # Saving results as JSON report
import time          # Measuring response times
import datetime      # Parsing and comparing certificate dates
import csv           # Saving results as CSV for Excel/spreadsheet use
import os

# =============================================================================
# TARGETS — Define what you want to monitor here
# Add as many as you need. This list drives everything.
# =============================================================================
TARGETS = [
    {"name": "Google",       "url": "https://www.google.com",   "port": 443},
    {"name": "GitHub",       "url": "https://www.github.com",   "port": 443},
    {"name": "Cloudflare DNS", "url": "https://1.1.1.1",        "port": 443},
    # Add your own servers:
    # {"name": "My App",     "url": "https://myapp.example.com","port": 443},
    # {"name": "My DB Server","url": "http://10.0.0.5",         "port": 3306},
]

# Warn if SSL cert expires within this many days
SSL_WARN_DAYS = 30

# Warn if response time is slower than this (in seconds)
SLOW_RESPONSE_THRESHOLD = 2.0


# =============================================================================
# FUNCTION: check_http
# Makes an HTTP GET request to the URL and measures:
# - Whether it responded (is it up?)
# - The HTTP status code (200=OK, 404=not found, 500=server error)
# - How long it took to respond (latency)
# =============================================================================
def check_http(url, timeout=5):
    """
    timeout=5 means: if the server doesn't respond within 5 seconds,
    we give up and mark it as DOWN. In production, 5s is already too slow.
    """
    start_time = time.time()  # Record start time in seconds (Unix timestamp)

    try:
        # urllib.request.urlopen opens the URL like a browser would
        with urllib.request.urlopen(url, timeout=timeout) as response:
            elapsed = round(time.time() - start_time, 3)  # How long it took
            status  = response.status  # HTTP status code (200, 301, 404, etc.)

            return {
                "status":   "UP",
                "code":     status,
                "latency":  elapsed,
                "slow":     elapsed > SLOW_RESPONSE_THRESHOLD
            }

    except urllib.error.HTTPError as e:
        # Server responded but with an error code (4xx, 5xx)
        elapsed = round(time.time() - start_time, 3)
        return {"status": "ERROR", "code": e.code, "latency": elapsed, "slow": False}

    except urllib.error.URLError as e:
        # Could not reach the server at all (DNS failure, connection refused, timeout)
        return {"status": "DOWN", "code": 0, "latency": None, "error": str(e.reason)}

    except Exception as e:
        return {"status": "DOWN", "code": 0, "latency": None, "error": str(e)}


# =============================================================================
# FUNCTION: check_port
# Tries to open a raw TCP connection to a host on a specific port.
# If it connects, the port is open. If it fails, the port is closed or blocked.
#
# This is like knocking on a specific door of a building:
# - Port 80  = HTTP (web traffic)
# - Port 443 = HTTPS (secure web traffic)
# - Port 22  = SSH (remote terminal)
# - Port 3306 = MySQL database
# - Port 5432 = PostgreSQL database
# =============================================================================
def check_port(host, port, timeout=5):
    # Extract hostname from URL if full URL is given
    # e.g., "https://www.google.com" → "www.google.com"
    host = host.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        # socket.AF_INET = IPv4, socket.SOCK_STREAM = TCP connection
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))  # Returns 0 if connection succeeded

            if result == 0:
                return {"status": "OPEN", "port": port}
            else:
                return {"status": "CLOSED", "port": port, "error_code": result}

    except socket.gaierror:
        # gaierror = "Get Address Info" error — DNS lookup failed
        return {"status": "DNS_FAIL", "port": port}

    except Exception as e:
        return {"status": "ERROR", "port": port, "error": str(e)}


# =============================================================================
# FUNCTION: check_dns
# Checks if a domain name resolves to an IP address.
# Every website needs DNS to work — like a phonebook for the internet.
# If DNS fails, no one can reach your server even if it's running fine.
# =============================================================================
def check_dns(host):
    host = host.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        # socket.gethostbyname converts domain → IP address
        # e.g., "google.com" → "142.250.74.46"
        ip_address = socket.gethostbyname(host)
        return {"status": "OK", "ip": ip_address}

    except socket.gaierror as e:
        return {"status": "FAIL", "error": str(e)}


# =============================================================================
# FUNCTION: check_ssl_expiry
# Connects to the server using SSL (HTTPS) and reads the certificate.
# Certificates have an expiry date — if they expire, browsers show a scary
# "Not Secure" warning and users can't access your site.
#
# This check tells you HOW MANY DAYS are left before expiry, so you can
# renew before it's a problem. Let's Encrypt certs expire every 90 days!
# =============================================================================
def check_ssl_expiry(host, port=443):
    host = host.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        # Create a default SSL context (trusts system's CA certificates)
        context = ssl.create_default_context()

        # Connect to the server and get its SSL certificate
        with socket.create_connection((host, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()  # Returns the certificate as a dictionary

        # Parse the expiry date from the certificate
        # SSL certs store dates in format: "May 15 12:00:00 2025 GMT"
        expire_date_str = cert["notAfter"]
        expire_date     = datetime.datetime.strptime(expire_date_str, "%b %d %H:%M:%S %Y %Z")
        days_remaining  = (expire_date - datetime.datetime.utcnow()).days

        return {
            "status":         "OK",
            "expires":        expire_date.strftime("%Y-%m-%d"),
            "days_remaining": days_remaining,
            "warning":        days_remaining <= SSL_WARN_DAYS
        }

    except ssl.SSLCertVerificationError as e:
        # Certificate is invalid or untrusted
        return {"status": "INVALID", "error": str(e)}

    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


# =============================================================================
# FUNCTION: run_full_check
# Runs all checks on a single target and returns a combined report.
# =============================================================================
def run_full_check(target):
    name = target["name"]
    url  = target["url"]
    port = target.get("port", 443)
    host = url.replace("https://", "").replace("http://", "").split("/")[0]

    print(f"\n  🔍 Checking: {name} ({url})")

    result = {
        "name":      name,
        "url":       url,
        "timestamp": datetime.datetime.now().isoformat(),
        "http":      check_http(url),
        "port":      check_port(host, port),
        "dns":       check_dns(host),
        "ssl":       check_ssl_expiry(host) if url.startswith("https") else {"status": "SKIP"}
    }

    # Print summary
    http_icon = "✅" if result["http"]["status"] == "UP" else "❌"
    port_icon = "✅" if result["port"]["status"] == "OPEN" else "❌"
    dns_icon  = "✅" if result["dns"]["status"] == "OK" else "❌"

    latency_str = f"{result['http']['latency']}s" if result['http']['latency'] else "N/A"
    slow_flag   = " ⚠️ SLOW" if result["http"].get("slow") else ""

    print(f"    {http_icon} HTTP   : {result['http']['status']} (code: {result['http']['code']}, latency: {latency_str}{slow_flag})")
    print(f"    {port_icon} Port   : {result['port']['status']} (port {port})")
    print(f"    {dns_icon} DNS    : {result['dns']['status']} → {result['dns'].get('ip', 'N/A')}")

    if result["ssl"]["status"] not in ("SKIP", "ERROR", "INVALID"):
        ssl_icon = "⚠️" if result["ssl"].get("warning") else "✅"
        print(f"    {ssl_icon} SSL    : Expires {result['ssl']['expires']} ({result['ssl']['days_remaining']} days left)")
    elif result["ssl"]["status"] == "INVALID":
        print(f"    ❌ SSL    : INVALID CERTIFICATE — {result['ssl'].get('error','')}")

    return result


# =============================================================================
# FUNCTION: save_report
# Saves the full check results to both JSON and CSV formats.
# JSON = good for APIs and dashboards. CSV = good for Excel and managers. 😄
# =============================================================================
def save_report(results):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON report
    json_file = f"health_report_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  💾 JSON report saved: {json_file}")

    # Save CSV report (flattened — one row per target)
    csv_file = f"health_report_{timestamp}.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        # Write header row
        writer.writerow(["Name", "URL", "HTTP Status", "HTTP Code", "Latency(s)", "Port Status", "DNS Status", "DNS IP", "SSL Expires", "SSL Days Left"])
        # Write one row per target
        for r in results:
            writer.writerow([
                r["name"], r["url"],
                r["http"]["status"], r["http"]["code"], r["http"].get("latency", ""),
                r["port"]["status"],
                r["dns"]["status"], r["dns"].get("ip", ""),
                r["ssl"].get("expires", ""), r["ssl"].get("days_remaining", "")
            ])
    print(f"  💾 CSV  report saved: {csv_file}")


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("="*55)
    print("  🏥 Infrastructure Health Checker")
    print(f"  Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*55)

    all_results = []

    for target in TARGETS:
        result = run_full_check(target)
        all_results.append(result)

    # Summary
    up_count   = sum(1 for r in all_results if r["http"]["status"] == "UP")
    down_count = len(all_results) - up_count

    print(f"\n{'='*55}")
    print(f"  📋 SUMMARY: {up_count} UP  |  {down_count} DOWN  |  {len(all_results)} Total")
    print(f"{'='*55}")

    # Save reports
    save_report(all_results)


if __name__ == "__main__":
    main()
