import os
from dataclasses import dataclass, field
from typing import List, Dict, Any
import yaml


@dataclass
class Settings:
    ntfy_topic: str = ""
    email: str = ""
    request_delay_seconds: float = 1.5
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) InternshipWatcher/1.0"
    db_path: str = "job_state.db"


@dataclass
class Filters:
    role_keywords: List[str] = field(default_factory=lambda: ["intern", "internship", "co-op"])
    topic_keywords: List[str] = field(default_factory=lambda: [
        "power", "analog", "hardware", "pcb", "fpga", "electrical",
        "embedded", "battery", "validation", "test"
    ])
    location_include: List[str] = field(default_factory=lambda: ["united states", "us", "usa", "remote"])
    visa_flag_keywords: List[str] = field(default_factory=lambda: [
        "u.s. citizen", "us citizen", "u.s. person", "us person",
        "security clearance", "itar", "export control"
    ])


@dataclass
class CompanyConfig:
    name: str
    adapter: str
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AppConfig:
    settings: Settings
    filters: Filters
    companies: List[CompanyConfig]


def load_config(config_path: str = "config.yaml") -> AppConfig:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    s_data = data.get("settings", {})
    # Prioritize environment variables for NTFY_TOPIC and EMAIL
    topic = os.environ.get("NTFY_TOPIC") or s_data.get("ntfy_topic") or ""
    email = os.environ.get("EMAIL_NOTIFY") or os.environ.get("NOTIFY_EMAIL") or s_data.get("email") or ""

    settings = Settings(
        ntfy_topic=topic,
        email=email,
        request_delay_seconds=float(s_data.get("request_delay_seconds", 1.5)),
        user_agent=s_data.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) InternshipWatcher/1.0"),
        db_path=os.environ.get("JOB_DB_PATH") or s_data.get("db_path", "job_state.db"),
    )

    f_data = data.get("filters", {})
    defaults = Filters()
    filters = Filters(
        role_keywords=[k.lower() for k in f_data.get("role_keywords", defaults.role_keywords)],
        topic_keywords=[k.lower() for k in f_data.get("topic_keywords", defaults.topic_keywords)],
        location_include=[k.lower() for k in f_data.get("location_include", defaults.location_include)],
        visa_flag_keywords=[k.lower() for k in f_data.get("visa_flag_keywords", defaults.visa_flag_keywords)],
    )

    companies = []
    for c in data.get("companies", []):
        c_copy = dict(c)
        name = c_copy.pop("name", "Unknown")
        adapter = c_copy.pop("adapter", "workday")
        companies.append(CompanyConfig(name=name, adapter=adapter, extra=c_copy))

    return AppConfig(settings=settings, filters=filters, companies=companies)
