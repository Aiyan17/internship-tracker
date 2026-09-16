import logging
import requests
from typing import List
from job_tracker.filter import JobMatch

logger = logging.getLogger(__name__)


class NtfyNotifier:
    def __init__(self, topic: str, email: str = "", ntfy_url: str = "https://ntfy.sh"):
        self.topic = topic
        self.email = email
        self.ntfy_url = ntfy_url.rstrip("/")

    def format_batch(self, matches: List[JobMatch], batch_num: int = 1, total_batches: int = 1) -> str:
        if not matches:
            return ""

        header_str = f"🎓 Found {len(matches)} new internship match{'es' if len(matches) > 1 else ''}"
        if total_batches > 1:
            header_str += f" (Batch {batch_num}/{total_batches})"
        header_str += ":\n"

        lines = [header_str]
        for match in matches:
            resume_str = f" | 📄 Resume: {match.resume_tag.upper()}" if match.resume_tag else ""
            warning_str = ""
            if match.visa_warning:
                flags = ", ".join(match.visa_flags) if match.visa_flags else "Citizenship/ITAR restriction"
                warning_str = f"\n  ⚠️ Warning: Mentions {flags}"

            lines.append(
                f"• {match.company}: {match.title}{resume_str}\n"
                f"  📍 {match.location}\n"
                f"  🔗 {match.url}"
                f"{warning_str}\n"
            )
        return "\n".join(lines)

    def send_notification(self, matches: List[JobMatch], dry_run: bool = False, max_batch_size: int = 8) -> List[JobMatch]:
        """
        Sends notifications in batches to respect the 4KB message limit.
        Returns the list of JobMatch objects that were successfully notified.
        """
        if not matches:
            logger.info("No new matches to notify.")
            return []

        if max_batch_size < 1:
            raise ValueError("max_batch_size must be positive")

        # Reserve the largest possible batch label when measuring UTF-8 bytes.
        # A fixed number of jobs does not guarantee a message fits ntfy's limit.
        batches = []
        batch = []
        for match in matches:
            candidate = batch + [match]
            size = len(self.format_batch(candidate, len(matches), len(matches)).encode("utf-8"))
            if batch and (len(candidate) > max_batch_size or size > 4096):
                batches.append(batch)
                batch = []
            if len(self.format_batch([match], len(matches), len(matches)).encode("utf-8")) > 4096:
                logger.error("Job %s/%s exceeds the notification byte limit; leaving it unseen.", match.company, match.job_id)
                continue
            batch.append(match)
        if batch:
            batches.append(batch)

        if dry_run:
            print("\n" + "=" * 50)
            print(" [DRY RUN] Notification message that would be sent to ntfy.sh:")
            print("=" * 50)
            # Preview in batches
            for idx, batch in enumerate(batches, start=1):
                print(self.format_batch(batch, batch_num=idx, total_batches=len(batches)))
            print("=" * 50 + "\n")
            return [match for batch in batches for match in batch]

        if not self.topic:
            logger.warning("No ntfy_topic specified. Skipping push notification.")
            return []

        # Split into batches to prevent exceeding 4KB message limits
        successful_matches: List[JobMatch] = []

        for idx, batch in enumerate(batches, start=1):
            message = self.format_batch(batch, batch_num=idx, total_batches=len(batches))
            target_endpoint = f"{self.ntfy_url}/{self.topic}"
            headers = {
                "Title": f"{len(batch)} New Internship Match{'es' if len(batch) > 1 else ''} ({idx}/{len(batches)})",
                "Priority": "default",
                "Tags": "mortar_board,briefcase",
                "Markdown": "yes"
            }

            try:
                response = requests.post(target_endpoint, data=message.encode("utf-8"), headers=headers, timeout=15)
                if response.status_code == 200:
                    logger.info(f"Successfully sent batch {idx}/{len(batches)} ({len(batch)} jobs)")
                    successful_matches.extend(batch)
                else:
                    logger.error(f"Failed to send batch {idx}. Status {response.status_code}")
            except Exception as e:
                logger.error("Error sending ntfy notification batch %s: %s", idx, type(e).__name__)

        return successful_matches
