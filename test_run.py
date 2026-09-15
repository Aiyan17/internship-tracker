import logging
import sys
from job_tracker.adapters.workday import WorkdayAdapter

logging.basicConfig(level=logging.INFO)

print("Starting Workday test for Micron...")
adapter = WorkdayAdapter(
    company_name="Micron",
    subdomain="micron.wd1.myworkdayjobs.com",
    client_path="External",
    delay_seconds=0.1
)

jobs = adapter.fetch_jobs()
print(f"Fetched {len(jobs)} jobs for Micron.")
for j in jobs:
    print(f"Title: {j.title} | Location: {j.location} | URL: {j.url}")
