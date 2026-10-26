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


@pytest.mark.parametrize("description_label", ["About the job", "Acerca del empleo"])
def test_sdui_job_reads_paragraph_title_company_link_and_semantic_description(driver, description_label):
    from app.local_agent.linkedin import read_job

    load_html(driver, f"""
        <main>
          <section><a href="https://www.linkedin.com/company/example/">Example Company</a>
            <p class="l4jk33" style="font-size:24px">Solution Architect</p>
            <p>Peru</p><button aria-label="Easy Apply to this job">Easy Apply</button>
          </section>
          <section><h2>Use AI to assess how you fit</h2><p>Unrelated AI content</p></section>
          <section><h2>{description_label}</h2><p>Design enterprise integrations.</p>
            <p>Python and Azure required.</p></section>
          <section><h2>About the company</h2><p>Unrelated company description</p></section>
          <footer>Footer noise</footer>
        </main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    job = read_job(fixture)
    assert job["title"] == "Solution Architect"
    assert job["company"] == "Example Company"
    assert job["description"] == "Design enterprise integrations.\nPython and Azure required."
    assert job["field_sources"]["description"] == f"heading:{description_label}"
    assert job["field_sources"]["title"] == "intro-prominent-paragraph"
    assert job["easy_apply"] is True
    assert "Unrelated" not in json.dumps(job)


def test_job_uses_selected_job_link_instead_of_unrelated_headings(driver):
    from app.local_agent.linkedin import read_job

    load_html(driver, """
        <main><section><a href="https://www.linkedin.com/company/example/">Example Company</a>
          <a href="https://www.linkedin.com/jobs/view/4481008368/">Solutions Architect</a></section>
          <section><h2>Use AI to assess how you fit</h2></section>
          <section><h2>About the job</h2><p>Build integration platforms.</p></section>
        </main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    assert read_job(fixture)["title"] == "Solutions Architect"


def test_job_waits_for_description_after_header_has_loaded(driver):
    from app.local_agent.linkedin import read_job

    load_html(driver, '<main><h1>Solution Architect</h1><section id="details"></section></main>')
    driver.execute_script("""
        setTimeout(() => document.querySelector('#details').innerHTML =
            '<h2>About the job</h2><p>Design enterprise systems.</p>', 600);
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    assert read_job(fixture)["description"] == "Design enterprise systems."


def test_job_can_use_browser_title_without_mistaking_section_headings_for_job_title(driver):
    from app.local_agent.linkedin import read_job

    load_html(driver, """
        <title>(3) Solution Architect | Example Company | LinkedIn</title>
        <main><p>Job detail</p><section><h2>Use AI to assess how you fit</h2></section>
          <section><h2>About the job</h2><p>Design systems.</p></section></main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    job = read_job(fixture)
    assert job["title"] == "Solution Architect"
    assert job["company"] == "Example Company"
    assert job["field_sources"]["title"] == "browser-title"


def test_generic_job_search_browser_title_is_not_used_as_job_title(driver, monkeypatch):
    from app.local_agent import linkedin

    monkeypatch.setattr(linkedin, "JOB_WAIT_SECONDS", 0)
    load_html(driver, """
        <title>Jobs in Peru | Search | LinkedIn</title>
        <main><section><h2>Use AI to assess how you fit</h2></section>
          <section><h2>About the job</h2><p>Design systems.</p></section></main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    with pytest.raises(RuntimeError, match="title"):
        linkedin.read_job(fixture)


def test_existing_sdui_application_without_heading_tags_is_recognized_without_click(driver):
    from app.local_agent.linkedin import inspect_application

    load_html(driver, """
        <main><button onclick="window.clickedAgain=true">Easy Apply to this job</button></main>
        <div role="dialog" aria-modal="true" class="l4jlsc l4jlsb">
          <p>Contact info</p>
          <label for="email">Email address</label><input id="email" type="email" value="private@example.test">
          <button onclick="window.nextClicked=true">Next</button>
        </div>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    form = inspect_application(fixture, open_dialog=True)
    assert form["title"] == "Contact info"
    assert form["fields"][0]["label"] == "Email address"
    assert form["fields"][0]["type"] == "email"
    assert form["actions"] == ["Next"]
    assert form["detection"] == "application-labels"
    assert "private@example.test" not in json.dumps(form)
    assert driver.execute_script("return !!window.clickedAgain || !!window.nextClicked") is False


def test_contact_step_without_a_title_uses_question_and_next_button(driver):
    from app.local_agent.linkedin import inspect_application

    load_html(driver, """
        <main>Job detail</main><div role="dialog" class="generated">
          <label>Email address<input type="email" value="private@example.test"></label>
          <label>Country<select><option>Peru</option><option>Chile</option></select></label>
          <button>Next</button>
        </div>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    form = inspect_application(fixture)
    assert form["detection"] == "contact-step"
    assert form["fields"][0]["label"] == "Email address"
    assert form["fields"][1]["label"] == "Country"
    assert form["fields"][1]["options"] == ["Peru", "Chile"]
    assert "private@example.test" not in json.dumps(form)


def test_resume_step_recognizes_hidden_native_file_input_without_reading_its_value(driver):
    from app.local_agent.linkedin import inspect_application

    load_html(driver, """
        <main>Job detail</main><div role="dialog" class="generated-modal">
          <p>Resume</p><label for="resume-upload">Upload resume</label>
          <input id="resume-upload" type="file" style="display:none" accept=".pdf">
          <button>Next</button>
        </div>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    form = inspect_application(fixture)
    assert form["title"] == "Resume"
    assert form["fields"][0] == {
        "label": "Upload resume", "type": "file", "required": False, "options": []
    }
    assert form["submitted"] is False


def test_application_uses_accessible_name_and_hidden_referenced_question_label(driver):
    from app.local_agent.linkedin import inspect_application

    load_html(driver, """
        <main>Job detail</main>
        <span id="app-title" hidden>Apply to Example</span>
        <span id="phone-label" hidden>Phone number</span>
        <div role="dialog" aria-labelledby="app-title">
          <input type="tel" aria-labelledby="phone-label" value="private-phone">
          <button>Next</button>
        </div>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    form = inspect_application(fixture)
    assert form["title"] == "Apply to Example"
    assert form["fields"][0]["label"] == "Phone number"
    assert "private-phone" not in json.dumps(form)


def test_new_generic_form_is_tied_to_the_easy_apply_click(driver):
    from app.local_agent.linkedin import inspect_application

    load_html(driver, """
        <main><button onclick="document.querySelector('[role=dialog]').hidden=false">Easy Apply</button></main>
        <div role="dialog" hidden class="generated-modal">
          <label for="availability">Availability</label><input id="availability" type="text">
          <button onclick="window.sent=true">Submit application</button>
        </div>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    form = inspect_application(fixture, open_dialog=True)
    assert form["fields"][0]["label"] == "Availability"
    assert form["submitted"] is False
    assert driver.execute_script("return !!window.sent") is False


def test_open_unrelated_message_dialog_is_preserved_and_not_reopened(driver):
    from app.local_agent.linkedin import inspect_application

    load_html(driver, """
        <main><button onclick="window.clicked=true">Easy Apply</button></main>
        <div role="dialog"><p>New message</p><label for="message">Message recruiter</label>
          <textarea id="message">Private draft</textarea><button>Send</button></div>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    with pytest.raises(RuntimeError, match="diálogo abierto"):
        inspect_application(fixture, open_dialog=True)
    assert driver.execute_script("return !!window.clicked") is False


def test_job_diagnostic_collects_structure_without_form_values_or_page_bodies(driver):
    from app.local_agent.linkedin import inspect_job

    load_html(driver, """
        <main><h2>Solution Architect</h2><section><h2>About the job</h2>
          <p>Job description body</p></section>
          <a href="https://www.linkedin.com/company/example/">Example</a>
          <button aria-label="Easy Apply to Solution Architect">Easy Apply</button>
          <aside><h2>Private sidebar heading</h2></aside>
        </main>
        <div role="dialog"><h2>Apply to Example</h2>
          <input type="email" value="private@example.test">
          <input type="hidden" value="secret-token">
        </div>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    result = inspect_job(fixture)
    assert result["headings"][0]["text"] == "Solution Architect"
    assert result["buttons"][0]["text"] == "Easy Apply to Solution Architect"
    assert result["dialogs"][0]["field_count"] == 1
    assert result["company_links"] == [{"text": "Example"}]
    encoded = json.dumps(result)
    for private in ("private@example.test", "secret-token", "Job description body", "Private sidebar"):
        assert private not in encoded


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


def preparation_answers():
    from app.local_agent.answers import empty_answers

    answers = empty_answers()
    answers["contact"] = {"email": "person@example.test", "phone_country_code": "+51",
                          "phone_number": "555010123"}
    answers["resume"]["filename"] = "CV_Architect.pdf"
    return answers


def load_preparation_flow(driver, *, title="Solution Architect", screening=False, stall=False,
                          resume_filename="CV_Architect.pdf"):
    countries = ''.join(f'<option>Country {index} (+{1000 + index})</option>' for index in range(110))
    load_html(driver, f"""
        <main><h1>{title}</h1><p data-field="company">Example Company</p>
          <div id="job-details">Design enterprise systems.</div></main>
        <div role="dialog" aria-label="Apply to Example" id="application"></div>
        <script>
          window.sent = false; window.advances = 0; window.chosenResume = null;
          const root = document.querySelector('#application');
          function review() {{
            root.innerHTML = '<h2>Review application</h2>'
              + '<button onclick="window.sent=true">Submit application</button>';
          }}
          function screening() {{
            root.innerHTML = '<h2>Additional questions</h2>'
              + '<label>Years of BIAN experience*<input type="number" required></label>'
              + '<button onclick="review()">Next</button>';
          }}
          function resumes() {{
            root.innerHTML = `<h2>Resume</h2>
              <input type="radio" id="dev" name="cv" checked style="display:none">
              <label for="dev"><p>CV_Developer.pdf</p><p>50 KB</p></label>
              <input type="radio" id="architect" name="cv" style="display:none">
              <label for="architect"><p>{resume_filename}</p><p>60 KB</p></label>
              <input type="file" aria-label="Upload resume" style="display:none">
              <button onclick="window.advances++; window.chosenResume = document.querySelector('#architect').checked ? 'architect' : 'developer';
                {'screening()' if screening else 'review()'}">Next</button>`;
          }}
          root.innerHTML = `<h2>Contact info</h2>
            <label>Email*<select required id="email"><option value=""></option><option>person@example.test</option></select></label>
            <label>Phone country code*<select required id="country"><option value=""></option>
              {countries}<option>Peru (+51)</option><option>Canada (+1)</option><option>United States (+1)</option></select></label>
            <label>Teléfono móvil*<input id="phone" type="tel" pattern="[0-9]{{9}}" required></label>
            <button onclick="window.advances++; {'void 0' if stall else 'resumes()'}">Next</button>`;
        </script>
    """)
    return LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")


def test_prepare_fills_contact_selects_exact_resume_and_stops_before_submission(driver):
    from app.local_agent.applications import prepare_application

    fixture = load_preparation_flow(driver)
    result = prepare_application(fixture, preparation_answers())
    assert result["status"] == "ready_for_review"
    assert result["submitted"] is False
    assert len(result["steps"]) == 2
    assert result["steps"][1]["resume"] == "CV_Architect.pdf"
    assert driver.execute_script("return window.chosenResume") == "architect"
    assert driver.execute_script("return window.advances") == 2
    assert driver.execute_script("return window.sent") is False
    assert "555010123" not in json.dumps(result)


def test_prepare_dry_run_makes_no_changes_or_next_click(driver):
    from app.local_agent.applications import prepare_application

    fixture = load_preparation_flow(driver)
    result = prepare_application(fixture, preparation_answers(), dry_run=True)
    assert result["status"] == "ready"
    assert driver.execute_script("return document.querySelector('#email').value") == ""
    assert driver.execute_script("return document.querySelector('#phone').value") == ""
    assert driver.execute_script("return window.advances") == 0


def test_prepare_missing_required_answer_does_not_partially_modify_contact(driver):
    from app.local_agent.applications import prepare_application

    fixture = load_preparation_flow(driver)
    data = preparation_answers()
    data["contact"]["phone_number"] = None
    result = prepare_application(fixture, data)
    assert result["status"] == "needs_answers"
    assert driver.execute_script("return document.querySelector('#email').value") == ""
    assert driver.execute_script("return window.advances") == 0


def test_prepare_uses_country_option_beyond_first_hundred(driver):
    from app.local_agent.applications import prepare_application
    from app.local_agent.linkedin import inspect_application

    fixture = load_preparation_flow(driver)
    countries = inspect_application(fixture)["fields"][1]["options"]
    assert "Peru (+51)" in countries[100:]
    result = prepare_application(fixture, preparation_answers(), max_steps=1)
    assert result["steps"][0]["blocked"] == []
    assert driver.execute_script("return window.advances") == 1


def test_prepare_ambiguous_country_code_stops_before_changing_fields(driver):
    from app.local_agent.applications import prepare_application

    fixture = load_preparation_flow(driver)
    data = preparation_answers()
    data["contact"]["phone_country_code"] = "+1"
    result = prepare_application(fixture, data)
    assert result["status"] == "needs_answers"
    assert result["steps"][0]["blocked"][0]["reason"] == "option_not_found_or_ambiguous"
    assert driver.execute_script("return window.advances") == 0


def test_prepare_verifies_phone_before_advancing(driver):
    from app.local_agent.applications import prepare_application

    fixture = load_preparation_flow(driver)
    data = preparation_answers()
    data["contact"]["phone_number"] = "123"
    result = prepare_application(fixture, data)
    assert result["status"] == "needs_answers"
    assert any(item["reason"] == "verification_failed" for item in result["steps"][0]["blocked"])
    assert driver.execute_script("return window.advances") == 0


def test_prepare_does_not_use_architect_resume_for_another_job(driver):
    from app.local_agent.applications import prepare_application

    fixture = load_preparation_flow(driver, title="Software Developer")
    result = prepare_application(fixture, preparation_answers())
    assert result["status"] == "needs_answers"
    assert result["steps"][-1]["blocked"][0]["reason"] == "resume_rule_not_applicable_to_job_title"
    assert driver.execute_script("return window.advances") == 1
    assert driver.execute_script("return document.querySelector('#dev').checked") is True


def test_prepare_missing_resume_does_not_select_an_alternative(driver):
    from app.local_agent.applications import prepare_application

    fixture = load_preparation_flow(driver, resume_filename="Another_Architect.pdf")
    result = prepare_application(fixture, preparation_answers())
    assert result["status"] == "needs_answers"
    assert result["steps"][-1]["blocked"][0]["reason"] == "resume_not_found_or_ambiguous"
    assert driver.execute_script("return window.advances") == 1


def test_prepare_duplicate_resume_names_do_not_choose_one_arbitrarily(driver):
    from app.local_agent.applications import prepare_application

    fixture = load_preparation_flow(driver)
    driver.execute_script("resumes(); document.querySelector('label[for=dev] p').textContent = 'CV_Architect.pdf';")
    result = prepare_application(fixture, preparation_answers())
    assert result["status"] == "needs_answers"
    assert result["steps"][0]["blocked"][0]["reason"] == "resume_not_found_or_ambiguous"
    assert driver.execute_script("return window.advances") == 0


def test_prepare_unrecognized_resume_controls_do_not_advance_with_a_default_resume(driver):
    from app.local_agent.applications import prepare_application

    fixture = load_preparation_flow(driver)
    driver.execute_script("resumes(); document.querySelectorAll('input[type=radio]').forEach(e => e.remove());")
    result = prepare_application(fixture, preparation_answers())
    assert result["status"] == "needs_answers"
    assert result["steps"][0]["blocked"][0]["reason"] == "resume_selection_controls_not_recognized"
    assert driver.execute_script("return window.advances") == 0


def test_prepare_stops_at_unknown_screening_question_without_inventing_bian_experience(driver):
    from app.local_agent.applications import prepare_application

    fixture = load_preparation_flow(driver, screening=True)
    result = prepare_application(fixture, preparation_answers())
    assert result["status"] == "needs_answers"
    assert result["steps"][-1]["blocked"][0]["field"] == "Years of BIAN experience*"
    assert driver.execute_script("return window.advances") == 2
    assert driver.execute_script("return document.querySelector('input[type=number]').value") == ""
    assert driver.execute_script("return window.sent") is False


def test_prepare_uses_explicit_answer_for_a_screening_question(driver):
    from app.local_agent.applications import prepare_application

    fixture = load_preparation_flow(driver, screening=True)
    data = preparation_answers()
    data["answers"]["Years of BIAN experience"] = "2"
    result = prepare_application(fixture, data)
    assert result["status"] == "ready_for_review"
    assert driver.execute_script("return window.sent") is False


def test_prepare_does_not_retry_next_when_step_did_not_change(driver, monkeypatch):
    from app.local_agent import applications

    monkeypatch.setattr(applications, "STEP_WAIT_SECONDS", 0)
    fixture = load_preparation_flow(driver, stall=True)
    result = applications.prepare_application(fixture, preparation_answers())
    assert result["status"] == "next_step_not_confirmed"
    assert driver.execute_script("return window.advances") == 1


def test_job_title_rejects_hybrid_link_and_reads_explicit_role_from_description(driver):
    from app.local_agent.linkedin import read_job

    load_html(driver, """
        <main><a href="https://www.linkedin.com/jobs/view/4481008368/">Hybrid</a>
          <section><h2>About the job</h2><p>Buscamos un</p>
          <p>Arquitecto de Soluciones Senior (Banca | BIAN)</p><p>con ganas de trabajar.</p></section>
        </main>
    """)
    fixture = LinkedInFixture(driver, "https://www.linkedin.com/jobs/view/4481008368/")
    result = read_job(fixture)
    assert result["title"] == "Arquitecto de Soluciones Senior (Banca | BIAN)"
    assert result["field_sources"]["title"] == "description-role"
