"""Prepare known application steps using verified local answers; stop before submission."""

import re
import unicodedata

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from app.local_agent.application_dom import APPLICATION_DOM
from app.local_agent.browser import require_linkedin_page
from app.local_agent.linkedin import _HELPERS, application_dialogs, inspect_application, read_job
from app.local_agent.urls import linkedin_url

STEP_WAIT_SECONDS = 15
CONTACT_LABELS = {
    "email": {"email", "email address", "correo", "correo electronico"},
    "phone_country_code": {"phone country code", "country code", "codigo de pais", "codigo de pais del telefono"},
    "phone_number": {"mobile phone number", "phone number", "telefono movil", "telefono", "numero de telefono"},
}
ADVANCE_LABELS = {"next", "siguiente", "continue", "continuar", "review", "revisar", "review application"}
SUBMIT_LABELS = {"submit", "submit application", "send application", "enviar", "enviar solicitud", "postular"}


def normalize(value: str) -> str:
    value = "".join(char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char))
    return " ".join(value.casefold().replace("*", "").strip(" :").split())


def _state(driver, expected_url: str) -> dict:
    require_linkedin_page(driver, "job")
    if linkedin_url(driver.current_url, "job") != expected_url:
        raise RuntimeError("La oferta cambió durante la preparación. No se continuará.")
    dialogs = application_dialogs(driver)
    if len(dialogs) != 1:
        raise RuntimeError("No se reconoce un único formulario. Ejecuta inspect-job sin cerrarlo.")
    return driver.execute_script(_HELPERS + APPLICATION_DOM + r"""
        const root = arguments[0];
        return {
            root, form: collectApplication(root),
            controls: appControls(root).map(element => ({element,
                label: appQuestion(element), type: element.type || element.getAttribute('role'),
                required: !!element.required || element.getAttribute('aria-required') === 'true'})),
            resumes: appResumeChoices(root)
        };
    """, dialogs[0])


def _fingerprint(state: dict) -> tuple:
    return (state["form"]["title"], tuple(
        (normalize(field["label"]), field["type"], field["required"])
        for field in state["controls"]
    ))


def _answer(field: dict, data: dict) -> tuple:
    label = normalize(field["label"])
    exact = [(key, value) for key, value in data["answers"].items() if normalize(key) == label]
    if len(exact) > 1:
        raise ValueError(f"Hay respuestas duplicadas para la pregunta {field['label']}.")
    if exact:
        return exact[0][1], "answers"
    for key, aliases in CONTACT_LABELS.items():
        if label in aliases:
            return data["contact"][key], "contact." + key
    return None, None


def _select_index(driver, element, answer, source: str | None) -> int | None:
    if not isinstance(answer, str | int | float) or isinstance(answer, bool):
        return None
    wanted = normalize(str(answer))
    matches = []
    options = driver.execute_script("""
        return [...arguments[0].options].map((option, index) => ({index, text: option.text,
            disabled: option.disabled || (option.parentElement.tagName === 'OPTGROUP'
                && option.parentElement.disabled)}));
    """, element)
    for option in options:
        if option["disabled"]:
            continue
        label = normalize(option["text"])
        matched = label == wanted
        if source == "contact.phone_country_code" and re.fullmatch(r"\+\d{1,4}", str(answer)):
            matched = bool(re.search(r"\(" + re.escape(str(answer)) + r"\)\s*$", option["text"]))
        if matched:
            matches.append(option["index"])
    return matches[0] if len(matches) == 1 else None


def _plan(driver, state: dict, data: dict, job_title: str) -> tuple[list, dict | None, list]:
    plan, blocked = [], []
    resume = None
    choices = state["resumes"]
    resume_step = choices or any(field["type"] == "file" for field in state["controls"]) or (
        re.search(r"\bresume\b|curriculum", normalize(state["form"]["title"]))
    )
    if resume_step and not choices:
        blocked.append({"field": "resume", "reason": "resume_selection_controls_not_recognized"})
    if choices:
        rule = data["resume"]
        matches = [choice for choice in choices if normalize(choice["filename"]) == normalize(rule["filename"] or "")]
        eligible = any(normalize(word) in normalize(job_title) for word in rule["job_title_contains"])
        if not eligible:
            blocked.append({"field": "resume", "reason": "resume_rule_not_applicable_to_job_title"})
        elif len(matches) != 1:
            blocked.append({"field": "resume", "reason": "resume_not_found_or_ambiguous",
                            "available": [choice["filename"] for choice in choices]})
        else:
            resume = matches[0]
    labels = [normalize(field["label"]) for field in state["controls"]]
    for field in state["controls"]:
        element = field["element"]
        if choices and (field["type"] == "file" or any(element == choice["element"] for choice in choices)):
            continue
        answer, source = _answer(field, data)
        entry = {**field, "answer": answer, "source": source, "index": None}
        if answer is None:
            if field["required"]:
                blocked.append({"field": field["label"], "reason": "answer_not_configured"})
            continue
        if not field["label"] or labels.count(normalize(field["label"])) != 1:
            blocked.append({"field": field["label"], "reason": "ambiguous_question"})
            continue
        if not element.is_enabled() or element.get_dom_attribute("readonly") is not None:
            blocked.append({"field": field["label"], "reason": "field_not_editable"})
            continue
        kind = field["type"]
        if kind == "select-one":
            entry["index"] = _select_index(driver, element, answer, source)
            if entry["index"] is None:
                blocked.append({"field": field["label"], "reason": "option_not_found_or_ambiguous"})
        elif kind == "checkbox":
            if not isinstance(answer, bool):
                blocked.append({"field": field["label"], "reason": "boolean_answer_required"})
        elif kind not in {"text", "email", "tel", "number", "url", "search", "textarea"} or isinstance(answer, bool):
            blocked.append({"field": field["label"], "reason": "unsupported_control"})
        plan.append(entry)
    return plan, resume, blocked


def _buttons(state: dict, wanted: set[str]) -> list:
    return [button for button in state["root"].find_elements(By.CSS_SELECTOR, 'button,[role="button"]')
            if button.is_displayed() and button.is_enabled() and any(
                normalize(label) in wanted for label in (button.text, button.get_attribute("aria-label") or "")
            )]


def _fill_step(driver, state: dict, data: dict, job_title: str, expected_url: str) -> dict:
    plan, resume, blocked = _plan(driver, state, data, job_title)
    report = {"fields": [{"label": item["label"], "source": item["source"]} for item in plan],
              "resume": resume["filename"] if resume else None, "blocked": blocked}
    if blocked:
        return report
    fingerprint = _fingerprint(state)
    for item in plan:
        current = _state(driver, expected_url)
        if _fingerprint(current) != fingerprint:
            raise RuntimeError("El formulario cambió durante el rellenado. No se pulsó Next.")
        field = next(field for field in current["controls"] if normalize(field["label"]) == normalize(item["label"]))
        element = field["element"]
        kind = field["type"]
        if kind == "select-one":
            index = _select_index(driver, element, item["answer"], item["source"])
            if index is None:
                raise RuntimeError(f"Las opciones cambiaron para {item['label']}. No se continuará.")
            label = driver.execute_script("return arguments[0].options[arguments[1]].text;", element, index)
            Select(element).select_by_visible_text(label)
        elif kind == "checkbox":
            if element.is_selected() != item["answer"]:
                element.click()
        else:
            element.clear()
            element.send_keys(str(item["answer"]))
    if resume:
        current = _state(driver, expected_url)
        matches = [choice for choice in current["resumes"] if normalize(choice["filename"]) == normalize(resume["filename"])]
        if len(matches) != 1:
            raise RuntimeError("Cambió la lista de CV. No se seleccionó otro archivo.")
        if not matches[0]["selected"]:
            matches[0]["target"].click()
    current = _state(driver, expected_url)
    for item in plan:
        field = next(field for field in current["controls"] if normalize(field["label"]) == normalize(item["label"]))
        element = field["element"]
        if field["type"] == "select-one":
            expected = _select_index(driver, element, item["answer"], item["source"])
            valid = expected is not None and element.get_property("selectedIndex") == expected
        elif field["type"] == "checkbox":
            valid = element.is_selected() == item["answer"]
        else:
            expected, actual = str(item["answer"]), element.get_property("value") or ""
            if field["type"] == "tel":
                expected, actual = re.sub(r"\D", "", expected), re.sub(r"\D", "", actual)
            valid = expected == actual
        valid = valid and driver.execute_script("return !arguments[0].validity || arguments[0].validity.valid;", element)
        if not valid:
            report["blocked"].append({"field": item["label"], "reason": "verification_failed"})
    if resume and not any(choice["selected"] and normalize(choice["filename"]) == normalize(resume["filename"])
                          for choice in current["resumes"]):
        report["blocked"].append({"field": "resume", "reason": "selection_not_confirmed"})
    return report


def prepare_application(driver, data: dict, *, open_dialog: bool = False,
                        dry_run: bool = False, max_steps: int = 8) -> dict:
    if not 1 <= max_steps <= 20:
        raise ValueError("max_steps debe estar entre 1 y 20.")
    job = read_job(driver)
    expected_url = job["url"]
    inspect_application(driver, open_dialog=open_dialog)
    events = []

    def finish(status: str, state: dict) -> dict:
        return {"url": expected_url, "job_title": job["title"], "status": status,
                "submitted": False, "steps": events, "current_step": state["form"]}

    for _ in range(max_steps):
        state = _state(driver, expected_url)
        if _buttons(state, SUBMIT_LABELS) and not _buttons(state, ADVANCE_LABELS):
            return finish("ready_for_review", state)
        if dry_run:
            plan, resume, blocked = _plan(driver, state, data, job["title"])
            events.append({"fields": [{"label": item["label"], "source": item["source"]} for item in plan],
                           "resume": resume["filename"] if resume else None, "blocked": blocked})
            return finish("needs_answers" if blocked else "ready", state)
        event = _fill_step(driver, state, data, job["title"], expected_url)
        events.append(event)
        if event["blocked"]:
            return finish("needs_answers", _state(driver, expected_url))
        state = _state(driver, expected_url)
        buttons = _buttons(state, ADVANCE_LABELS)
        if len(buttons) != 1:
            return finish("needs_action", state)
        fingerprint = _fingerprint(state)
        buttons[0].click()

        def changed(browser, expected_fingerprint=fingerprint):
            try:
                next_state = _state(browser, expected_url)
            except RuntimeError:
                return None
            return next_state if _fingerprint(next_state) != expected_fingerprint else None

        try:
            WebDriverWait(driver, STEP_WAIT_SECONDS).until(changed)
        except TimeoutException:
            return finish("next_step_not_confirmed", _state(driver, expected_url))
    return finish("step_limit_reached", _state(driver, expected_url))
