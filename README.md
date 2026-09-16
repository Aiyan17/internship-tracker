# 🎓 Career Internship Watcher & Mobile Notifier

Automated Python tool that watches target company career portals for new hardware, analog, embedded, PCB, FPGA, power, and electrical engineering internship postings. It filters roles by location, flags visa/ITAR requirements (for F-1 visa candidates), deduplicates seen jobs in SQLite, and sends instant push notifications directly to your phone and laptop via **ntfy.sh**.

---

## Key Features & Fixes

- 🏢 **Multi-ATS Support**: Platform adapters for **Workday** (CXS API), **Greenhouse** (v1 API), **Lever** (JSON API), **Eightfold** (v2 API), and **Phenom/Custom JSON** endpoints.
- 🎯 **Precision Filtering**: Matches titles containing `intern`, `internship`, `co-op` on regex word boundaries (`\b`).
- ⚡ **Domain & Resume Tagging**: Automatically tags each match with its recommended resume version (`📄 Resume: POWER`, `📄 Resume: SEMICONDUCTOR`, or `📄 Resume: HARDWARE`).
- 📍 **Location Filtering**: Strict regex word boundary matching for US & Remote postings.
- ⚠️ **Expanded Visa & ITAR Warning Flagging**: Scans postings for restrictions (`U.S. Citizen`, `Permanent Resident`, `Green Card`, `Without Sponsorship`, `Security Clearance`, `ITAR`, `Export Control`) and flags them with a warning tag instead of dropping them.
- 📱 **Instant Mobile & Laptop Push Alerts**: Direct summary notifications sent to your iOS/Android phone and desktop browser via [ntfy.sh](https://ntfy.sh) with 1-click application links.
- 📦 **4KB Message Batching**: Automatically chunks notifications into small batches so large runs never get truncated or dropped.
- 🔒 **Transaction Safety**: Only records jobs in SQLite after notification delivery succeeds.
- 💾 **SQLite State Persistence**: Tracks seen job IDs in `job_state.db` to prevent duplicate alerts.
- 📊 **Scraper Health Summary**: Logs adapter execution stats, jobs returned per company, and flags failing scrapers.
- 🤖 **Automated Daily Scheduling**: Configured for GitHub Actions daily cron runs (runs even when your computer is powered off).
- 🧪 **Dry-Run Mode**: Test fetching and filtering without sending notifications or mutating state.

---

## Target Companies

Includes **100+ target semiconductor, hardware, power, automotive, and medical device companies** organized across 8 categories:

1. **Power & Analog Semiconductors** (`resume: POWER`)
2. **Power Conversion & Energy Systems** (`resume: POWER`)
3. **Digital Semiconductors & Compute** (`resume: SEMICONDUCTOR`)
4. **Fabs, Memory & Storage** (`resume: SEMICONDUCTOR`)
5. **Semiconductor Equipment & Test** (`resume: SEMICONDUCTOR`)
6. **PCB, Interconnect & Components** (`resume: HARDWARE`)
7. **Embedded, Consumer & Industrial Systems** (`resume: HARDWARE`)
8. **Medical Device Engineering** (`resume: HARDWARE`)

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
3. Set your topic as an environment variable or update `config.yaml`:
```bash
export NTFY_TOPIC="your_topic_name"
```

---

## Local Usage

### Dry-Run Mode (Preview matches without notifying or saving state)
```bash
python main.py --dry-run
```

### Test a Specific Company
```bash
python main.py --dry-run --company Micron
python main.py --dry-run --company NVIDIA
python main.py --dry-run --company Medtronic
```

### Live Run (Saves seen jobs to SQLite & sends ntfy alerts)
```bash
python main.py
```

---

## Automated Daily Runs via GitHub Actions

This repository includes a pre-configured GitHub Actions workflow in `.github/workflows/daily_check.yml`.

### Setup GitHub Actions:
1. Push this repository to GitHub.
2. In your GitHub repository, go to **Settings > Secrets and variables > Actions**.
3. Add a New Repository Secret:
   - **Name**: `NTFY_TOPIC`
   - **Secret**: `your_ntfy_topic_name`
4. The workflow will run automatically **every day at 14:00 UTC** and automatically commit state updates back to `job_state.db`.

---

## License

MIT License.
