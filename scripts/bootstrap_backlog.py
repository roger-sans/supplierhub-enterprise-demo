"""Initialize this product's GitHub Issues and milestones using an authenticated gh CLI."""
import argparse
import json
import subprocess
from pathlib import Path

BACKLOG = Path(__file__).resolve().parents[1] / "docs" / "backlog.json"
REPOSITORY = "roger-sans/supplierhub-enterprise-demo"


def gh(*args, payload=None, pages=False):
    result = subprocess.run(
        ["gh", *args], input=json.dumps(payload) if payload is not None else None,
        capture_output=True, text=True, check=True,
    )
    if not pages:
        return json.loads(result.stdout) if result.stdout.strip() else None
    # gh versions that predate --slurp emit one JSON array per page.
    pending = result.stdout.strip()
    decoder = json.JSONDecoder()
    rows = []
    while pending:
        page, end = decoder.raw_decode(pending)
        rows.extend(page)
        pending = pending[end:].lstrip()
    return rows


def issue_title(item):
    return f"[{item['id']}] {item['title']}"


def issue_body(item):
    checks = "\n".join("- " + criterion for criterion in item["acceptance"])
    dependencies = ", ".join(item["depends"]) or "None"
    links = f"\nVerification: `{item['evidence']}`\n" if item["evidence"] else ""
    return (
        f"**{item['kind']} · {item['epic']} · Priority {item['rank']}**\n\n"
        f"{item['user']}\n\n{item['value']}\n\n"
        f"Accepting role: {item['owner']}\n\nRisk: {item['risk']}\n\nDependencies: {dependencies}\n\n"
        f"## Acceptance criteria\n\n{checks}\n{links}"
    )


def bootstrap(backlog):
    base = f"repos/{REPOSITORY}"
    state = gh("api", base)
    if not state["private"]:
        raise SystemExit("Initialize the backlog while the new repository is private.")
    existing_milestones = gh("api", "--paginate", base + "/milestones?state=all&per_page=100", pages=True)
    existing_issues = gh("api", "--paginate", base + "/issues?state=all&per_page=100", pages=True)
    milestones = {row["title"]: row for row in existing_milestones}
    issues = {row["title"].split("]", 1)[0][1:]: row for row in existing_issues if "pull_request" not in row and row["title"].startswith("[SH-")}
    numbers = []
    for milestone in backlog["milestones"]:
        title = milestone["title"]
        if title not in milestones:
            milestones[title] = gh("api", "--method", "POST", base + "/milestones", "--input", "-",
                                   payload={**milestone, "state": "open"})
        numbers.append(milestones[title]["number"])
    for item in backlog["items"]:
        title = issue_title(item)
        issue = issues.get(item["id"])
        if not issue:
            issue = gh("api", "--method", "POST", base + "/issues", "--input", "-", payload={
                "title": title, "body": issue_body(item), "milestone": numbers[item["milestone"]],
                "labels": ["enhancement"],
            })
        if item["done"] and issue["state"] == "open":
            gh("api", "--method", "PATCH", base + f"/issues/{issue['number']}", "--input", "-",
               payload={"state": "closed", "state_reason": "completed"})
        print(f"{item['id']} · #{issue['number']} · {item['title']}")
    for milestone in backlog["milestones"]:
        current = milestones[milestone["title"]]
        if milestone["state"] == "closed" and current["state"] == "open":
            gh("api", "--method", "PATCH", base + f"/milestones/{current['number']}", "--input", "-",
               payload={"state": "closed"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help=f"Create issues and milestones in the private repository {REPOSITORY}")
    args = parser.parse_args()
    backlog = json.loads(BACKLOG.read_text())
    if args.apply:
        try:
            bootstrap(backlog)
        except subprocess.CalledProcessError as error:
            raise SystemExit(error.stderr.strip()) from error
    else:
        for item in backlog["items"]:
            print(f"{item['rank']:2}. {issue_title(item)} · {item['kind']} · {item['owner']}")
