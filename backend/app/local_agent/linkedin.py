"""DOM readers and a single supported click: opening the Easy Apply dialog."""

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from app.local_agent.browser import require_linkedin_page
from app.local_agent.urls import linkedin_url

# No HTML, cookies, localStorage, hidden inputs, or complete page source is exported.
_HELPERS = r"""
const visible = e => !!e && !!e.getClientRects().length;
const text = e => visible(e) ? e.innerText.trim() : '';
const first = (root, selectors) => {
    for (const selector of selectors) {
        const value = [...root.querySelectorAll(selector)].map(text).find(Boolean);
        if (value) return value;
    }
    return '';
};
const main = document.querySelector('main');
"""


def read_profile(driver) -> dict:
    require_linkedin_page(driver, "profile")
    result = driver.execute_script(_HELPERS + r"""
        if (!main) return null;
        const sections = [...main.querySelectorAll('section')].filter(visible);
        const section = (id, limit) => sections
            .filter(e => e.id === id || e.querySelector(`[id="${id}"]`))
            .map(text).join('\n').slice(0, limit);
        return {
            full_name: first(main, ['h1']),
            headline: first(main, ['.text-body-medium.break-words', '[data-field="headline"]']),
            about: section('about', 8000),
            experience: section('experience', 16000),
            education: section('education', 8000),
            skills: section('skills', 8000)
        };
    """)
    if not result or not result["full_name"]:
        raise RuntimeError("No se reconoció el perfil visible. Puede haber cambiado el DOM.")
    return {"url": linkedin_url(driver.current_url, "profile"), **result}


def read_job(driver) -> dict:
    require_linkedin_page(driver, "job")
    result = driver.execute_script(_HELPERS + r"""
        if (!main) return null;
        return {
            title: first(main, ['.job-details-jobs-unified-top-card__job-title h1', 'h1']),
            company: first(main, [
                '.job-details-jobs-unified-top-card__company-name',
                '.jobs-unified-top-card__company-name', '[data-field="company"]'
            ]),
            location: first(main, [
                '.job-details-jobs-unified-top-card__primary-description-container',
                '.jobs-unified-top-card__bullet', '[data-field="location"]'
            ]),
            description: first(main, ['#job-details', '.jobs-description__content'])
                .slice(0, 24000),
            easy_apply: [...main.querySelectorAll('button')].filter(visible).some(e =>
                /easy apply|solicitud sencilla/i.test(e.getAttribute('aria-label') || text(e)))
        };
    """)
    if not result or not result["title"] or not result["description"]:
        raise RuntimeError("La vacante no está cargada o no se reconoció su descripción.")
    return {"url": linkedin_url(driver.current_url, "job"), **result}


def inspect_application(driver, open_dialog: bool = False) -> dict:
    require_linkedin_page(driver, "job")
    dialogs = application_dialogs(driver)
    if not dialogs and open_dialog:
        buttons = [
            element for element in driver.find_elements(By.CSS_SELECTOR, "main button")
            if element.is_displayed() and element.is_enabled()
            and any(label in (element.get_attribute("aria-label") or element.text).casefold()
                    for label in ("easy apply", "solicitud sencilla"))
        ]
        if len(buttons) != 1:
            raise RuntimeError("No se encontró un único botón visible de Easy Apply.")
        buttons[0].click()
        try:
            WebDriverWait(driver, 10).until(application_dialogs)
        except TimeoutException:
            raise RuntimeError("No se abrió Easy Apply. Revisa la pestaña de Firefox.") from None
        require_linkedin_page(driver, "job")
        dialogs = application_dialogs(driver)
    if len(dialogs) != 1:
        raise RuntimeError("Abre un único formulario de Easy Apply o usa --open.")
    result = driver.execute_script(_HELPERS + r"""
        const dialog = arguments[0];
        const label = e => {
            const labels = e.labels ? [...e.labels].map(text).filter(Boolean) : [];
            const labelled = (e.getAttribute('aria-labelledby') || '').split(/\s+/)
                .map(id => text(document.getElementById(id))).filter(Boolean);
            return labels.join(' ') || e.getAttribute('aria-label')
                || labelled.join(' ') || e.getAttribute('placeholder') || '';
        };
        return {
            title: first(dialog, ['h1', 'h2', 'h3']),
            fields: [...dialog.querySelectorAll('input,select,textarea')]
                .filter(e => visible(e) && !['hidden','password','submit','button']
                    .includes(e.type)).slice(0, 80).map(e => ({
                    label: label(e), type: e.type || e.tagName.toLowerCase(),
                    required: e.required || e.getAttribute('aria-required') === 'true',
                    options: e.tagName === 'SELECT'
                        ? [...e.options].slice(0, 100).map(o => o.text) : []
                })),
            actions: [...dialog.querySelectorAll('button')].filter(visible)
                .map(e => e.getAttribute('aria-label') || text(e)).slice(0, 30)
        };
    """, dialogs[0])
    return {
        "url": linkedin_url(driver.current_url, "job"),
        "submitted": False,
        "scope": "visible_step_only",
        **result,
    }


def application_dialogs(driver) -> list:
    selector = (
        '[role="dialog"].jobs-easy-apply-modal, '
        '[role="dialog"]:has(.jobs-easy-apply-content)'
    )
    return [element for element in driver.find_elements(By.CSS_SELECTOR, selector)
            if element.is_displayed()]
