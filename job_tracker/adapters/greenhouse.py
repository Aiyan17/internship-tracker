import logging
import re
from typing import List
from job_tracker.adapters.base import BaseAdapter, RawJob

logger = logging.getLogger(__name__)


class GreenhouseAdapter(BaseAdapter):
    """
    Adapter for companies using Greenhouse ATS.
    Endpoint: GET https://boards-api.greenhouse.io/v1/boards/<board_token>/jobs?content=true
    """

    def fetch_jobs(self) -> List[RawJob]:
        board_token = self.kwargs.get("board_token")
        if not board_token:
            logger.error(f"[{self.company_name}] Missing 'board_token' in config.")
            return []

        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        resp = self.fetch_url(api_url, method="GET")
        if not resp:
            return []

        try:
            data = resp.json()
        except Exception as e:
            logger.error(f"[{self.company_name}] Failed to parse Greenhouse JSON response: {e}")
            return []

        raw_jobs = data.get("jobs", [])
        results: List[RawJob] = []

        for item in raw_jobs:
            job_id = str(item.get("id", ""))
            title = item.get("title", "")
            location_info = item.get("location", {})
            location = location_info.get("name", "") if isinstance(location_info, dict) else str(location_info)
            url = item.get("absolute_url", f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}")

            content_html = item.get("content", "")
            # Simple HTML tag stripping for text analysis
            description = re.sub(r'<[^>]+>', ' ', content_html)

            results.append(RawJob(
                job_id=job_id,
                title=title,
                location=location,
                url=url,
                description=description
            ))

        logger.info(f"[{self.company_name}] Fetched {len(results)} candidate postings via Greenhouse API.")
        return results
