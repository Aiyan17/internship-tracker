import logging
from typing import List
from job_tracker.adapters.base import BaseAdapter, RawJob

logger = logging.getLogger(__name__)


class EightfoldAdapter(BaseAdapter):
    """
    Adapter for companies using Eightfold AI ATS (e.g., Siemens).
    Endpoint: GET https://<domain>/api/apply/v2/jobs?start=0&num=50&query=intern
    """

    def fetch_jobs(self) -> List[RawJob]:
        domain = self.kwargs.get("domain")
        if not domain:
            logger.error(f"[{self.company_name}] Missing 'domain' in config.")
            return []

        results: List[RawJob] = []
        queries = ["intern", "co-op"]

        for query in queries:
            api_url = f"https://{domain}/api/apply/v2/jobs?start=0&num=50&query={query}"
            resp = self.fetch_url(api_url, method="GET")
            if not resp:
                continue

            try:
                data = resp.json()
            except Exception as e:
                logger.error(f"[{self.company_name}] Failed to parse Eightfold JSON: {e}")
                continue

            positions = data.get("positions", [])
            for item in positions:
                job_id = str(item.get("id", item.get("position_id", "")))
                title = item.get("name", item.get("title", ""))
                location = item.get("location", "")
                url = item.get("canonical_url", f"https://{domain}/careers/job/{job_id}")
                description = item.get("job_description", "")

                results.append(RawJob(
                    job_id=job_id,
                    title=title,
                    location=location,
                    url=url,
                    description=description
                ))

        # Deduplicate
        seen_ids = set()
        unique_results = []
        for r in results:
            if r.job_id not in seen_ids:
                seen_ids.add(r.job_id)
                unique_results.append(r)

        logger.info(f"[{self.company_name}] Fetched {len(unique_results)} candidate postings via Eightfold API.")
        return unique_results
