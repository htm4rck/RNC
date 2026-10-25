import json
import sqlite3
from unittest.mock import Mock

import pytest

from app.local_agent.browser import require_linkedin_page, select_linkedin_tab
from app.local_agent.cli import main
from app.local_agent.store import LocalStore
from app.local_agent.urls import linkedin_url


@pytest.mark.parametrize("value", [
    "https://linkedin.com.evil.example/jobs/view/123/",
    "https://www.linkedin.com@evil.example/jobs/view/123/",
    "https://user:password@linkedin.com/jobs/view/123/",
    "http://www.linkedin.com/jobs/view/123/",
    "https://www.linkedin.com:444/jobs/view/123/",
    "https://www.linkedin.com/feed/",
    "file:///tmp/jobs/view/123/",
    "https://www.linkedin.com/jobs/view/123/../../feed/",
])
def test_urls_reject_external_or_unrelated_pages(value):
    with pytest.raises(ValueError):
        linkedin_url(value, "job")


def test_canonical_urls_remove_tracking_and_keep_resource():
    assert linkedin_url("https://linkedin.com/jobs/view/123?trackingId=secret", "job") == (
        "https://www.linkedin.com/jobs/view/123/"
    )
    assert linkedin_url("https://www.linkedin.com/in/marc-demo/#about", "profile") == (
        "https://www.linkedin.com/in/marc-demo/"
    )


def test_tracking_requires_capture_and_preserves_notes_without_duplicate(tmp_path):
    url = "https://www.linkedin.com/jobs/view/123/"
    with LocalStore(tmp_path) as store:
        with pytest.raises(ValueError, match="Primero captura"):
            store.track(url, "applied")
        store.snapshot("job", {"url": url, "title": "Engineer", "company": "Example"})
        first = store.track(url, "saved", "Consultar salario")
        updated = store.track(url, "preparing")
        assert first["id"] == updated["id"]
        assert updated["notes"] == "Consultar salario"
        assert store.applications("applied") == []
        assert len(store.applications()) == 1
        assert store.db.execute("SELECT COUNT(*) FROM application_events").fetchone()[0] == 2
    with LocalStore(tmp_path) as reopened:
        assert reopened.applications()[0]["status"] == "preparing"


def test_tracking_event_failure_rolls_back_status_update(tmp_path):
    url = "https://www.linkedin.com/jobs/view/123/"
    with LocalStore(tmp_path) as store:
        store.snapshot("job", {"url": url, "title": "Engineer", "company": "Example"})
        store.track(url, "saved")
        store.db.execute("""CREATE TRIGGER fail_event BEFORE INSERT ON application_events
                            BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
        with pytest.raises(sqlite3.IntegrityError):
            store.track(url, "applied")
        assert store.applications()[0]["status"] == "saved"


def test_invalid_state_does_not_modify_tracker(tmp_path):
    with LocalStore(tmp_path) as store:
        with pytest.raises(ValueError, match="Estado"):
            store.track("https://www.linkedin.com/jobs/view/123/", "unknown")
        assert store.applications() == []


def test_cli_tracker_works_without_browser(tmp_path, capsys):
    assert main(["--data-dir", str(tmp_path), "applications"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert main(["--marionette-port", "0", "doctor"]) == 1
    assert "puerto" in capsys.readouterr().err


class Tabs:
    def __init__(self, urls):
        self.urls = urls
        self.current_window_handle = "original"
        self.window_handles = list(urls)
        self.switch_to = Mock()
        self.switch_to.window.side_effect = self.switch
        self.get = Mock()
        self.execute_script = Mock(
            side_effect=lambda script: "complete" if "readyState" in script else True
        )
        self.find_elements = Mock(return_value=[])

    def switch(self, handle):
        self.current_window_handle = handle

    @property
    def current_url(self):
        return self.urls[self.current_window_handle]


def test_selects_matching_tab_without_navigating_other_tabs():
    driver = Tabs({
        "original": "https://example.com/",
        "other": "https://www.linkedin.com/in/marc/",
        "job": "https://www.linkedin.com/jobs/view/123/?trackingId=x",
    })
    assert select_linkedin_tab(driver, "job") == "https://www.linkedin.com/jobs/view/123/"
    assert driver.current_window_handle == "job"
    driver.get.assert_not_called()


def test_profile_selection_prefers_current_tab_over_background_profile():
    driver = Tabs({
        "background": "https://www.linkedin.com/in/another-person/",
        "original": "https://www.linkedin.com/in/marc-demo/?isSelfProfile=true",
    })
    assert select_linkedin_tab(driver, "profile") == "https://www.linkedin.com/in/marc-demo/"
    assert driver.current_window_handle == "original"
    driver.get.assert_not_called()


def test_no_linkedin_tab_restores_original_and_does_not_navigate():
    driver = Tabs({"original": "https://example.com/", "other": "https://bank.example/"})
    with pytest.raises(RuntimeError, match="Abre tu perfil"):
        select_linkedin_tab(driver, "job", "https://www.linkedin.com/jobs/view/123/")
    assert driver.current_window_handle == "original"
    driver.get.assert_not_called()


def test_explicit_url_navigates_only_existing_linkedin_tab():
    driver = Tabs({"original": "https://example.com/", "linkedin": "https://linkedin.com/feed/"})
    driver.get.side_effect = lambda url: driver.urls.update({driver.current_window_handle: url})
    target = "https://www.linkedin.com/jobs/view/123/"
    assert select_linkedin_tab(driver, "job", target) == target
    assert driver.current_window_handle == "linkedin"
    assert driver.urls["original"] == "https://example.com/"
    driver.get.assert_called_once_with(target)


def test_login_redirect_stops_inspection():
    driver = Tabs({"original": "https://www.linkedin.com/checkpoint/challenge/"})
    with pytest.raises(RuntimeError, match="cambió de página"):
        require_linkedin_page(driver, "job")


def test_login_overlay_stops_inspection():
    driver = Tabs({"original": "https://www.linkedin.com/jobs/view/123/"})
    driver.find_elements.return_value = [object()]
    with pytest.raises(RuntimeError, match="verificación"):
        require_linkedin_page(driver, "job")
