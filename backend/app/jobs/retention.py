"""Run the retention sweep once, e.g. from cron or an EventBridge schedule on
Lambda where there is no long-lived process for the in-app sweeper:

    python -m app.jobs.retention
"""
import json

from app.logging_setup import configure_logging
from app.services import retention

if __name__ == "__main__":
    configure_logging()
    print(json.dumps(retention.purge_expired()))
