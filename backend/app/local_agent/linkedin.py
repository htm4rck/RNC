"""DOM readers and a single supported click: opening the Easy Apply dialog."""

from time import sleep

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
const main = [...document.querySelectorAll('main, [role="main"]')].find(visible);
"""

PROFILE_WAIT_SECONDS = 15
PROFILE_SCROLL_STEPS = 20
PROFILE_SCROLL_PAUSE = 0.4
PROFILE_FIELDS = ("headline", "about", "experience", "education", "skills")

_PROFILE_HELPERS = _HELPERS + r"""
const excluded = e => !!e.closest('aside,nav,[role="dialog"]');
const nameSelectors = [
    'h1',
    '[role="heading"][aria-level="1"]',
    '.pv-text-details__left-panel .text-heading-xlarge',
    '.text-heading-xlarge',
    '[data-anonymize="person-name"]',
    '[data-view-name="profile-top-card"] h2',
    '.pv-top-card h2',
    '[aria-label="Profile header"] h2'
];
const profileElement = (root, selectors) => {
    for (const selector of selectors) {
        const value = [...root.querySelectorAll(selector)]
            .find(e => !excluded(e) && text(e));
        if (value) return value;
    }
    return null;
};
const profileText = (root, selectors) => text(profileElement(root, selectors));
const normalize = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ').trim().toLowerCase();
const aliases = {
    about: ['about', 'acerca de', 'sobre mi', 'extracto'],
    experience: ['experience', 'experiencia', 'experiencia laboral', 'experiencia profesional'],
    education: ['education', 'educacion', 'formacion', 'formacion academica'],
    skills: ['skills', 'aptitudes', 'conocimientos y aptitudes', 'habilidades']
};
const sections = main ? [...main.querySelectorAll('section')]
    .filter(e => visible(e) && !excluded(e)) : [];
const sectionMarker = '[id="about"],[id="experience"],[id="education"],'
    + '[id="skills"],[id="recent-activity"],[id="analytics"],[id="resources"]';
const topCard = sections[0];
const topCardIsIntro = topCard && !topCard.matches(sectionMarker)
    && !topCard.querySelector(sectionMarker);
const candidateNameElement = main ? profileElement(main, nameSelectors) || (
    topCardIsIntro ? profileElement(topCard, ['h2', '[role="heading"][aria-level="2"]']) : null
) : null;
const sectionNames = [...Object.values(aliases).flat(), 'suggested for you', 'analytics',
    'activity', 'resources', 'interests', 'recommendations', 'sugerencias para ti',
    'analisis', 'actividad', 'recursos', 'intereses', 'recomendaciones'];
const profileNameElement = candidateNameElement
    && !text(candidateNameElement).split('\n').some(line => sectionNames.includes(normalize(line)))
    ? candidateNameElement : null;
const profileName = text(profileNameElement);
const headings = main ? [...main.querySelectorAll('h1,h2,h3,h4,h5,h6,[role="heading"]')]
    .filter(e => visible(e) && !excluded(e)) : [];
const level = e => Number(e.getAttribute('aria-level') || e.tagName.match(/^H([1-6])$/)?.[1] || 2);
const headingKey = e => Object.keys(aliases).find(key =>
    text(e).split('\n').some(line => aliases[key].includes(normalize(line))));
const ignoredText = 'aside,nav,[role="dialog"],script,style,svg,noscript,button,'
    + 'input,select,textarea,[hidden],.visually-hidden,.sr-only';
const renderedText = (root, range = null) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const lines = [];
    while (walker.nextNode()) {
        const node = walker.currentNode;
        const parent = node.parentElement;
        const value = node.nodeValue.trim();
        if (!value || !parent || parent.closest(ignoredText) || !visible(parent)
            || getComputedStyle(parent).visibility !== 'visible'
            || (range && !range.intersectsNode(node))) continue;
        if (lines[lines.length - 1] !== value) lines.push(value);
    }
    return lines.join('\n');
};
const followingBoundary = heading => headings.find(candidate =>
    candidate !== heading && level(candidate) <= level(heading)
    && (heading.compareDocumentPosition(candidate) & Node.DOCUMENT_POSITION_FOLLOWING));
const headingText = heading => {
    const range = document.createRange();
    range.setStartBefore(heading);
    const boundary = followingBoundary(heading);
    if (boundary) range.setEndBefore(boundary);
    else range.setEnd(main, main.childNodes.length);
    return renderedText(main, range);
};
const introRoot = profileNameElement?.closest('section') || main;
const introBoundary = profileNameElement ? followingBoundary(profileNameElement) : null;
const introParagraphs = introRoot ? [...introRoot.querySelectorAll('p,[role="paragraph"]')]
    .filter(e => text(e) && !e.closest('a,button,aside,nav,[role="dialog"]')
        && profileNameElement
        && (profileNameElement.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_FOLLOWING)
        && (!introBoundary
            || (e.compareDocumentPosition(introBoundary) & Node.DOCUMENT_POSITION_FOLLOWING))) : [];
const extractProfile = (knownName = '') => {
    if (!main || (!profileName && !knownName)) return null;
    const sources = {};
    const section = (key, limit) => {
        const heading = headings.find(e => level(e) <= 2 && headingKey(e) === key);
        if (heading) {
            const value = headingText(heading).slice(0, limit);
            const body = value.split('\n').filter(line => !aliases[key].includes(normalize(line)));
            if (body.length) {
                sources[key] = 'heading:' + text(heading).split('\n')[0];
                return value;
            }
        }
        const anchor = main.querySelector(`[id="${key}"]`);
        const legacy = anchor?.closest('section');
        if (legacy && visible(legacy) && !excluded(legacy)) {
            const value = renderedText(legacy).slice(0, limit);
            if (value && !aliases[key].includes(normalize(value))) {
                sources[key] = 'section-id:' + key;
                return value;
            }
        }
        return '';
    };
    const explicitHeadline = profileNameElement ? profileText(introRoot, [
        '.text-body-medium.break-words', '[data-field="headline"]',
        '[data-anonymize="headline"]', '[data-view-name="profile-headline"]'
    ]) : '';
    const paragraphHeadline = introParagraphs.map(text)
        .find(value => value !== profileName && value.length <= 500) || '';
    const headline = explicitHeadline || paragraphHeadline;
    if (headline) sources.headline = explicitHeadline ? 'headline-selector' : 'intro-paragraph';
    return {
        full_name: profileName || knownName, headline,
        about: section('about', 8000), experience: section('experience', 16000),
        education: section('education', 8000), skills: section('skills', 8000),
        field_sources: sources
    };
};
"""


def read_profile(driver, scroll: bool = True) -> dict:
    def capture(browser, known_name: str | None = None):
        require_linkedin_page(browser, "profile")
        return browser.execute_script(
            _PROFILE_HELPERS + "return extractProfile(arguments[0]);", known_name
        )

    try:
        result = WebDriverWait(driver, PROFILE_WAIT_SECONDS).until(capture)
    except TimeoutException:
        raise RuntimeError(
            "No se reconoció el nombre del perfil tras esperar a que cargue. "
            "Ejecuta rcn-agent inspect-profile con la misma --url para diagnosticar los encabezados."
        ) from None
    if scroll and not all(result[field] for field in PROFILE_FIELDS):
        result = _read_scrolled_profile(driver, result, capture)
    require_linkedin_page(driver, "profile")
    missing = [field for field in PROFILE_FIELDS if not result[field]]
    if len(missing) == len(PROFILE_FIELDS):
        raise RuntimeError(
            "Solo se reconoció el nombre; no se guardó una captura sin datos profesionales. "
            "Ejecuta rcn-agent inspect-profile para revisar la estructura del perfil."
        )
    result["capture_status"] = "partial" if missing else "captured"
    result["field_status"] = {
        field: "not_detected" if field in missing else "captured" for field in PROFILE_FIELDS
    }
    result["warnings"] = [
        (
            f"No se detectaron: {', '.join(missing)}. Esto no indica que estén vacíos en LinkedIn. "
            "Ejecuta rcn-agent inspect-profile para diagnosticar la lectura."
        )
    ] if missing else []
    return {"url": linkedin_url(driver.current_url, "profile"), **result}


def _read_scrolled_profile(driver, result: dict, capture) -> dict:
    state = driver.execute_script(_HELPERS + r"""
        let scroller = main;
        while (scroller && scroller !== document.documentElement) {
            if (/(auto|scroll)/.test(getComputedStyle(scroller).overflowY)
                && scroller.scrollHeight > scroller.clientHeight) break;
            scroller = scroller.parentElement;
        }
        scroller = scroller && scroller !== document.documentElement
            ? scroller : document.scrollingElement;
        return {element: scroller, top: scroller.scrollTop, left: scroller.scrollLeft};
    """)
    element = state["element"]
    bottom_rounds = 0
    try:
        driver.execute_script("arguments[0].scrollTo({top: 0, behavior: 'instant'});", element)
        for _ in range(PROFILE_SCROLL_STEPS):
            sleep(PROFILE_SCROLL_PAUSE)
            current = capture(driver, result["full_name"])
            if current:
                if current["full_name"] != result["full_name"]:
                    raise RuntimeError("El perfil cambió durante la captura; repite el comando.")
                for field in PROFILE_FIELDS:
                    if len(current[field]) > len(result[field]):
                        result[field] = current[field]
                        result["field_sources"][field] = current["field_sources"][field]
            if all(result[field] for field in PROFILE_FIELDS):
                break
            position = driver.execute_script(r"""
                const e = arguments[0];
                const atBottom = e.scrollTop + e.clientHeight >= e.scrollHeight - 2;
                if (!atBottom) e.scrollBy({top: Math.max(400, e.clientHeight * 0.8), behavior: 'instant'});
                return atBottom;
            """, element)
            bottom_rounds = bottom_rounds + 1 if position else 0
            if bottom_rounds >= 3:
                break
    finally:
        driver.execute_script(
            "arguments[0].scrollTo({top: arguments[1], left: arguments[2], behavior: 'instant'});",
            element, state["top"], state["left"],
        )
    return result


def inspect_profile(driver) -> dict:
    """Limited structural diagnosis; no page HTML, form values, or message bodies."""
    require_linkedin_page(driver, "profile")
    result = driver.execute_script(_PROFILE_HELPERS + r"""
        const summary = e => ({
            tag: e.tagName.toLowerCase(),
            role: e.getAttribute('role'),
            level: e.getAttribute('aria-level'),
            class: String(e.className).slice(0, 200),
            text: text(e).slice(0, 160)
        });
        const profile = extractProfile();
        return {
            ready_state: document.readyState,
            main_found: !!main,
            name_detected: !!profileName,
            detected_fields: Object.fromEntries(
                ['headline','about','experience','education','skills'].map(key => [key, {
                    detected: !!profile?.[key],
                    characters: profile?.[key]?.length || 0,
                    source: profile?.field_sources[key] || null
                }])
            ),
            intro_paragraphs: introParagraphs.slice(0, 12).map(summary),
            name_candidates: main ? nameSelectors.map(selector => ({
                selector,
                matches: [...main.querySelectorAll(selector)]
                    .filter(e => visible(e) && !excluded(e)).slice(0, 3).map(summary)
            })) : [],
            headings: main ? [...main.querySelectorAll('h1,h2,h3,[role="heading"]')]
                .filter(e => visible(e) && !excluded(e)).slice(0, 20).map(summary) : [],
            sections: sections.slice(0, 12).map(e => ({
                id: e.id,
                anchors: [...e.querySelectorAll('[id]')].slice(0, 12).map(n => n.id),
                heading: profileText(e, ['h1','h2','h3','[role="heading"]']).slice(0, 160)
            }))
        };
    """)
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
