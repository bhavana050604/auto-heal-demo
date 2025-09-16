# Auto-Heal Demo

This repository is a ready-to-run demo of an **Error-Aware Auto-Healing CI/CD pipeline**.

## Quick start (local)

1. Install Node.js (v18 recommended) and npm.
2. Install dev dependencies:
   ```
   npm install
   ```
3. Run tests locally:
   ```
   npm test
   ```
   You will see a failing test (intentional bug).

## Teach the healer

Add a mapping to the DB so the healer can auto-fix the failure:

```
python3 tools/teach.py --signature "expected 4 to equal 5" --file src/sum.js --search "return a + b - 1;" --replace "return a + b;" --db healer/db.sqlite
```

Commit and push the DB file (`healer/db.sqlite`) to your repo so CI can use it.

## GitHub Actions

Push to GitHub and the workflow `.github/workflows/ci-auto-heal.yml` will run tests. On failure, `tools/heal.py` will try to match the log and apply a patch; if it applies and pushes a commit, GitHub will trigger a new workflow run.
