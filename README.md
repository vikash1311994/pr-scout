# pr-scout

A daily shortlist of GitHub issues that are actually safe to attempt — no automatic PRs.

Top repositories get dozens of drive-by PRs a day. Maintaining a real contribution record means **fewer, better PRs**, not one per day regardless of quality. This tool finds candidates that pass a basic safety screen; you still read the thread and decide.

## The screen

For each open issue in the configured repos:

- unassigned
- at most 6 comments
- created within 120 days
- **no PR, open or closed, referencing the issue number** (rejected directions are the main trap)
- no `wontfix`, `by design`, `duplicate`, `already fixed`, or `closing` language in comments
- flags issues where a maintainer said "PR welcome" or similar

## Run

```bash
python3 scout.py --repos laravel/framework,facebook/react --out report.md
```

Requires `gh` authenticated. No API token is stored by this tool.

## Output

A Markdown table with repo, issue, age, comment count, and whether a maintainer explicitly welcomed a PR. If nothing passes, the report says so — that is a valid result. Do not force a PR on a bad day.

## Why no auto-submit

Automatic daily PRs into high-star repos are flagged as spam, get closed, and damage the account's reputation. A vetted candidate you approve is worth more than thirty closed PRs.
