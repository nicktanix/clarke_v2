"""Temporal worker — connects to Temporal server and runs CLARKE background workflows."""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from clarke.jobs.cleanup_jobs import (
    CleanupWorkflow,
    gc_expired_agents_activity,
    prune_stale_edges_activity,
)
from clarke.jobs.clustering_jobs import ClusteringWorkflow, run_clustering_activity
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

TASK_QUEUE = "clarke-jobs"


async def run_worker(temporal_address: str = "localhost:7233") -> None:
    """Start the Temporal worker."""
    client = await Client.connect(temporal_address)
    logger.info("temporal_worker_starting", address=temporal_address, queue=TASK_QUEUE)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ClusteringWorkflow, CleanupWorkflow],
        activities=[
            run_clustering_activity,
            prune_stale_edges_activity,
            gc_expired_agents_activity,
        ],
    )

    await worker.run()


def main() -> None:
    """Entry point for running the worker."""
    import argparse

    parser = argparse.ArgumentParser(description="CLARKE Temporal Worker")
    parser.add_argument("--address", default="localhost:7233", help="Temporal server address")
    args = parser.parse_args()

    asyncio.run(run_worker(args.address))


if __name__ == "__main__":
    main()
