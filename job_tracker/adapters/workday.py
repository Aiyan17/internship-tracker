import logging
from typing import List
from job_tracker.adapters.base import AdapterError, BaseAdapter, RawJob

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
            raise AdapterError("Missing 'subdomain' in config")

        api_url = f"https://{subdomain}/wday/cxs/{tenant}/{client_path}/jobs"
        jobs: List[RawJob] = []
        limit = 20
        max_jobs_to_fetch = int(self.kwargs.get("max_pages", 100)) * limit
        seen_ids = set()

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

                data = self.fetch_json(api_url, method="POST", json=payload, headers=headers)
                postings = self.require_list(data, "jobPostings")
                total = data.get("total")
                if not isinstance(total, int) or total < 0:
                    raise AdapterError("Workday response has no valid total")
                if not postings:
                    if offset < total:
                        raise AdapterError("Workday returned an empty page before its reported total")
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
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    job_url = f"https://{subdomain}/en-US/{client_path}{external_path}" if external_path else f"https://{subdomain}"

                    # Only fetch full detail page if title looks relevant to avoid unnecessary network delay
                    description = ""
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in role_keywords) and external_path:
                        detail_api_url = f"https://{subdomain}/wday/cxs/{tenant}/{client_path}{external_path}"
                        d_data = self.fetch_json(detail_api_url, headers={"Accept": "application/json"})
                        job_info = d_data.get("jobPostingInfo")
                        if not isinstance(job_info, dict):
                            raise AdapterError(f"Missing Workday jobPostingInfo for {job_id}")
                        description = job_info.get("jobDescription", "")
                        locations = [job_info.get("location") or location]
                        locations.extend(job_info.get("additionalLocations") or [])
                        country = (job_info.get("country") or {}).get("descriptor", "")
                        if country:
                            locations.append(country)
                        location = "; ".join(str(loc) for loc in locations if loc)

                    jobs.append(RawJob(
                        job_id=job_id,
                        title=title,
                        location=location,
                        url=job_url,
                        description=description
                    ))

                offset += limit
                if offset >= total:
                    break
            else:
                raise AdapterError(f"Workday exceeded the {max_jobs_to_fetch}-posting safety limit; increase max_pages")

        # Deduplicate raw jobs by job_id
        seen_ids = set()
        unique_jobs = []
        for j in jobs:
            if j.job_id not in seen_ids:
                seen_ids.add(j.job_id)
                unique_jobs.append(j)

        logger.info(f"[{self.company_name}] Fetched {len(unique_jobs)} candidate postings via Workday API.")
        return unique_jobs
