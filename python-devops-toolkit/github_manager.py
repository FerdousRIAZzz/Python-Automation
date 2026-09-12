"""
=============================================================================
FILE:    github_manager.py
PURPOSE: Automates common GitHub tasks using the GitHub REST API.
         Instead of clicking through GitHub's website, this script lets you
         manage repos, list branches, close issues, and more — from your terminal.

         This is a core DevOps skill: automating manual platform tasks via APIs.
         Tools like GitHub Actions, Jenkins, and ArgoCD all talk to GitHub this way.

LIBRARY: requests — Python's go-to library for making HTTP API calls.
         Install with: pip install requests

SETUP:   1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens
         2. Generate a token with "repo" and "issues" scopes
         3. Set it as an environment variable:
            Linux/Mac: export GITHUB_TOKEN="your_token_here"
            Windows:   set GITHUB_TOKEN=your_token_here

AUTHOR:  Your Name
=============================================================================
"""

import requests    # For making HTTP calls to the GitHub API
import os          # To read environment variables (where we store the token safely)
import json        # For pretty-printing API responses
import sys         # For exiting the script with error codes
from datetime import datetime  # For formatting dates from API responses

# =============================================================================
# CONFIGURATION
# =============================================================================

# Read the GitHub token from an environment variable — NEVER paste tokens directly in code!
# If someone sees your code, they'd have full access to your GitHub account.
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# GitHub's API base URL — all API calls start with this
API_BASE = "https://api.github.com"

# Standard headers sent with every API request
# "Authorization: Bearer <token>" proves who you are to GitHub
# "Accept: application/vnd.github+json" tells GitHub we want JSON back
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept":        "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"  # Pin to a specific API version for stability
}


# =============================================================================
# FUNCTION: check_token
# Validates the token by calling /user — if it works, we know we're authenticated.
# =============================================================================
def check_token():
    if not GITHUB_TOKEN:
        print("[ERROR] No GitHub token found!")
        print("  Set it with: export GITHUB_TOKEN='your_token_here'")
        sys.exit(1)  # Exit with error code 1

    response = requests.get(f"{API_BASE}/user", headers=HEADERS)

    if response.status_code == 200:
        user = response.json()  # Parse the JSON response into a Python dictionary
        print(f"✅ Authenticated as: {user['login']} ({user['name']})")
        return user["login"]
    else:
        print(f"[ERROR] Authentication failed: {response.status_code}")
        print(f"  Response: {response.json().get('message', 'Unknown error')}")
        sys.exit(1)


# =============================================================================
# FUNCTION: list_repositories
# Fetches all repos for the authenticated user.
# The API returns paginated results — we handle that with ?per_page=100.
# =============================================================================
def list_repositories(username):
    print(f"\n📦 Repositories for @{username}:\n")

    # ?per_page=100 gets up to 100 repos per page (GitHub max is 100)
    # ?sort=updated shows most recently updated repos first
    url = f"{API_BASE}/user/repos?per_page=100&sort=updated"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"[ERROR] Could not fetch repos: {response.status_code}")
        return

    repos = response.json()  # List of repo objects

    if not repos:
        print("  No repositories found.")
        return

    # Loop through each repo and print key info
    for i, repo in enumerate(repos, start=1):
        # repo is a dictionary — we access values with repo["key"]
        visibility = "🔒 Private" if repo["private"] else "🌍 Public"
        language   = repo.get("language") or "N/A"  # .get() avoids KeyError if key missing

        # Format the last-updated date from ISO format (2024-01-15T...) to readable
        updated = datetime.strptime(repo["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
        updated_str = updated.strftime("%d %b %Y")

        print(f"  {i:2}. {repo['name']:<35} {visibility:<12} Lang: {language:<12} Updated: {updated_str}")

    print(f"\n  Total: {len(repos)} repositories")
    return repos


# =============================================================================
# FUNCTION: create_repository
# Creates a new GitHub repository via the API.
# This is exactly how CI/CD tools auto-create repos when a new project starts.
# =============================================================================
def create_repository(name, description="", private=False, auto_init=True):
    print(f"\n🆕 Creating repository: {name}")

    # The payload is a Python dict — requests will convert it to JSON automatically
    payload = {
        "name":        name,
        "description": description,
        "private":     private,    # True = private repo, False = public
        "auto_init":   auto_init,  # True = automatically create a README.md
        "gitignore_template": "Python"  # GitHub will add a Python .gitignore automatically
    }

    response = requests.post(f"{API_BASE}/user/repos", headers=HEADERS, json=payload)

    if response.status_code == 201:  # 201 = Created (not 200!)
        repo = response.json()
        print(f"  ✅ Repository created: {repo['html_url']}")
        return repo
    elif response.status_code == 422:
        print(f"  [ERROR] Repository '{name}' already exists or name is invalid.")
    else:
        print(f"  [ERROR] Failed to create repo: {response.status_code} — {response.json().get('message')}")

    return None


# =============================================================================
# FUNCTION: list_open_issues
# Lists all open issues in a repository.
# Issues are how teams track bugs and feature requests — automating this
# is useful for daily stand-up reports or Slack notifications.
# =============================================================================
def list_open_issues(username, repo_name):
    print(f"\n🐛 Open Issues in {username}/{repo_name}:\n")

    url = f"{API_BASE}/repos/{username}/{repo_name}/issues?state=open&per_page=50"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 404:
        print("  [ERROR] Repository not found. Check the username and repo name.")
        return

    if response.status_code != 200:
        print(f"  [ERROR] {response.status_code}: {response.json().get('message')}")
        return

    issues = response.json()

    # GitHub's Issues API also returns Pull Requests — filter them out
    # Real issues don't have a "pull_request" key
    issues = [i for i in issues if "pull_request" not in i]

    if not issues:
        print("  ✅ No open issues. Clean repo!")
        return

    for issue in issues:
        created = datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        labels  = ", ".join([l["name"] for l in issue["labels"]]) or "no labels"
        print(f"  #{issue['number']:<5} {issue['title'][:50]:<50} Labels: {labels}")
        print(f"         Opened: {created.strftime('%d %b %Y')} by @{issue['user']['login']}\n")

    print(f"  Total open issues: {len(issues)}")


# =============================================================================
# FUNCTION: get_repo_stats
# Pulls a summary of a repo's activity — stars, forks, watchers, languages.
# Useful for building GitHub profile dashboards or weekly digest emails.
# =============================================================================
def get_repo_stats(username, repo_name):
    print(f"\n📊 Stats for {username}/{repo_name}:\n")

    # Fetch main repo info
    url = f"{API_BASE}/repos/{username}/{repo_name}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"  [ERROR] {response.status_code}: {response.json().get('message')}")
        return

    repo = response.json()

    print(f"  📝 Description : {repo.get('description') or 'No description'}")
    print(f"  ⭐ Stars        : {repo['stargazers_count']}")
    print(f"  🍴 Forks        : {repo['forks_count']}")
    print(f"  👁️  Watchers     : {repo['watchers_count']}")
    print(f"  🐛 Open Issues  : {repo['open_issues_count']}")
    print(f"  🔤 Language     : {repo.get('language') or 'N/A'}")
    print(f"  📅 Created      : {repo['created_at'][:10]}")
    print(f"  🔄 Last Push    : {repo['pushed_at'][:10]}")
    print(f"  🔗 URL          : {repo['html_url']}")

    # Also fetch language breakdown
    lang_url = f"{API_BASE}/repos/{username}/{repo_name}/languages"
    lang_response = requests.get(lang_url, headers=HEADERS)
    if lang_response.status_code == 200:
        languages = lang_response.json()
        if languages:
            total_bytes = sum(languages.values())
            print(f"\n  💻 Language Breakdown:")
            for lang, bytes_count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                percent = round((bytes_count / total_bytes) * 100, 1)
                print(f"     {lang:<20}: {percent}%")


# =============================================================================
# FUNCTION: add_topics_to_repo
# Topics (tags) on GitHub repos help recruiters and developers find your work.
# Example topics: "devops", "python", "automation", "linux"
# =============================================================================
def add_topics_to_repo(username, repo_name, topics):
    print(f"\n🏷️  Adding topics to {repo_name}: {topics}")

    url = f"{API_BASE}/repos/{username}/{repo_name}/topics"

    # Topics must be lowercase and use hyphens, not spaces
    clean_topics = [t.lower().replace(" ", "-") for t in topics]

    response = requests.put(url, headers=HEADERS, json={"names": clean_topics})

    if response.status_code == 200:
        print(f"  ✅ Topics added: {', '.join(clean_topics)}")
    else:
        print(f"  [ERROR] {response.status_code}: {response.json().get('message')}")


# =============================================================================
# MAIN MENU — Interactive demo of all functions
# =============================================================================
def main():
    print("="*55)
    print("  🐙 GitHub Repository Manager (Python + API)")
    print("="*55)

    # Step 1: Authenticate
    username = check_token()

    # Step 2: Show menu
    while True:
        print("\n" + "="*55)
        print("  What would you like to do?")
        print("  1) List all my repositories")
        print("  2) Create a new repository")
        print("  3) View open issues in a repo")
        print("  4) Get repository stats")
        print("  5) Add topics/tags to a repo")
        print("  6) Exit")
        print("="*55)

        choice = input("  Choose [1-6]: ").strip()

        if choice == "1":
            list_repositories(username)

        elif choice == "2":
            name  = input("  Repo name: ").strip()
            desc  = input("  Description: ").strip()
            priv  = input("  Private? (y/n): ").strip().lower() == "y"
            create_repository(name, desc, priv)

        elif choice == "3":
            repo = input("  Repo name: ").strip()
            list_open_issues(username, repo)

        elif choice == "4":
            repo = input("  Repo name: ").strip()
            get_repo_stats(username, repo)

        elif choice == "5":
            repo   = input("  Repo name: ").strip()
            topics = input("  Topics (comma-separated, e.g. devops,python,automation): ").strip().split(",")
            add_topics_to_repo(username, repo, topics)

        elif choice == "6":
            print("  Goodbye! 👋")
            break

        else:
            print("  [ERROR] Invalid choice. Please enter 1-6.")


if __name__ == "__main__":
    main()
