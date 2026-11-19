import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

from supplierhub.app import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.sqlite"


@pytest.fixture
def client(db_path):
    with TestClient(create_app(db_path)) as service:
        yield service


@pytest.fixture
def live_url(db_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    with subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "supplierhub.app:app", "--no-access-log", "--port", str(port)],
        cwd=ROOT, env={**os.environ, "SUPPLIERHUB_DB": str(db_path)}, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    ) as process:
        try:
            for _ in range(100):
                if process.poll() is not None:
                    pytest.fail(process.stderr.read().decode())
                try:
                    with urlopen(url + "/api/health", timeout=0.3) as response:
                        if response.status == 200:
                            break
                except URLError:
                    time.sleep(0.05)
            else:
                pytest.fail("SupplierHub failed to start.")
            yield url
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        executable = os.environ.get("SUPPLIERHUB_CHROMIUM")
        if not executable and not Path(playwright.chromium.executable_path).is_file():
            executable = shutil.which("chromium")
        browser = playwright.chromium.launch(executable_path=executable)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    yield page
    page.close()
