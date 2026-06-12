"""CLI entrypoint: python -m app.worker"""

import asyncio

from app.core.config import get_settings
from app.observability.langsmith_setup import configure_langsmith
from app.worker.runner import run_worker_forever


def main() -> None:
    configure_langsmith(get_settings())
    from app.core.database import engine
    from app.observability.otel_setup import setup_otel
    setup_otel("munger-worker", sqlalchemy_engine=engine)
    asyncio.run(run_worker_forever())


if __name__ == "__main__":
    main()
