import logging
from typing import List
from job_tracker.adapters.base import BaseAdapter, RawJob

logger = logging.getLogger(__name__)


class WorkdayAdapter(BaseAdapter):
    """
    Adapter for companies using Workday ATS (CXS API).
    Endpoints:
      POST https://<subdomain>/wday/cxs/<tenant>/<client_path>/jobs
      GET  https://<subdomain>/wday/cxs/<tenant>/<client_path>/job/<job_slug>
    """

    def fetch_jobs(self) -> List[RawJob]:
        subdomain = self.kwargs.get("subdomain")
        client_path = self.kwargs.get("client_path", "External")
        tenant = self.kwargs.get("tenant", subdomain.split(".")[0] if subdomain else "")

        if not subdomain:
            logger.error(f"[{self.company_name}] Missing 'subdomain' in config.")
            return []

        api_url = f"https://{subdomain}/wday/cxs/{tenant}/{client_path}/jobs"
        jobs: List[RawJob] = []
        limit = 20
        max_jobs_to_fetch = 60  # Cap pagination for safety

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Query for intern/coop keywords
        search_terms = ["intern", "co-op"]
        role_keywords = ["intern", "internship", "co-op", "coop"]

        for search_term in search_terms:
            offset = 0
            while offset < max_jobs_to_fetch:
                payload = {
                    "limit": limit,
                    "offset": offset,
                    "searchText": search_term,
                    "appliedFacets": {}
                }

                resp = self.fetch_url(api_url, method="POST", json=payload, headers=headers)
                if not resp:
                    break

                try:
                    data = resp.json()
                except Exception as e:
                    logger.error(f"[{self.company_name}] Failed to parse JSON response: {e}")
                    break

                postings = data.get("jobPostings", [])
                if not postings:
                    break

                for item in postings:
                    title = item.get("title", "")
                    external_path = item.get("externalPath", "")
                    location = item.get("locationsText", "")

                    job_id = item.get("bulletFields", [None])[0] if item.get("bulletFields") else ""
                    if not job_id and external_path:
                        job_id = external_path.split("_")[-1] if "_" in external_path else external_path.split("/")[-1]

                    if not job_id:
                        job_id = title

                    job_url = f"https://{subdomain}/en-US/{client_path}{external_path}" if external_path else f"https://{subdomain}"

                    # Only fetch full detail page if title looks relevant to avoid unnecessary network delay
                    description = ""
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in role_keywords) and external_path:
                        detail_api_url = f"https://{subdomain}/wday/cxs/{tenant}/{client_path}{external_path}"
                        detail_resp = self.fetch_url(detail_api_url, method="GET", headers={"Accept": "application/json"})
                        if detail_resp and detail_resp.status_code == 200:
                            try:
                                d_data = detail_resp.json()
                                job_info = d_data.get("jobPostingInfo", {})
                                description = job_info.get("jobDescription", "")
                                if not location and job_info.get("location"):
                                    location = job_info.get("location")
                            except Exception as e:
                                logger.debug(f"[{self.company_name}] Detail parse error for {job_id}: {e}")

                    jobs.append(RawJob(
                        job_id=job_id,
                        title=title,
                        location=location,
                        url=job_url,
                        description=description
                    ))

                total = data.get("total", 0)
                offset += limit
                if offset >= total:
                    break

        # Deduplicate raw jobs by job_id
        seen_ids = set()
        unique_jobs = []
        for j in jobs:
            if j.job_id not in seen_ids:
                seen_ids.add(j.job_id)
                unique_jobs.append(j)

        logger.info(f"[{self.company_name}] Fetched {len(unique_jobs)} candidate postings via Workday API.")
        return unique_jobs
