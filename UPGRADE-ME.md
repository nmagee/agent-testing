# UPGRADE-ME: Agent-driven upgrades with GitHub Copilot

This guide sets up the GitHub Copilot cloud agent (formerly "coding agent") to upgrade this repo
to current versions of Python, its dependencies, the test suite and the Dockerfile, and to verify
the result. It then adds a monthly schedule that repeats the cycle. Every change arrives as a pull
request that a human reviews and merges. Copilot never pushes to `main`.

Nothing in this file has been applied yet. Work through the steps in order.

> GitHub renames Copilot settings and features often. If a menu path below doesn't match what you
> see, search the [Copilot cloud agent docs](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-github)
> for the same setting.

---

## How it works

1. A GitHub Actions workflow runs on a schedule (monthly) or on demand.
2. It opens an issue describing the upgrade and assigns that issue to Copilot.
3. Copilot works in a GitHub Actions sandbox, pushes a `copilot/*` branch, and opens a draft PR.
4. The CI workflow runs the tests and builds and smoke-tests the Docker image on that PR.
5. You review, ask for changes with `@copilot` comments on the PR if needed, then merge.

Copilot works on a branch in this repository, not a fork. Branch protection on `main` (step 3)
provides the same safeguard a fork would: nothing lands without your review.

---

## 1. Account prerequisites

- A Copilot plan that includes the cloud agent: **Copilot Pro, Pro+, Business or Enterprise**.
  Copilot Free does not include it.
- **Personal account (Pro/Pro+):** the agent is enabled by default. Check under
  *github.com → Settings → Copilot → Features* that the cloud agent is not turned off.
- **Business/Enterprise (e.g. a university org):** an org or enterprise admin must enable the
  Copilot cloud agent policy under *Organization → Settings → Copilot → Policies*. If the repo
  lives under an org, ask your admin to confirm this first.
- Each agent session uses GitHub Actions minutes and Copilot premium requests. Check the
  allowances on your plan.

## 2. Repository settings

In *github.com/nmagee/agent-testing → Settings*:

1. **Copilot → Cloud agent:** make sure the agent is enabled for this repository. Leave the
   firewall on (the default). Add these to the allowlist if the agent reports blocked hosts:
   `pypi.org`, `files.pythonhosted.org`, `registry-1.docker.io`, `auth.docker.io`,
   `production.cloudflare.docker.com`, `docker.io`.
2. **Actions → General:** make sure GitHub Actions is allowed to run.
3. By default, CI workflows on Copilot's PRs wait until a human clicks **Approve and run
   workflows** on the PR. Leave that default in place (if the cloud agent settings page offers an
   option to skip approval, leave it off). It is part of the human review.

## 3. Protect `main`

*Settings → Rules → Rulesets → New branch ruleset*, target `main`:

- Require a pull request before merging, with **1 approval**.
- Require status checks to pass: add `test` and `docker` (the job names from step 5, available
  after the CI workflow has run once).
- Block force pushes.

Note: GitHub does not let the person who assigned the task to Copilot count as the approving
reviewer on Copilot's PR. If you are the only maintainer, either set required approvals to 0 and
rely on your own review before merging, or add a second reviewer.

## 4. Add a personal access token for the scheduler

Assigning an issue to Copilot requires a **user** token. The default Actions `GITHUB_TOKEN` cannot
do it.

1. *github.com → Settings → Developer settings → Fine-grained tokens → Generate new token.*
2. Resource owner: the account or org that owns the repo. Repository access: **only
   `agent-testing`**.
3. Repository permissions, **Read and write**: Actions, Contents, Issues, Pull requests.
   (Metadata: read is added automatically.)
4. Expiration: up to one year. Set a calendar reminder to rotate it.
5. Save it as a repository secret: *Settings → Secrets and variables → Actions → New repository
   secret*, name **`COPILOT_ASSIGN_TOKEN`**.

The token's owner must have a Copilot license that includes the cloud agent.

## 5. Add files to the repo

Create these five files on a branch, open a PR, and merge it. All file contents are below.

| File | Purpose |
|---|---|
| `.github/copilot-instructions.md` | Standing rules Copilot reads on every task in this repo |
| `.github/workflows/copilot-setup-steps.yml` | Pre-installs tools in Copilot's sandbox |
| `.github/workflows/ci.yml` | Independent test + Docker verification on every PR |
| `.github/upgrade-task.md` | The upgrade task given to Copilot each cycle |
| `.github/workflows/monthly-upgrade.yml` | Opens the issue and assigns it to Copilot monthly |

### 5a. `.github/copilot-instructions.md`

```markdown
# Copilot instructions for agent-testing

This is a small FastAPI book-catalog API (`app/main.py`) with a pytest suite (`tests/`),
a Pipfile/Pipfile.lock, and a multi-stage Dockerfile.

## Environment
- Use pipenv for all Python dependency management. Never add requirements.txt to the repo
  (the Dockerfile may generate one at build time).
- Run tests with: `pipenv run pytest -q`
- Build and smoke-test the image with:
  `docker build -t agent-testing . && docker run -d -p 8000:8000 --name at agent-testing`
  then `curl -fsS localhost:8000/` must return JSON with `"service": "book-catalog"`.

## Rules
- Keep the API's external behavior identical: same routes, status codes, and response bodies.
  The existing tests define that behavior. You may modernize test code, but do not weaken or
  delete an assertion to make a test pass.
- Prefer each library's current idiomatic API over compatibility shims.
- Keep README.md accurate: update the version table and remove notes about workarounds
  that no longer apply.
- Never commit secrets, generated caches, or virtualenvs.
- In the PR description, list every version change (old → new), every code change made to
  accommodate a breaking API change, and the exact verification commands you ran with results.
```

### 5b. `.github/workflows/copilot-setup-steps.yml`

The job **must** be named `copilot-setup-steps`. Copilot runs it before starting work. Docker is
already available on the `ubuntu-latest` runner.

```yaml
name: Copilot setup steps

on:
  workflow_dispatch:
  push:
    paths: [.github/workflows/copilot-setup-steps.yml]
  pull_request:
    paths: [.github/workflows/copilot-setup-steps.yml]

jobs:
  copilot-setup-steps:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v5

      # Install the newest stable Python. Copilot may install others if a dependency needs it.
      - uses: actions/setup-python@v6
        with:
          python-version: "3.x"

      - name: Install pipenv
        run: python -m pip install --upgrade pip pipenv

      - name: Show tool versions
        run: |
          python --version
          pipenv --version
          docker --version
```

### 5c. `.github/workflows/ci.yml`

This verifies every PR independently of what Copilot reports. It reads the Python version from the
`Pipfile`, so it follows the upgrade automatically.

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Read Python version from Pipfile
        id: py
        run: echo "version=$(grep -Po 'python_version = "\K[^"]+' Pipfile)" >> "$GITHUB_OUTPUT"
      - uses: actions/setup-python@v6
        with:
          python-version: ${{ steps.py.outputs.version }}
      - run: python -m pip install pipenv
      - run: pipenv install --dev --deploy
      - run: pipenv run pytest -v

  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - run: docker build -t agent-testing:ci .
      - name: Smoke test
        run: |
          docker run -d -p 8000:8000 --name app agent-testing:ci
          for i in $(seq 1 20); do
            curl -fsS localhost:8000/ && break
            sleep 1
          done
          curl -fsS localhost:8000/ | grep -q '"service":"book-catalog"'
          curl -fsS localhost:8000/books | grep -q '"id"'
      - if: always()
        run: docker logs app || true
```

Note: CI will fail on the current repo until the first upgrade, because pipenv on a current
runner cannot install the 2018 lock on Python 3.8 (see README). That is expected. If you want CI
green before the first upgrade, merge this file in the same PR Copilot opens, or add it after the
first upgrade lands.

### 5d. `.github/upgrade-task.md`

This is the issue body. Edit it to change what each cycle does.

```markdown
Upgrade this repository to the latest stable versions of everything it depends on, then verify.

## Scope
1. **Python:** move to the newest stable CPython release that all dependencies support. Update
   `[requires] python_version` in the Pipfile.
2. **Dependencies:** upgrade every package in the Pipfile (runtime and dev) to its latest stable
   release. Remove pins that only existed to work around old-version bugs (e.g. setuptools,
   attrs, pluggy, py, atomicwrites). Drop packages no longer needed (e.g. replace `requests`
   with `httpx` if the current TestClient requires it). Regenerate `Pipfile.lock` with
   `pipenv lock`.
3. **Application code:** update `app/main.py` for breaking changes, e.g. top-level
   `from fastapi import ...`, `fastapi.HTTPException`, pydantic v2 (`Field`, `field_validator`,
   `model_config`, `model_dump`), and a lifespan handler instead of `@app.on_event`.
   Keep external API behavior unchanged.
4. **Tests:** update `tests/` to current pytest and FastAPI testing practice. Keep every existing
   assertion's intent. Add tests for any behavior that was untested and that your changes
   touched.
5. **Dockerfile:** use the matching current `python:<version>-slim` base image (current Debian
   release), keep the multi-stage build, run as a non-root user, remove the
   `--loop asyncio` workaround if no longer needed, and update `.dockerignore` if required.
6. **Docs:** update README.md (version table, setup steps, known problems).

## Verification (required before marking the PR ready)
- `pipenv install --dev --deploy` succeeds from a clean environment.
- `pipenv run pytest -v` passes.
- `docker build` succeeds and the smoke test in `.github/workflows/ci.yml` passes locally.
- Paste the command output summaries into the PR description.

## If already current
If nothing has a newer release since the last cycle, make no changes and say so in a PR comment
or close the task with an explanation.
```

### 5e. `.github/workflows/monthly-upgrade.yml`

Runs at 09:00 UTC on the 1st of each month, and can be started by hand from the Actions tab.

```yaml
name: Monthly upgrade (Copilot)

on:
  schedule:
    - cron: "0 9 1 * *"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  open-upgrade-issue:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      # The issue closes when its PR merges, so an open issue means an unfinished cycle.
      - name: Skip if a previous upgrade is still open
        id: check
        env:
          GH_TOKEN: ${{ secrets.COPILOT_ASSIGN_TOKEN }}
        run: |
          open=$(gh issue list --state open --label dependencies --search "Monthly upgrade in:title" --json number --jq 'length')
          echo "open=$open" >> "$GITHUB_OUTPUT"

      - name: Create issue and assign to Copilot
        if: steps.check.outputs.open == '0'
        env:
          GH_TOKEN: ${{ secrets.COPILOT_ASSIGN_TOKEN }}
        run: |
          title="Monthly upgrade: $(date -u +%Y-%m)"
          jq -n --arg title "$title" --rawfile body .github/upgrade-task.md \
            '{title: $title, body: $body, labels: ["dependencies"], assignees: ["copilot-swe-agent[bot]"]}' \
          | gh api repos/${{ github.repository }}/issues --method POST --input -
```

Create the `dependencies` label first (*Issues → Labels*), or remove `labels` from the payload.

---

## 6. First run and verification

1. After the step 5 PR is merged, go to *Actions → Copilot setup steps → Run workflow*. It must
   pass, or Copilot will start in a broken environment.
2. Go to *Actions → Monthly upgrade (Copilot) → Run workflow*.
3. Confirm a new issue appears, assigned to Copilot, with an 👀 reaction. Within a minute Copilot
   opens a draft PR linked to it. You can watch progress from the PR's **View session** button or
   at [github.com/copilot/agents](https://github.com/copilot/agents).
4. When Copilot finishes, it requests your review. Click **Approve and run workflows** so CI runs.
5. Review the PR:
   - Read the version table in the description and the diff of `app/main.py`.
   - Confirm both CI jobs (`test`, `docker`) passed.
   - Optionally check it out locally: `gh pr checkout <n>`, then `pipenv install --dev`,
     `pipenv run pytest`, `docker build -t agent-testing . && docker run -p 8000:8000 agent-testing`.
6. If something needs changing, comment on the PR starting with `@copilot` (e.g.
   "@copilot the Dockerfile still runs as root"). Copilot pushes follow-up commits. It does not
   read later comments on the issue, only on the PR.
7. When satisfied, mark the PR ready, approve (or have a second reviewer approve), and merge.
   The issue closes automatically.

## 7. Ongoing maintenance

- **Each month:** one issue and one PR appear on the 1st. Review and merge, or close the PR if the
  changes aren't wanted. If the previous upgrade issue is still open, the workflow skips that month.
- **Token:** rotate `COPILOT_ASSIGN_TOKEN` before it expires. When it expires, the scheduled run
  fails with a 401 in the Actions log.
- **Changing the task:** edit `.github/upgrade-task.md`. Changing the rules Copilot follows on all
  tasks: edit `.github/copilot-instructions.md`.
- **Pausing:** *Actions → Monthly upgrade (Copilot) → ⋯ → Disable workflow*.
- **Scheduled workflows** are disabled automatically by GitHub after 60 days without repository
  activity. Monthly merges keep it active. If you skip two months, re-enable it in the Actions tab.

## References

- [Using Copilot cloud agent on GitHub](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-github)
- [Using Copilot cloud agent via the API](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-via-the-api)
- [Asking Copilot to create a pull request](https://docs.github.com/en/copilot/using-github-copilot/coding-agent/using-copilot-to-work-on-an-issue)
- [Changelog: Assign issues to Copilot using the API (Dec 2025)](https://github.blog/changelog/2025-12-03-assign-issues-to-copilot-using-the-api/)
