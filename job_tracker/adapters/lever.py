import logging
from typing import List
from job_tracker.adapters.base import AdapterError, BaseAdapter, RawJob

logger = logging.getLogger(__name__)


class LeverAdapter(BaseAdapter):
    """
    Adapter for companies using Lever ATS.
    Endpoint: GET https://api.lever.co/v0/postings/<site_name>?mode=json
    """

    def fetch_jobs(self) -> List[RawJob]:
        site_name = self.kwargs.get("site_name") or self.kwargs.get("company_slug")
        if not site_name:
            raise AdapterError("Missing 'site_name' in config")

        api_url = f"https://api.lever.co/v0/postings/{site_name}?mode=json"
        data = self.fetch_json(api_url)

        if not isinstance(data, list):
            raise AdapterError("Lever response must be a list")

        results: List[RawJob] = []
        for item in data:
            job_id = str(item.get("id", ""))
            title = item.get("text", "")
            categories = item.get("categories", {})
            location = categories.get("location", "") if isinstance(categories, dict) else ""
            url = item.get("hostedUrl", "")
            description = item.get("descriptionPlain", "") or item.get("description", "")

            results.append(RawJob(
                job_id=job_id,
                title=title,
                location=location,
                url=url,
                description=description
            ))

        logger.info(f"[{self.company_name}] Fetched {len(results)} candidate postings via Lever API.")
        return results
