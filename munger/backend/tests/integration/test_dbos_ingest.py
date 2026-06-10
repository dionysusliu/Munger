from app.core.config import get_settings
from app.runtime.dbos_app import get_dbos, launch_dbos, destroy_dbos


def test_get_dbos_is_idempotent_and_launches():
    settings = get_settings()
    d1 = get_dbos(settings)
    d2 = get_dbos(settings)
    assert d1 is d2  # singleton
    launch_dbos(settings)  # must not raise against test Postgres
    destroy_dbos()
