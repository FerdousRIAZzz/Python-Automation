# 🐍 Python DevOps Toolkit

A portfolio of Python automation scripts covering the four core pillars of DevOps engineering — **Monitoring**, **Infrastructure**, **Cloud**, and **CI/CD Automation**. Every script is production-inspired, heavily commented, and built to demonstrate real-world DevOps skills to recruiters.

---

## 📁 Project Structure

```
python-devops-toolkit/
│
├── monitoring/
│   └── system_monitor.py       # Real-time CPU, RAM, Disk & Network monitor with alerts
│
├── infrastructure/
│   └── infra_health_checker.py # HTTP, Port, DNS & SSL certificate health checks
│
├── cloud/
│   └── cloud_resource_audit.py # AWS resource auditor — cost waste & security gaps
│
├── git_automation/
│   └── github_manager.py       # GitHub API automation — repos, issues, stats & topics
│
├── requirements.txt            # All third-party dependencies
└── README.md                   # You are here
```

---

## 🚀 Scripts Overview

### 1. 📊 `monitoring/system_monitor.py` — Real-Time Server Monitor

Monitors your Linux/Windows server in real-time and fires alerts when resources are overloaded. Think of it as a lightweight, self-built version of **Datadog** or **Prometheus**.

| What it monitors | Alert threshold |
|---|---|
| CPU Usage | > 80% |
| Memory (RAM) | > 80% |
| Disk Space | > 85% |
| Network I/O | Delta per interval |
| Top Processes | Top 5 by CPU |

**Features:**
- 🔴 Console alerts with colour coding
- 📧 Optional email alerts via SMTP (Gmail ready)
- 📝 Alert history saved as JSON
- ♾️ Runs in a loop — checks every N seconds (configurable)

```bash
pip install psutil
python monitoring/system_monitor.py
```

---

### 2. 🏥 `infrastructure/infra_health_checker.py` — Infrastructure Health Checker

Checks the health of any server, website, or service from the outside — the same way tools like **Pingdom** or **UptimeRobot** work under the hood.

| Check | What it does |
|---|---|
| HTTP/HTTPS | Is the website responding? What's the status code? |
| Port Scan | Is the TCP port open? (SSH, DB, app ports) |
| DNS Resolution | Does the domain resolve to an IP? |
| SSL Certificate | When does HTTPS cert expire? Warns if < 30 days |
| Response Time | Flags anything slower than 2 seconds |

**Features:**
- ✅ No external libraries — uses Python built-ins only (`socket`, `ssl`, `urllib`)
- 📄 Saves reports as both **JSON** and **CSV** (for Excel/management)
- ➕ Just add targets to the `TARGETS` list at the top — no code changes needed

```bash
# No pip install needed!
python infrastructure/infra_health_checker.py
```

---

### 3. ☁️ `cloud/cloud_resource_audit.py` — AWS Cloud Resource Auditor

Scans your AWS account for **cost waste** and **security misconfigurations** — the kind of thing a Cloud/DevOps engineer is expected to catch before it becomes a bill or a breach.

| Audit Check | Why it matters |
|---|---|
| Stopped EC2 instances | You still pay for EBS storage even when instances are stopped |
| Security Groups with open ports | Port 22/3389 open to `0.0.0.0/0` = anyone can attempt to break in |
| S3 public bucket access | Public S3 buckets have caused major data breaches at big companies |
| IAM users without MFA | A leaked password = full account access without MFA |

**Features:**
- 🔒 **Read-only** — never modifies anything, safe to run in production
- 📋 Generates a severity-ranked JSON audit report (Critical / High / Medium)
- 🏗️ Uses OOP (Class-based) structure — demonstrates Python best practices

```bash
pip install boto3
aws configure   # Set up your AWS credentials first
python cloud/cloud_resource_audit.py
```

---

### 4. 🐙 `git_automation/github_manager.py` — GitHub API Automation

Automates GitHub repository management using the **GitHub REST API** — no clicking through the website. This is how CI/CD tools, bots, and automation pipelines interact with GitHub.

| Feature | What it does |
|---|---|
| List Repositories | Shows all your repos with visibility, language, and last-updated date |
| Create Repository | Creates a new repo with Python `.gitignore` auto-added |
| View Open Issues | Lists all open issues with labels and author |
| Repository Stats | Stars, forks, watchers, language breakdown % |
| Add Topics/Tags | Adds searchable tags to your repos (great for recruiter visibility!) |

**Features:**
- 🔑 Token-based authentication via environment variable — no hardcoded secrets
- 🌐 Demonstrates REST API patterns (GET, POST, PUT) used across all DevOps tools
- 📋 Interactive menu-driven interface

```bash
pip install requests

# Set your GitHub token safely (never paste it in code!)
export GITHUB_TOKEN="your_personal_access_token"   # Linux/Mac
set GITHUB_TOKEN=your_personal_access_token        # Windows

python git_automation/github_manager.py
```

> **Get a GitHub token:** GitHub → Settings → Developer Settings → Personal Access Tokens → Generate new token (classic) → Select `repo` + `read:user` scopes.

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.8 or higher
- pip (comes with Python)

### Install all dependencies

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/python-devops-toolkit.git
cd python-devops-toolkit

# Install dependencies
pip install -r requirements.txt
```

### Run any script

```bash
python monitoring/system_monitor.py
python infrastructure/infra_health_checker.py
python git_automation/github_manager.py
python cloud/cloud_resource_audit.py  # Requires AWS credentials
```

---

## 🔐 Security Best Practices Demonstrated

This project intentionally demonstrates secure coding habits that matter in DevOps:

| Practice | Where |
|---|---|
| **Never hardcode secrets** — use environment variables | `github_manager.py`, `cloud_resource_audit.py` |
| **Read-only cloud operations** — audit without risk | `cloud_resource_audit.py` |
| **Graceful error handling** — scripts never crash silently | All scripts |
| **Audit logging** — every action is timestamped and saved | `system_monitor.py`, `infra_health_checker.py` |
| **Input validation** — user inputs are sanitised before use | `github_manager.py` |

---

## 🛠️ Skills Demonstrated

| Skill | Evidence |
|---|---|
| Python scripting (intermediate) | OOP classes, functions, error handling, loops |
| REST API integration | GitHub API (GET, POST, PUT requests) |
| AWS SDK (boto3) | EC2, S3, IAM audit automation |
| Linux system internals | psutil, socket, ssl, process monitoring |
| Networking concepts | TCP ports, DNS, SSL/TLS certificates, HTTP status codes |
| Security awareness | MFA checks, open port detection, public bucket alerts |
| DevOps mindset | Automation, monitoring, alerting, self-healing patterns |
| Documentation | Inline comments explaining WHY, not just WHAT |

---

## 🗺️ Roadmap — Coming Soon

- [ ] Docker containerisation of the monitor script
- [ ] Prometheus metrics endpoint for Grafana dashboards
- [ ] Slack/Teams webhook alerting
- [ ] Azure Resource Manager (ARM) audit script
- [ ] GitHub Actions CI pipeline for this repo itself

---

## Author

**[Your Name]**
System/Infrastructure Engineer → Junior DevOps Engineer

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://linkedin.com/in/YOUR_PROFILE)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black)](https://github.com/YOUR_USERNAME)
