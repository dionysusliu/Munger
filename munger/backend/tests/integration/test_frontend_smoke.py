import os
import re
from urllib.parse import urljoin

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.live_frontend]

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:13000")


def test_frontend_shell_serves_html():
    response = httpx.get(FRONTEND_BASE_URL, timeout=20.0)

    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text

    script_match = re.search(r'<script[^>]+src="([^"]+)"', response.text)
    assert script_match is not None

    bundle_response = httpx.get(urljoin(f"{FRONTEND_BASE_URL}/", script_match.group(1)), timeout=20.0)
    assert bundle_response.status_code == 200
    assert bundle_response.text
