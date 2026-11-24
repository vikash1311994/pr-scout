#!/usr/bin/env python3
"""
pr-scout — find one vetted, unclaimed issue per repo for a possible PR.

It does NOT open pull requests. It produces a daily shortlist with the signals
that make a contribution safe: fresh issue, no assignee, few comments, no prior
PR referencing it, and no maintainer rejection language.

Usage:
  python3 scout.py --repos laravel/framework,facebook/react --out report.md
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REPOS = [
    "python/cpython", "nodejs/node", "kubernetes/kubernetes", "django/django",
    "pytorch/pytorch", "tensorflow/tensorflow", "huggingface/transformers",
    "pydantic/pydantic", "fastapi/fastapi", "psf/requests", "microsoft/playwright",
    "SeleniumHQ/selenium", "pytest-dev/pytest", "facebook/react",
    "vercel/next.js", "laravel/framework", "laravel/docs",
]

POSITIVE = re.compile(r"(pr welcome|pull request welcome|please (?:send|open|submit) a pr|contributions? welcome|help wanted)", re.I)
NEGATIVE = re.compile(r"(wontfix|won't fix|by design|intended behavior|closing this|duplicate of|already fixed|rejected|not accepting|out of scope)", re.I)


def gh(args: list[str], timeout: int = 90) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def search_issues(repo: str, per_repo: int) -> list[dict]:
    query = f"repo:{repo} is:issue is:open sort:created-desc"
    q = f"search/issues?q={query.replace(' ', '%20')}&per_page={per_repo}"
    raw = gh(["api", q])
    if not raw:
        return []
    try:
        return json.loads(raw).get("items", [])
    except json.JSONDecodeError:
        return []


def prior_prs(repo: str, number: int) -> list[dict]:
    raw = gh(["pr", "list", "-R", repo, "--search", str(number),
              "--state", "all", "--limit", "10", "--json", "number,state,title"])
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def issue_text(repo: str, number: int) -> str:
    raw = gh(["issue", "view", str(number), "-R", repo, "--json", "body,comments"])
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    comments = "\n".join(c.get("body", "") for c in data.get("comments", []))
    return (data.get("body") or "") + "\n" + comments


def age_days(created_at: str) -> int:
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return 9999


def vet(repo: str, item: dict) -> dict | None:
    number = item.get("number")
    comments = item.get("comments", 0)
    if item.get("assignee") or comments > 6 or age_days(item.get("created_at", "")) > 120:
        return None
    prs = prior_prs(repo, number)
    if prs:
        return None
    text = issue_text(repo, number)
    if NEGATIVE.search(text):
        return None
    labels = {x.get("name", "").lower() for x in item.get("labels", [])}
    positive_labels = bool(labels & {
        "enhancement", "feature", "help wanted", "good first issue", "contributions welcome"
    })
    return {
        "repo": repo,
        "number": number,
        "title": item.get("title", ""),
        "comments": comments,
        "age_days": age_days(item.get("created_at", "")),
        "maintainer_blessed": positive_labels or bool(POSITIVE.search(text)),
        "url": item.get("html_url", f"https://github.com/{repo}/issues/{number}"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repos", default=",".join(DEFAULT_REPOS))
    ap.add_argument("--per-repo", type=int, default=15)
    ap.add_argument("--out", help="write Markdown report to this file")
    args = ap.parse_args(argv)

    candidates: list[dict] = []
    for repo in [r.strip() for r in args.repos.split(",") if r.strip()]:
        try:
            for item in search_issues(repo, args.per_repo):
                v = vet(repo, item)
                if v:
                    candidates.append(v)
        except Exception as exc:
            print(f"warning: {repo}: {exc}")

    candidates.sort(key=lambda c: (not c["maintainer_blessed"], c["comments"], c["age_days"]))
    lines = [
        "# PR scout — " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "",
        f"{len(candidates)} vetted candidate(s). No PR is opened automatically.",
        "",
    ]
    if not candidates:
        lines.append("No safe candidate today. Do not force a PR.")
    else:
        lines += ["| Repo | Issue | Age | Comments | Blessed |", "|---|---|---:|---:|---|"]
        for c in candidates[:20]:
            lines.append(
                f"| {c['repo']} | [#{c['number']} {c['title'][:70]}]({c['url']}) "
                f"| {c['age_days']}d | {c['comments']} | {'yes' if c['maintainer_blessed'] else 'no'} |"
            )
        lines += ["", "Only pick a candidate with `Blessed = yes` unless you have read the full thread yourself."]

    report = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
