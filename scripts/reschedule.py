"""
reschedule.py — Shift a GitHub issue's due date and cascade to all downstream issues.

Usage:
  python scripts/reschedule.py --issue 3 --new-start 2026-04-25

How it works:
  1. Reads the issue body to find "blocks: #N" markers
  2. Calculates how many days the date shifted
  3. Updates the due date on this issue and all downstream ones
  4. Posts an audit comment on every affected issue

Requires GITHUB_TOKEN and GITHUB_REPO in .env
"""
import argparse
import re
import sys
from datetime import datetime, timedelta
import requests
from polymatt.config import GITHUB_TOKEN, GITHUB_REPO

BASE_URL = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

DATE_FORMAT = "%Y-%m-%d"
DATE_PATTERN = re.compile(r"Due:\s*(\d{4}-\d{2}-\d{2})")
BLOCKS_PATTERN = re.compile(r"blocks:\s*#(\d+)", re.IGNORECASE)


def get_issue(number: int) -> dict:
    resp = requests.get(f"{BASE_URL}/repos/{GITHUB_REPO}/issues/{number}", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def update_issue_body(number: int, new_body: str):
    resp = requests.patch(
        f"{BASE_URL}/repos/{GITHUB_REPO}/issues/{number}",
        headers=HEADERS,
        json={"body": new_body},
    )
    resp.raise_for_status()


def post_comment(number: int, message: str):
    resp = requests.post(
        f"{BASE_URL}/repos/{GITHUB_REPO}/issues/{number}/comments",
        headers=HEADERS,
        json={"body": message},
    )
    resp.raise_for_status()


def shift_issue(number: int, delta_days: int, changed_by: str):
    """Shift one issue's due date by delta_days and cascade to blocked issues."""
    issue = get_issue(number)
    body = issue["body"] or ""
    title = issue["title"]

    # Find current due date
    match = DATE_PATTERN.search(body)
    if not match:
        print(f"  Issue #{number} has no 'Due: YYYY-MM-DD' line — skipping")
        return

    old_date = datetime.strptime(match.group(1), DATE_FORMAT)
    new_date = old_date + timedelta(days=delta_days)
    new_body = DATE_PATTERN.sub(f"Due: {new_date.strftime(DATE_FORMAT)}", body)

    update_issue_body(number, new_body)
    comment = (
        f"📅 **Date rescheduled** by `{changed_by}`\n"
        f"- Due date: `{old_date.strftime(DATE_FORMAT)}` → `{new_date.strftime(DATE_FORMAT)}`\n"
        f"- Shift: {delta_days:+d} days\n"
        f"- Cascaded from upstream reschedule"
    )
    post_comment(number, comment)
    print(f"  Issue #{number} ({title[:40]}): {old_date.strftime(DATE_FORMAT)} → {new_date.strftime(DATE_FORMAT)} ✓")

    # Cascade to blocked issues
    for m in BLOCKS_PATTERN.finditer(body):
        blocked_number = int(m.group(1))
        shift_issue(blocked_number, delta_days, changed_by)


def main():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[PolyMatt] ERROR: GITHUB_TOKEN and GITHUB_REPO must be set in .env")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Cascade GitHub issue date changes")
    parser.add_argument("--issue", type=int, required=True, help="Issue number to reschedule")
    parser.add_argument("--new-start", required=True, help="New start date (YYYY-MM-DD)")
    args = parser.parse_args()

    # Calculate delta from issue's current start date
    issue = get_issue(args.issue)
    body = issue["body"] or ""
    match = re.search(r"Start:\s*(\d{4}-\d{2}-\d{2})", body)
    if not match:
        print(f"Issue #{args.issue} has no 'Start: YYYY-MM-DD' line. Add it to the issue body.")
        sys.exit(1)

    old_start = datetime.strptime(match.group(1), DATE_FORMAT)
    new_start = datetime.strptime(args.new_start, DATE_FORMAT)
    delta_days = (new_start - old_start).days

    print(f"[PolyMatt] Rescheduling issue #{args.issue} by {delta_days:+d} days...")
    shift_issue(args.issue, delta_days, changed_by="reschedule.py")
    print(f"\n[PolyMatt] Done. All downstream issues updated and commented.")


if __name__ == "__main__":
    main()
