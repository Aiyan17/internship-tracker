import argparse
import logging
import sys
from typing import List

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from job_tracker.config import load_config
from job_tracker.db import JobDatabase
from job_tracker.filter import JobFilter, JobMatch
from job_tracker.notifier import NtfyNotifier
from job_tracker.adapters import get_adapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")


def main():
    parser = argparse.ArgumentParser(
        description="Watch company career sites for internship postings and send matches to your phone via ntfy.sh."
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration YAML file (default: config.yaml)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print matches to stdout without sending notifications or updating SQLite state"
    )
    parser.add_argument(
        "--company",
        type=str,
        help="Run check for a specific company only (case-insensitive name match)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug level logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Starting Internship Watcher (dry_run={args.dry_run})...")

    # Load configuration
    try:
        app_config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Filter target companies if requested
    target_companies = app_config.companies
    if args.company:
        target_name = args.company.lower()
        target_companies = [c for c in target_companies if c.name.lower() == target_name]
        if not target_companies:
            logger.error(f"Company '{args.company}' not found in configuration.")
            sys.exit(1)

    db = JobDatabase(app_config.settings.db_path)
    job_filter = JobFilter(app_config.filters)
    notifier = NtfyNotifier(app_config.settings.ntfy_topic)

    all_new_matches: List[JobMatch] = []

    logger.info(f"Checking {len(target_companies)} companies...")

    for comp in target_companies:
        logger.info(f"--- Checking {comp.name} ({comp.adapter}) ---")
        try:
            adapter = get_adapter(
                comp.adapter,
                company_name=comp.name,
                user_agent=app_config.settings.user_agent,
                delay_seconds=app_config.settings.request_delay_seconds,
                **comp.extra
            )
            raw_jobs = adapter.fetch_jobs()
        except Exception as e:
            logger.error(f"[{comp.name}] Error running adapter '{comp.adapter}': {e}. Skipping.")
            continue

        company_matches = 0
        for r_job in raw_jobs:
            match = job_filter.evaluate_job(
                company=comp.name,
                job_id=r_job.job_id,
                title=r_job.title,
                location=r_job.location,
                url=r_job.url,
                description=r_job.description
            )
            if match:
                # Check if already in SQLite DB
                already_seen = db.is_seen(comp.name, match.job_id)
                if not already_seen:
                    company_matches += 1
                    all_new_matches.append(match)
                    if not args.dry_run:
                        db.mark_seen(comp.name, match.job_id, match.title, match.url)

        logger.info(f"[{comp.name}] Found {company_matches} new match(es) passing filters.")

    logger.info(f"Total new matches found across all checked companies: {len(all_new_matches)}")

    if all_new_matches:
        notifier.send_notification(all_new_matches, dry_run=args.dry_run)
    else:
        logger.info("No new matches found. No notification sent.")

    db.close()
    logger.info("Run complete.")


if __name__ == "__main__":
    main()
