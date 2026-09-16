"""Oracle Candidate Experience public job search, used by Texas Instruments."""
from urllib.parse import quote

from job_tracker.adapters.base import AdapterError, BaseAdapter, RawJob
from job_tracker.filter import has_word


class OracleAdapter(BaseAdapter):
    def fetch_jobs(self):
        api_base = self.kwargs.get("api_base", "").rstrip("/")
        site_url = self.kwargs.get("site_url", "").rstrip("/")
        site = self.kwargs.get("site_number", "CX")
        if not api_base or not site_url:
            raise AdapterError("Oracle requires api_base and site_url")
        results = {}
        page_size = 50
        for term in self.kwargs.get("search_terms", ["intern", "co-op"]):
            for page in range(int(self.kwargs.get("max_pages", 100))):
                data = self.fetch_json(
                    f"{api_base}/recruitingCEJobRequisitions",
                    params={"onlyData": "true", "expand": "requisitionList",
                            "finder": f"findReqs;siteNumber={site},keyword={term},limit={page_size},offset={page * page_size}"},
                )
                items = self.require_list(data, "items")
                if not items:
                    raise AdapterError("Oracle response has no search result metadata")
                postings = self.require_list(items[0], "requisitionList")
                for item in postings:
                    job_id = str(item["Id"])
                    title = item["Title"]
                    if job_id in results:
                        continue
                    description = item.get("ShortDescriptionStr") or ""
                    if any(has_word(title, word) for word in ("intern", "internship", "co-op", "coop")):
                        detail = self.fetch_json(
                            f"{api_base}/recruitingCEJobRequisitionDetails",
                            params={"onlyData": "true", "finder": f'ById;Id="{job_id}",siteNumber={site}'},
                        )
                        details = self.require_list(detail, "items")
                        if not details:
                            raise AdapterError(f"Oracle returned no detail for {job_id}")
                        description = " ".join(details[0].get(key) or "" for key in (
                            "ExternalDescriptionStr", "ExternalQualificationsStr", "ExternalResponsibilitiesStr"))
                    results[job_id] = RawJob(
                        job_id, title, item.get("PrimaryLocation") or "",
                        f"{site_url}/en/sites/{quote(site)}/job/{quote(job_id)}", description,
                    )
                if (page + 1) * page_size >= int(items[0]["TotalJobsCount"]):
                    break
                if not postings:
                    raise AdapterError("Oracle returned an empty page before its reported total")
            else:
                raise AdapterError("Oracle exceeded max_pages; result would be incomplete")
        return list(results.values())
