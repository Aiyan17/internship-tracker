import logging
import re
from typing import List
from job_tracker.adapters.base import AdapterError, BaseAdapter, RawJob

logger = logging.getLogger(__name__)


class PhenomAdapter(BaseAdapter):
    """
    Adapter for companies using Phenom People or custom JSON career endpoints (e.g., TI).
    Endpoints commonly: GET/POST https://<domain>/api/jobs?keywords=intern
    """

    def fetch_jobs(self) -> List[RawJob]:
        site_url = self.kwargs.get("site_url", "").rstrip("/")
        api_url = self.kwargs.get("api_url")

        if not site_url and not api_url:
            raise AdapterError("Missing 'site_url' or 'api_url' in config")

        if not api_url:
            api_url = f"{site_url}/api/jobs"

        results: List[RawJob] = []
        search_terms = ["intern", "co-op"]

        for term in search_terms:
            target = f"{api_url}?keywords={term}&size=50"
            data = self.fetch_json(target)

            jobs_data = []
            if isinstance(data, dict):
                jobs_data = data.get("jobs", data.get("data", data.get("positions")))
            elif isinstance(data, list):
                jobs_data = data
            else:
                raise AdapterError("Unexpected Phenom response shape")
            if not isinstance(jobs_data, list):
                raise AdapterError("Phenom response is missing a jobs array")

            for item in jobs_data:
                if not isinstance(item, dict):
                    continue
                job_id = str(item.get("jobId", item.get("id", item.get("reqId", ""))))
                title = item.get("title", item.get("name", ""))
                location = item.get("location", item.get("city", ""))
                url = item.get("url", item.get("applyUrl", f"{site_url}/job/{job_id}"))
                description = item.get("description", item.get("summary", ""))

                if job_id and title:
                    results.append(RawJob(
                        job_id=job_id,
                        title=title,
                        location=location,
                        url=url,
                        description=description
                    ))

        # Deduplicate
        seen = set()
        unique = []
        for r in results:
            if r.job_id not in seen:
                seen.add(r.job_id)
                unique.append(r)

        logger.info(f"[{self.company_name}] Fetched {len(unique)} candidate postings via Phenom/Custom API.")
        return unique
