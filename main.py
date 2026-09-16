import argparse
import logging
import sys
from typing import List, Dict

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


def main(argv=None):
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

    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Starting Internship Watcher (dry_run={args.dry_run})...")

    # Load configuration
    try:
        app_config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return 1

    # Filter target companies if requested
    target_companies = app_config.companies
    if args.company:
        target_name = args.company.lower()
        target_companies = [c for c in target_companies if c.name.lower() == target_name]
        if not target_companies:
            logger.error(f"Company '{args.company}' not found in configuration.")
            return 1

    if not args.dry_run and not app_config.settings.ntfy_topic:
        logger.error("Set NTFY_TOPIC before a live run (or use --dry-run).")
        return 1
    if not target_companies:
        logger.error("No companies configured.")
        return 1

    db = JobDatabase(app_config.settings.db_path, read_only=args.dry_run)
    try:
        return check_companies(app_config, target_companies, db, args.dry_run)
    finally:
        db.close()


def check_companies(app_config, target_companies, db, dry_run):
    job_filter = JobFilter(app_config.filters)
    notifier = NtfyNotifier(app_config.settings.ntfy_topic, email=app_config.settings.email)

    all_new_matches: List[JobMatch] = []
    company_stats: Dict[str, int] = {}
    failed_adapters: List[str] = []

    logger.info(f"Checking {len(target_companies)} companies...")

    for comp in target_companies:
        logger.info(f"--- Checking {comp.name} ({comp.adapter}) ---")
        adapter = None
        try:
            adapter = get_adapter(
                comp.adapter,
                company_name=comp.name,
                user_agent=app_config.settings.user_agent,
                delay_seconds=app_config.settings.request_delay_seconds,
                **comp.extra
            )
            raw_jobs = adapter.fetch_jobs()
            company_stats[comp.name] = len(raw_jobs)
            evaluated = [job_filter.evaluate_job(
                company=comp.name,
                job_id=job.job_id,
                title=job.title,
                location=job.location,
                url=job.url,
                description=job.description,
                resume_tag=comp.extra.get("resume_tag", "")
            ) for job in raw_jobs]
        except Exception as e:
            logger.error(f"[{comp.name}] Error running adapter '{comp.adapter}': {e}. Skipping.")
            failed_adapters.append(comp.name)
            continue
        finally:
            if adapter is not None:
                adapter.session.close()

        company_matches = 0
        seen_in_run = set()
        for match in evaluated:
            if match:
                # Check if already in SQLite DB
                already_seen = db.is_seen(comp.name, match.job_id)
                if not already_seen and match.job_id not in seen_in_run:
                    seen_in_run.add(match.job_id)
                    company_matches += 1
                    all_new_matches.append(match)

        logger.info(f"[{comp.name}] Found {company_matches} new match(es) passing filters.")

    logger.info(f"Total new matches found across all checked companies: {len(all_new_matches)}")

    # Transaction ordering: Send notification FIRST, then mark jobs as seen in SQLite ONLY after send succeeds!
    notification_failed = False
    if all_new_matches:
        successful_matches = notifier.send_notification(all_new_matches, dry_run=dry_run)
        notification_failed = len(successful_matches) != len(all_new_matches)
        if not dry_run:
            marked_count = 0
            for match in successful_matches:
                if db.mark_seen(match.company, match.job_id, match.title, match.url):
                    marked_count += 1
            logger.info(f"Recorded {marked_count} new job(s) in SQLite database state.")
    else:
        logger.info("No new matches found. No notification sent.")

    # Scraper Health Summary Report
    logger.info("=" * 50)
    logger.info("SCRAPER HEALTH SUMMARY")
    logger.info(f"• Total Companies Checked: {len(target_companies)}")
    logger.info(f"• Adapters Failed: {len(failed_adapters)} {failed_adapters if failed_adapters else ''}")
    logger.info(f"• Companies returning 0 jobs: {sum(1 for v in company_stats.values() if v == 0)}")
    logger.info("=" * 50)

    logger.info("Run complete.")
    return 1 if failed_adapters or notification_failed else 0


if __name__ == "__main__":
    sys.exit(main())
