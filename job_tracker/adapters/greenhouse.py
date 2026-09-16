import logging
import re
from typing import List
from job_tracker.adapters.base import AdapterError, BaseAdapter, RawJob

logger = logging.getLogger(__name__)


class GreenhouseAdapter(BaseAdapter):
    """
    Adapter for companies using Greenhouse ATS.
    Endpoint: GET https://boards-api.greenhouse.io/v1/boards/<board_token>/jobs?content=true
    """

    def fetch_jobs(self) -> List[RawJob]:
        board_token = self.kwargs.get("board_token")
        if not board_token:
            raise AdapterError("Missing 'board_token' in config")

        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        data = self.fetch_json(api_url)
        raw_jobs = self.require_list(data, "jobs")
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
