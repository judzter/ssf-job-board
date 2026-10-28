# SSF Portfolio Job Board

Auto-aggregates open roles from portfolio companies' public ATS feeds
(Greenhouse, Lever, Ashby) and serves a live `jobs.json` that a Webflow
embed on [sarahsmith.fund](https://www.sarahsmith.fund/) reads to render
the job board.

## How it works

```
companies.json  ──►  fetch_jobs.py  ──►  jobs.json
     (52 co.)       (ATS auto-detect)    (refreshed daily)
                                              │
                                    GitHub Pages (public URL)
                                              │
                                    Webflow embed on sarahsmith.fund
```

GitHub Actions runs `fetch_jobs.py` every morning at 06:00 UTC, commits
the updated `jobs.json` back to the repo, and GitHub Pages serves it at a
stable public URL.

---

## One-time setup (≈ 20 minutes)

### 1 — Create the GitHub repository

1. Go to [github.com/new](https://github.com/new) (sign in as the SSF org or your personal account).
2. Name it **`ssf-job-board`** (private or public — both work, but **public** is required for free GitHub Pages).
3. Leave "Initialize repository" unchecked. Click **Create repository**.

### 2 — Push these files

From your terminal:

```bash
cd ssf-job-board          # this folder
git init
git add .
git commit -m "init: SSF job board"
git branch -M main
git remote add origin https://github.com/YOUR-ORG/ssf-job-board.git
git push -u origin main
```

Replace `YOUR-ORG` with the GitHub org or username you used in step 1.

### 3 — Enable GitHub Pages

1. In the repo → **Settings → Pages**.
2. Under **Source**, choose **Deploy from a branch**.
3. Branch: `main`, folder: `/ (root)`. Click **Save**.
4. After ~60 seconds you'll see:
   > Your site is live at `https://YOUR-ORG.github.io/ssf-job-board/`

Your `jobs.json` will be at:
```
https://YOUR-ORG.github.io/ssf-job-board/jobs.json
```

### 4 — Run the first refresh

The daily cron job won't fire until tomorrow. Trigger it manually now:

1. In the repo → **Actions** tab.
2. Click **Refresh Jobs** → **Run workflow** → **Run workflow**.
3. Wait ~2 minutes. When it goes green, `jobs.json` is live.

> **Tip:** Click the workflow run to see which companies had ATS feeds detected and how many jobs each returned.

### 5 — Add the Webflow embed

1. Open `webflow-embed.html` and copy everything inside it.
2. In Webflow Designer, navigate to your Jobs page (create one if needed).
3. Drop an **Embed** element where you want the board.
4. Paste the copied code into the embed editor.
5. **Edit line 1 of the `<script>` block**:
   ```js
   var JOBS_JSON_URL = "https://YOUR-ORG.github.io/ssf-job-board/jobs.json";
   ```
   Replace `YOUR-ORG` with your GitHub org/username.
6. Save and publish.

---

## Ongoing maintenance

| Task | What to do |
|------|-----------|
| **Add a new portfolio company** | Add an entry to `companies.json` with `name`, `domain`, and optional `description`. Push. The next daily run picks it up automatically. |
| **Company not detected** | The ATS slug auto-detection tries several candidates but won't catch everything. Add `"ats"` and `"slug"` fields to the company entry in `companies.json` to override (see below). |
| **Remove a company** | Delete its entry from `companies.json`. Push. |
| **Force a refresh now** | Go to Actions → Refresh Jobs → Run workflow. |

### Manual ATS override

If a company's board isn't being found automatically, look up their
Greenhouse/Lever/Ashby URL and add the slug:

```json
{
  "name": "Example Co",
  "domain": "example.com",
  "description": "Does cool things",
  "ats": "greenhouse",
  "slug": "exampleco-careers"
}
```

Find the slug from the company's career page URL, e.g.:
- Greenhouse: `boards.greenhouse.io/`**`pika`** → slug is `pika`
- Lever: `jobs.lever.co/`**`bandwidth`** → slug is `bandwidth`
- Ashby: `jobs.ashbyhq.com/`**`linear`** → slug is `linear`

---

## File reference

| File | Purpose |
|------|---------|
| `companies.json` | Source list of 52 SSF portfolio companies |
| `fetch_jobs.py` | ATS auto-detector + aggregator; writes `jobs.json` |
| `requirements.txt` | Python dependency (requests) |
| `jobs.json` | Generated output — do not edit by hand |
| `.github/workflows/refresh_jobs.yml` | Daily GitHub Actions cron job |
| `webflow-embed.html` | Paste into a Webflow Embed element |

---

## Cancelling Getro

Once the new board is live on sarahsmith.fund and you've confirmed it's
working, you can cancel Getro invoice #13695 and the subscription.
The subdomain `jobs.sarahsmith.fund` currently points to Getro; you can
either:
- **Leave it**: let it expire when the subscription ends.
- **Redirect it**: add a Webflow redirect from `jobs.sarahsmith.fund` → the
  new jobs page URL.
