"""CLI entrypoint: python -m app.worker"""

import asyncio

from app.core.config import get_settings
from app.observability.langsmith_setup import configure_langsmith
from app.worker.runner import run_worker_forever


def main() -> None:
    configure_langsmith(get_settings())
    asyncio.run(run_worker_forever())


if __name__ == "__main__":
    main()
