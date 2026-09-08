"""Dedicated process entrypoint for reliable Redis task consumers."""
import logging

from api.utils.task_queue import run_workers


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_workers()
