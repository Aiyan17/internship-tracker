# 🎓 Career Internship Watcher & Notifier

Automated Python tool that watches target company career portals for new hardware, analog, embedded, PCB, FPGA, power, and electrical engineering internship postings. It filters roles by location, flags visa/ITAR requirements (for F-1 visa candidates), deduplicates seen jobs in SQLite, and sends instant push notifications directly to your phone via **ntfy.sh**.

---

## Features

- 🏢 **Multi-ATS Support**: Platform adapters for **Workday**, **Greenhouse**, **Lever**, **Eightfold**, and **Phenom/Custom JSON** endpoints.
- 🎯 **Targeted Filtering**: Matches titles containing `intern`, `internship`, `co-op` and technical keywords (`power`, `analog`, `hardware`, `PCB`, `FPGA`, `embedded`, `electrical`, `battery`, `validation`, `test`).
- 📍 **Location Filtering**: Filters for US & Remote postings.
- ⚠️ **Visa & ITAR Warning Flagging**: Scans postings for restrictions (`U.S. Citizen`, `Security Clearance`, `ITAR`, `Export Control`) and flags them with a warning tag instead of dropping them.
- 📱 **Instant Mobile Push Alerts**: Direct summary notifications sent to your iOS or Android phone via [ntfy.sh](https://ntfy.sh).
- 💾 **SQLite State Persistence**: Tracks seen job IDs to prevent duplicate alerts.
- 🤖 **Automated Daily Scheduling**: Configured for GitHub Actions cron runs (runs even when your computer is powered off).
- 🧪 **Dry-Run Mode**: Test fetching and filtering without sending notifications or mutating state.

---

## Target Companies

The included `config.yaml` comes pre-configured with 14 target semiconductor & medical device engineering companies:
- **Texas Instruments** (Phenom)
- **onsemi** (Workday)
- **Microchip** (Workday)
- **NXP** (Workday)
- **Micron** (Workday)
- **Applied Materials** (Workday)
- **Lam Research** (Workday)
- **KLA** (Workday)
- **AMD** (Workday)
- **Arm** (Workday)
- **Siemens** (Eightfold)
- **Garmin** (Workday)
- **TSMC Arizona** (Greenhouse)
- **Medtronic** (Workday)

---

## Quick Setup

### 1. Local Prerequisites
- Python 3.9+
- Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configure ntfy.sh on Your Phone
1. Install the free **ntfy** app on your phone ([iOS App Store](https://apps.apple.com/app/ntfy/id1625396386) or [Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy)).
2. Open the ntfy app, tap **+ (Subscribe to topic)**.
3. Enter a unique topic name (e.g., `my_internship_alerts_9872`).
4. Update `config.yaml`:
```yaml
settings:
  ntfy_topic: "my_internship_alerts_9872"
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
python main.py --dry-run --company Medtronic
```

### Live Run (Saves seen jobs to SQLite & sends ntfy alerts)
```bash
python main.py
```

---

## Adding New Companies to `config.yaml`

Adding a company is as simple as adding an entry to `config.yaml`:

### Workday Example
```yaml
  - name: "Company Name"
    adapter: "workday"
    subdomain: "company.wd1.myworkdayjobs.com"
    client_path: "External"
```

### Greenhouse Example
```yaml
  - name: "Company Name"
    adapter: "greenhouse"
    board_token: "company_board_id"
```

### Lever Example
```yaml
  - name: "Company Name"
    adapter: "lever"
    site_name: "company_slug"
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
5. You can also manually trigger a run anytime via the **Actions** tab by selecting **Daily Internship Watcher** -> **Run workflow**.

---

## License

MIT License.
