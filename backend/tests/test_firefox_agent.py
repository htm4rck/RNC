"""Opt-in integration tests: a separate temporary Firefox, never the user's session."""

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from app.local_agent.browser import connected_firefox, firefox_status

pytestmark = pytest.mark.skipif(
    os.environ.get("RCN_FIREFOX_TESTS") != "1",
    reason="Set RCN_FIREFOX_TESTS=1 to run isolated Firefox integration tests.",
)


@pytest.fixture(scope="module")
def firefox_instance():
    assert shutil.which("firefox") and shutil.which("geckodriver")
    # Firefox Snap cannot read the host's /tmp. Use its shared directory for fixtures.
    root = Path.home() / "snap/firefox/common"
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcn-test-", dir=root) as directory:
        profile = Path(directory)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        (profile / "user.js").write_text(
            f'user_pref("marionette.port", {port});\n'
            'user_pref("browser.shell.checkDefaultBrowser", false);\n'
            'user_pref("browser.startup.homepage_override.mstone", "ignore");\n',
            encoding="utf-8",
        )
        with (profile / "firefox.log").open("w") as log:
            process = subprocess.Popen(
                ["firefox", "--headless", "--no-remote", "--profile", str(profile),
                 "--marionette", "about:blank"],
                stdout=log, stderr=log,
            )
            try:
                deadline = time.monotonic() + 25
                while not firefox_status(port)["marionette_listening"]:
                    if process.poll() is not None or time.monotonic() > deadline:
                        pytest.fail((profile / "firefox.log").read_text()[-4000:])
                    time.sleep(0.2)
                yield port, profile, process
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


@pytest.fixture
def driver(firefox_instance):
    port, directory, _ = firefox_instance
    with connected_firefox(port, directory) as browser:
        yield browser


class LinkedInFixture:
    """Exercise real Firefox DOM/scripts with a synthetic resource URL and local HTML."""
    def __init__(self, driver, url):
        self.driver = driver
        self.current_url = url

    def __getattr__(self, name):
        return getattr(self.driver, name)


def load_html(driver, html):
    driver.get("about:blank")
    driver.execute_script("document.open(); document.write(arguments[0]); document.close();", html)


def test_profile_extraction_ignores_unrelated_page_content(driver):
    from app.local_agent.linkedin import read_profile

    load_html(driver, """
        <aside>Secret private message</aside>
        <main><h1>Marc Demo</h1><div class="text-body-medium break-words">Engineer</div>
        <section><div id="about"></div><h2>About</h2><p>I build software.</p></section>
        <section><div id="experience"></div><p>Engineer at Example</p></section>
        <section hidden><div id="education"></div><p>Hidden content</p></section></main>
    """)
    profile = read_profile(LinkedInFixture(driver, "https://www.linkedin.com/in/marc/"))
    assert profile["full_name"] == "Marc Demo"
    assert profile["headline"] == "Engineer"
    assert "I build software." in profile["about"]
    assert "Engineer at Example" in profile["experience"]
    assert profile["education"] == ""
    assert "Secret private message" not in json.dumps(profile)


def test_job_and_application_only_open_and_inspect_visible_step(driver):
    from app.local_agent.linkedin import inspect_application, read_job

    load_html(driver, """
        <script>window.sent = false;</script>
        <main><h1>Senior Engineer</h1><div data-field="company">Example</div>
        <div data-field="location">Remote LATAM</div>
        <div id="job-details">Build Python services.</div>
        <button aria-label="Solicitud sencilla para Senior Engineer"
          onclick="document.querySelector('[role=dialog]').hidden=false">Solicitud sencilla</button>
        </main>
        <div role="dialog" class="jobs-easy-apply-modal" hidden><h2>Apply to Example</h2>
          <label for="phone">Phone</label><input id="phone" type="tel" value="private" required>
          <input type="hidden" value="secret-token">
          <label>Country<select><option>Peru</option><option>Chile</option></select></label>
          <input aria-label="CV" type="file">
          <button onclick="window.sent=true">Enviar solicitud</button>
        </div>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/123/?trackingId=x")
    job = read_job(fixture)
    assert job["company"] == "Example"
    assert job["description"] == "Build Python services."
    assert job["easy_apply"] is True
    with pytest.raises(RuntimeError, match="--open"):
        inspect_application(fixture)
    application = inspect_application(fixture, open_dialog=True)
    assert application["submitted"] is False
    assert application["fields"][0] == {
        "label": "Phone", "type": "tel", "required": True, "options": []
    }
    assert application["fields"][1]["options"] == ["Peru", "Chile"]
    assert "private" not in json.dumps(application)
    assert "secret-token" not in json.dumps(application)
    assert driver.execute_script("return window.sent") is False
    assert inspect_application(fixture)["fields"] == application["fields"]


def test_ambiguous_easy_apply_does_not_click(driver):
    from app.local_agent.linkedin import inspect_application

    load_html(driver, """<main>
        <button onclick="window.clicked=true">Easy Apply</button>
        <button onclick="window.clicked=true">Easy Apply</button></main>""")
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/123/")
    with pytest.raises(RuntimeError, match="único botón"):
        inspect_application(fixture, open_dialog=True)
    assert driver.execute_script("return !!window.clicked") is False


def test_unrelated_dialog_is_not_read_as_application(driver):
    from app.local_agent.linkedin import inspect_application

    load_html(driver, '<main>Job</main><div role="dialog"><h2>Private message</h2></div>')
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/123/")
    with pytest.raises(RuntimeError, match="formulario de Easy Apply"):
        inspect_application(fixture)


def test_disconnect_keeps_firefox_open_and_allows_reconnect(firefox_instance):
    port, directory, process = firefox_instance
    with connected_firefox(port, directory) as browser:
        load_html(browser, "<title>RNC reconnect fixture</title><p>Local content</p>")
    assert process.poll() is None
    with connected_firefox(port, directory) as browser:
        assert browser.title == "RNC reconnect fixture"
        with (
            pytest.raises(RuntimeError, match="Otro agente"),
            connected_firefox(port, directory),
        ):
            pytest.fail("Concurrent browser attachment must be rejected")
