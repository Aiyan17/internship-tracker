# 🎓 Career Internship Watcher & Mobile Notifier

Automated Python tool that watches target company career portals for new hardware, analog, embedded, PCB, FPGA, power, and electrical engineering internship postings. It filters roles by location, flags visa/ITAR requirements (for F-1 visa candidates), deduplicates seen jobs in SQLite, and sends instant push notifications directly to your phone and laptop via **ntfy.sh**.

---

## Key Features & Fixes

- 🏢 **Multi-ATS Support**: Workday, Greenhouse, Lever, Eightfold, Phenom/custom JSON, Oracle Candidate Experience (TI), and public Avature pages (Siemens).
- 🎯 **Precision Filtering**: Matches titles containing `intern`, `internship`, `co-op` on regex word boundaries (`\b`).
- ⚡ **Domain & Resume Tagging**: Automatically tags each match with its recommended resume version (`📄 Resume: POWER`, `📄 Resume: SEMICONDUCTOR`, or `📄 Resume: HARDWARE`).
- 📍 **Location Filtering**: US country labels and city/state pairs such as `Austin, TX` and `Santa Clara, California`, plus the configured Remote keyword.
- ⚠️ **Expanded Visa & ITAR Warning Flagging**: Scans postings for restrictions (`U.S. Citizen`, `Permanent Resident`, `Green Card`, `Without Sponsorship`, `Security Clearance`, `ITAR`, `Export Control`) and flags them with a warning tag instead of dropping them.
- 📱 **Instant Mobile & Laptop Push Alerts**: Direct summary notifications sent to your iOS/Android phone and desktop browser via [ntfy.sh](https://ntfy.sh) with 1-click application links.
- 📦 **4KB Message Batching**: Measures UTF-8 bytes, not job count. Oversized individual jobs are reported and left unseen rather than truncated. HTTP headers use ASCII while message bodies support Unicode.
- 🔒 **Transaction Safety**: Only records jobs in SQLite after notification delivery succeeds.
- 💾 **SQLite State Persistence**: Tracks seen job IDs in `job_state.db` to prevent duplicate alerts.
- 📊 **Scraper Health Summary**: HTTP errors, unexpected responses, and incomplete pagination are failures, not empty job boards. A failed source or delivery makes the process exit with status 1 while other companies continue.
- 🤖 **Automated Daily Scheduling**: Configured for GitHub Actions daily cron runs (runs even when your computer is powered off).
- 🧪 **Dry-Run Mode**: Test fetching and filtering without sending notifications or mutating state.

---

## Target Companies

Includes **94 configured companies across seven categories**. Inclusion is not a guarantee that each career endpoint is still valid; check the health summary after every run.

1. **Power & Analog Semiconductors** (`resume: POWER`)
2. **Power Conversion & Energy Systems** (`resume: POWER`)
3. **Digital Semiconductors & Compute** (`resume: SEMICONDUCTOR`)
4. **Fabs, Memory & Storage** (`resume: SEMICONDUCTOR`)
5. **Semiconductor Equipment & Test** (`resume: SEMICONDUCTOR`)
6. **Embedded, Consumer & Industrial Systems** (`resume: HARDWARE`)
7. **Medical Device Engineering** (`resume: HARDWARE`)

---

## Quick Setup

### 1. Local Prerequisites
- Python 3.9+
- Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configure ntfy.sh on Your Laptop & Phone
1. **Laptop Browser**: Open **`https://ntfy.sh/your_topic_name`** in Chrome, Safari, or Edge.
2. **Phone**: Install the free **ntfy** app ([iOS](https://apps.apple.com/app/ntfy/id1625396386) or [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy)) and subscribe to your topic name.
3. Choose a **new, hard-to-guess topic** and set it as an environment variable. The previously committed topic is public; do not reuse it or commit your replacement.
```bash
export NTFY_TOPIC="your_topic_name"
```

For PowerShell, use `$env:NTFY_TOPIC = "your_topic_name"` instead. Live runs fail before scraping if no topic is configured. Dry runs do not require a topic. The legacy `email` field is retained for compatibility but does not send email; delivery is through ntfy only.

---

## Local Usage

### Dry-Run Mode (Preview matches without notifying or saving state)
```bash
python main.py --dry-run
```

### Test a Specific Company
```bash
python main.py --dry-run --company "Micron Technology"
python main.py --dry-run --company NVIDIA
python main.py --dry-run --company Medtronic
```

### Live Run (Saves seen jobs to SQLite & sends ntfy alerts)
```bash
python main.py
```

`--company` uses the full configured name, ignoring case. `--verbose` enables diagnostic logs. `--config PATH` selects another configuration. Dry runs use existing deduplication state but do not create or change the database or send notifications. `JOB_DB_PATH` overrides the database path.

## Matching and source limitations

The title must contain a whole role keyword. It must also contain one technical keyword, or the normalized description must contain two distinct technical keywords. Visa warnings are keyword hints, not eligibility determinations. A city without a state/country is not guessed; the `remote` keyword admits remote postings even if they have geographic restrictions, so read the original posting.

SiFive now uses Workday's `sifivecareers` board, TI uses Oracle's public Candidate Experience API, and Siemens uses its public Avature search/detail pages. Workday and Oracle paginate up to 100 pages per query; Avature up to 500. A company can override `max_pages`; reaching a limit is a visible failure, not a claim of complete coverage. Siemens can take several minutes because its site returns six jobs per page.

Eightfold and Phenom retain their existing single-page queries and require site-specific validation before relying on complete coverage. Other configured endpoints may also need updating as companies change systems. Requests remain paced and checked against robots.txt; blocked requests are reported as failures.

---

## Automated Daily Runs via GitHub Actions

This repository includes a pre-configured GitHub Actions workflow in `.github/workflows/daily_check.yml`.

### Setup GitHub Actions:
1. Push this repository to GitHub.
2. In your GitHub repository, go to **Settings > Secrets and variables > Actions**.
3. Add a New Repository Secret:
   - **Name**: `NTFY_TOPIC`
   - **Secret**: `your_ntfy_topic_name`
4. Merge the workflow into the default branch and enable Actions. It runs **daily at 14:00 UTC**; GitHub may delay scheduled runs.
5. Select **Daily Internship Watcher → Run workflow** for a manual run. The `dry_run` option defaults to true; disable it to send notifications.

Scheduled publishing is guarded off on forks, though forks can run manually. CI tests run separately on pushes and pull requests without notification secrets or live career-site requests.

The daily workflow stores `.state/job_state.db` in the Actions cache, including successful deliveries from runs where another source failed. Runs are serialized and require only read access to repository contents; no binary database commits are pushed to `main`. Each run uploads a seven-day log artifact for diagnostics.

**Persistence limitation:** GitHub can evict caches. Losing state causes existing matching jobs to be alerted again. Use durable external storage if stronger guarantees are required. Locally, `job_state.db` remains the default. Failed notification batches stay unseen for retry; a crash after delivery but before saving can still cause a duplicate alert.

## Tests

```sh
python -m unittest discover -s tests -v
```

The tests cover real HTTP delivery against a local server, Unicode/byte limits, partial delivery failures, retry/deduplication, read-only dry runs, filters, source errors, and adapter pagination. They send no external notifications.

---

## License

MIT License.
