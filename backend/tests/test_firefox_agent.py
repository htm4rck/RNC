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


def test_profile_accepts_h2_intro_card_and_accessible_main(driver):
    from app.local_agent.linkedin import read_profile

    load_html(driver, """
        <main hidden><h1>Stale hidden profile</h1></main>
        <div role="main">
          <aside><h1>Another person</h1></aside>
          <section><h2>Marc Demo</h2><p data-anonymize="headline">Python Engineer</p></section>
          <section><div id="about"></div><h2>Acerca de</h2><p>Systems engineer.</p></section>
        </div>
    """)
    fixture = LinkedInFixture(
        driver, "https://www.linkedin.com/in/marc-demo/?isSelfProfile=true"
    )
    profile = read_profile(fixture)
    assert profile["full_name"] == "Marc Demo"
    assert profile["headline"] == "Python Engineer"
    assert profile["url"] == "https://www.linkedin.com/in/marc-demo/"
    assert "Systems engineer." in profile["about"]


def test_profile_accepts_visible_accessible_heading(driver):
    from app.local_agent.linkedin import read_profile

    load_html(driver, """
        <main><div role="heading" aria-level="1">Marc Demo</div>
        <p data-field="headline">Engineer</p></main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    assert read_profile(fixture)["full_name"] == "Marc Demo"


def test_profile_waits_for_name_after_main_already_has_text(driver):
    from app.local_agent.linkedin import read_profile

    load_html(driver, "<main><p>Loading profile...</p></main>")
    driver.execute_script("""
        setTimeout(() => document.querySelector('main').innerHTML =
            '<h1>Marc Demo</h1><p data-field="headline">Engineer</p>', 700);
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    assert read_profile(fixture)["full_name"] == "Marc Demo"


def test_profile_without_name_does_not_capture_about_heading(driver, monkeypatch):
    from app.local_agent import linkedin

    monkeypatch.setattr(linkedin, "PROFILE_WAIT_SECONDS", 0)
    load_html(driver, '<main><section id="about"><h2>About</h2><p>Bio</p></section></main>')
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    with pytest.raises(RuntimeError, match="inspect-profile"):
        linkedin.read_profile(fixture)


def test_profile_diagnostic_excludes_bodies_hidden_headings_and_input_values(driver):
    from app.local_agent.linkedin import inspect_profile

    load_html(driver, """
        <main><section><h2 class="new-profile-heading">Marc Demo</h2></section>
        <h3 hidden>Hidden heading</h3>
        <aside><h2>Private message heading</h2><p>Private message body</p></aside>
        <div role="dialog"><h2>Private dialog</h2></div>
        <section id="about"><h2>About</h2><p>Personal biography</p></section>
        <input type="email" value="private@example.test"></main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    diagnostic = inspect_profile(fixture)
    assert diagnostic["main_found"] is True
    assert diagnostic["name_detected"] is True
    assert diagnostic["headings"][0]["tag"] == "h2"
    assert diagnostic["headings"][0]["text"] == "Marc Demo"
    encoded = json.dumps(diagnostic)
    for private in (
        "Hidden heading", "Private message", "Private dialog", "Personal biography",
        "private@example.test", "<section",
    ):
        assert private not in encoded


def test_profile_diagnostic_handles_missing_main(driver):
    from app.local_agent.linkedin import inspect_profile

    load_html(driver, "<p>Profile layout not loaded</p>")
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    diagnostic = inspect_profile(fixture)
    assert diagnostic["main_found"] is False
    assert diagnostic["name_detected"] is False
    assert diagnostic["headings"] == []


@pytest.mark.parametrize("labels", [
    ("About", "Experience", "Education", "Skills"),
    ("Acerca de", "Experiencia", "Educación", "Conocimientos y aptitudes"),
])
def test_sdui_profile_reads_sections_without_legacy_ids_or_classes(driver, labels):
    from app.local_agent.linkedin import read_profile

    about, experience, education, skills = labels
    load_html(driver, f"""
        <main>
          <section><div id="com.linkedin.sdui.profile.card.refDemoTopcard">
            <section><h2 class="l4jk8d l4jk37">Marc Demo</h2>
            <p class="l4jk8d l4jk33">Senior Software Engineer</p>
            <p>Lima, Peru</p></section></div></section>
          <section><h2>Suggested for you</h2><p>Unrelated suggestions</p></section>
          <section><h2>Analytics</h2><p>123 profile views</p></section>
          <section><h2 class="l4jk8d">{about}</h2><p>I build useful systems.</p></section>
          <section><h2>Activity</h2><p>Unrelated post content</p></section>
          <section><h2>{experience}</h2><h3>Engineer at Example</h3>
            <p>Built Python services.</p></section>
          <section><h2>{education}</h2><p>Example University</p></section>
          <section><h2>{skills}</h2><p>Python</p><p>PostgreSQL</p></section>
        </main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    profile = read_profile(fixture, scroll=False)
    assert profile["headline"] == "Senior Software Engineer"
    assert "I build useful systems." in profile["about"]
    assert "Built Python services." in profile["experience"]
    assert "Example University" in profile["education"]
    assert "PostgreSQL" in profile["skills"]
    assert profile["capture_status"] == "captured"
    assert profile["warnings"] == []
    assert profile["field_sources"]["about"] == f"heading:{about}"
    assert "Unrelated" not in json.dumps(profile)
    assert "123 profile views" not in json.dumps(profile)


def test_profile_reads_div_cards_and_accessible_headings_without_section_tags(driver):
    from app.local_agent.linkedin import read_profile

    load_html(driver, """
        <main><h1>Marc Demo</h1><p>Software Engineer</p>
        <div><div role="heading" aria-level="2">About</div><p>My biography.</p></div>
        <div><div role="heading" aria-level="2">Experience</div>
        <h3>Senior Engineer</h3><p>Example Company</p></div>
        <div><h2>Interests</h2><p>Unrelated interests</p></div></main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    profile = read_profile(fixture, scroll=False)
    assert profile["headline"] == "Software Engineer"
    assert "My biography." in profile["about"]
    assert "Example Company" in profile["experience"]
    assert "Unrelated interests" not in json.dumps(profile)
    assert profile["capture_status"] == "partial"
    assert profile["field_status"]["education"] == "not_detected"
    assert "education" in profile["warnings"][0]


@pytest.mark.parametrize("heading,total", [
    ("Skills (64)", 64),
    ("Skills (1,234)", 1234),
    ("Aptitudes (64)", 64),
    ("Conocimientos y aptitudes [64]", 64),
])
def test_counted_skills_heading_is_read_without_claiming_the_full_list(driver, heading, total):
    from app.local_agent.linkedin import read_profile

    load_html(driver, f"""
        <main><section><h2>Marc Demo</h2><p>Solution Architect</p></section>
          <section><h2>About</h2><p>Biography</p></section>
          <section><h2>Experience</h2><p>Example Company</p></section>
          <section><h2>Education</h2><p>Example University</p></section>
          <section><h2>{heading}</h2>
            <div id="com.linkedin.sdui.profile.skill(demo, 20)">Python</div>
            <div id="com.linkedin.sdui.profile.skill(demo, 20)-divider">Divider</div>
            <div id="com.linkedin.sdui.profile.skill(demo, 21)">Microsoft Azure</div>
            <button>Show all {total} skills</button>
          </section>
          <section><h2>Interests</h2><p>Unrelated content</p></section>
        </main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    profile = read_profile(fixture, scroll=False)
    assert "Python" in profile["skills"]
    assert "Microsoft Azure" in profile["skills"]
    assert "Unrelated content" not in profile["skills"]
    assert profile["field_status"]["skills"] == "captured"
    assert profile["section_counts"]["skills"] == {"reported": total, "rendered": 2}
    assert profile["capture_status"] == "partial"
    assert profile["capture_scope"] == "rendered_overview"
    assert profile["incomplete_sections"] == ["skills"]
    assert str(total) in profile["warnings"][0]


def test_counted_skills_heading_with_no_entries_does_not_count_as_skill_content(driver):
    from app.local_agent.linkedin import read_profile

    load_html(driver, """
        <main><section><h2>Marc Demo</h2><p>Engineer</p></section>
        <section id="skills"><h2>Skills (64)</h2></section></main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    profile = read_profile(fixture, scroll=False)
    assert profile["skills"] == ""
    assert profile["field_status"]["skills"] == "not_detected"
    assert profile["section_counts"]["skills"]["reported"] == 64


def test_last_section_stays_within_its_card_before_lower_sections_have_loaded(driver):
    from app.local_agent.linkedin import read_profile

    load_html(driver, """
        <main><section><h2>Marc Demo</h2><p>Solution Architect</p></section>
          <section><h2>Experience</h2><p>Example Company</p>
            <p>Designed enterprise platforms.</p>
            <footer><p>Nested footer noise</p></footer>
          </section>
          <div><p>LinkedIn Corporation © 2026</p><p>Questions?</p>
            <p>Visit our Help Center.</p><p>Recommendation transparency</p></div>
          <div role="contentinfo"><h2>Footer heading</h2><p>Manage privacy</p></div>
        </main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    profile = read_profile(fixture, scroll=False)
    assert profile["experience"] == (
        "Experience\nExample Company\nDesigned enterprise platforms."
    )
    for noise in ("footer", "Corporation", "Questions?", "Help Center", "transparency", "privacy"):
        assert noise not in profile["experience"]


def test_profile_with_only_name_does_not_return_success(driver):
    from app.local_agent.linkedin import read_profile

    load_html(driver, "<main><section><h2>Marc Demo</h2></section></main>")
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    with pytest.raises(RuntimeError, match="no se guardó"):
        read_profile(fixture, scroll=False)


def test_lazy_sections_are_captured_and_original_page_scroll_is_restored(driver):
    from app.local_agent.linkedin import read_profile

    load_html(driver, """
        <style>body {margin:0} main {min-height:2400px}</style>
        <main><section><h2>Marc Demo</h2><p>Software Engineer</p></section>
          <section><h2>About</h2><p>I build services.</p></section>
          <section><h2>Experience</h2><p>Example Company</p></section>
          <div><p>LinkedIn Corporation © 2026</p><p>Visit our Help Center.</p></div>
        </main>
        <script>
          window.addEventListener('scroll', () => {
            if (window.scrollY > 350 && !document.querySelector('#loaded')) {
              document.querySelector('main').insertAdjacentHTML('beforeend',
                '<div id="loaded"><section><h2>Education</h2><p>Example University</p></section>'
                + '<section><h2>Skills</h2><p>Python</p></section></div>');
            }
          });
        </script>
    """)
    driver.execute_script("window.scrollTo({top:100, behavior:'instant'});")
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    profile = read_profile(fixture)
    assert profile["capture_status"] == "captured"
    assert "Example University" in profile["education"]
    assert "Python" in profile["skills"]
    assert "Corporation" not in profile["experience"]
    assert "Help Center" not in profile["experience"]
    assert driver.execute_script("return window.scrollY") == 100


def test_internal_scroll_and_virtualized_header_preserve_earlier_fields(driver):
    from app.local_agent.linkedin import read_profile

    load_html(driver, """
        <main style="height:300px; overflow-y:auto">
          <section id="intro"><h2>Marc Demo</h2><p>Software Engineer</p></section>
          <section><h2>About</h2><p>I build services.</p></section>
          <section><h2>Experience</h2><p>Example Company</p></section>
          <div style="height:1000px"></div>
        </main>
        <script>
          const main = document.querySelector('main');
          main.addEventListener('scroll', () => {
            if (main.scrollTop > 150 && !document.querySelector('#loaded')) {
              document.querySelector('#intro').remove();
              main.insertAdjacentHTML('beforeend',
                '<div id="loaded"><section><h2>Education</h2><p>Example University</p></section>'
                + '<section><h2>Skills</h2><p>Python</p></section></div>');
            }
          });
        </script>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/in/marc-demo/")
    profile = read_profile(fixture)
    assert profile["full_name"] == "Marc Demo"
    assert profile["headline"] == "Software Engineer"
    assert "Example University" in profile["education"]
    assert "Python" in profile["skills"]
    assert driver.execute_script("return document.querySelector('main').scrollTop") == 0


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
