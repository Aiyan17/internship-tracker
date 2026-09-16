from job_tracker.adapters.base import BaseAdapter
from job_tracker.adapters.workday import WorkdayAdapter
from job_tracker.adapters.greenhouse import GreenhouseAdapter
from job_tracker.adapters.lever import LeverAdapter
from job_tracker.adapters.eightfold import EightfoldAdapter
from job_tracker.adapters.phenom import PhenomAdapter
from job_tracker.adapters.oracle import OracleAdapter
from job_tracker.adapters.avature import AvatureAdapter

ADAPTER_REGISTRY = {
    "workday": WorkdayAdapter,
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "eightfold": EightfoldAdapter,
    "phenom": PhenomAdapter,
    "oracle": OracleAdapter,
    "avature": AvatureAdapter,
}

def get_adapter(name: str, **kwargs) -> BaseAdapter:
    adapter_cls = ADAPTER_REGISTRY.get(name.lower())
    if not adapter_cls:
        raise ValueError(f"Unknown adapter type: '{name}'. Available: {list(ADAPTER_REGISTRY.keys())}")
    return adapter_cls(**kwargs)
