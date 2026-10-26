"""DOM readers and a single supported click: opening the Easy Apply dialog."""

from time import sleep

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from app.local_agent.application_dom import APPLICATION_DOM
from app.local_agent.browser import require_linkedin_page
from app.local_agent.job_dom import JOB_DOM
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
JOB_WAIT_SECONDS = 15
APPLICATION_WAIT_SECONDS = 10

_PROFILE_HELPERS = _HELPERS + r"""
const excluded = e => !!e.closest('aside,nav,footer,[role="contentinfo"],[role="dialog"]');
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
const headingLabel = value => normalize(value).replace(/\s*[\[(]\s*\d[\d\s,.]*[\])]\s*$/, '');
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
    && !text(candidateNameElement).split('\n').some(line => sectionNames.includes(headingLabel(line)))
    ? candidateNameElement : null;
const profileName = text(profileNameElement);
const headings = main ? [...main.querySelectorAll('h1,h2,h3,h4,h5,h6,[role="heading"]')]
    .filter(e => visible(e) && !excluded(e)) : [];
const level = e => Number(e.getAttribute('aria-level') || e.tagName.match(/^H([1-6])$/)?.[1] || 2);
const headingKey = e => Object.keys(aliases).find(key =>
    text(e).split('\n').some(line => aliases[key].includes(headingLabel(line))));
const ignoredText = 'aside,nav,footer,[role="contentinfo"],[role="dialog"],script,style,svg,noscript,button,'
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
    // A lower section may not have loaded yet. Never extend beyond this card.
    const scope = heading.closest('section,article,[role="region"]') || heading.parentElement;
    const range = document.createRange();
    range.setStartAfter(heading);
    const boundary = followingBoundary(heading);
    if (boundary && scope.contains(boundary)) range.setEndBefore(boundary);
    else range.setEnd(scope, scope.childNodes.length);
    return renderedText(scope, range);
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
    const counts = {};
    const section = (key, limit) => {
        const heading = headings.find(e => level(e) <= 2 && headingKey(e) === key);
        if (heading) {
            const total = text(heading).match(/[\[(]\s*(\d[\d\s,.]*)[\])]\s*$/);
            if (total) {
                const root = heading.closest('section,article,[role="region"]') || heading.parentElement;
                const entries = key === 'skills' ? [...root.querySelectorAll(
                    '[id^="com.linkedin.sdui.profile.skill("]'
                )].filter(e => !e.id.endsWith('-divider') && visible(e) && !excluded(e)) : [];
                counts[key] = {
                    reported: Number(total[1].replace(/\D/g, '')),
                    rendered: entries.length || null
                };
            }
            const body = headingText(heading);
            if (body) {
                sources[key] = 'heading:' + text(heading).split('\n')[0];
                return (text(heading) + '\n' + body).slice(0, limit);
            }
            return '';
        }
        const anchor = main.querySelector(`[id="${key}"]`);
        const legacy = anchor?.closest('section');
        if (legacy && visible(legacy) && !excluded(legacy)) {
            const value = renderedText(legacy).slice(0, limit);
            if (value && !aliases[key].includes(headingLabel(value))) {
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
        field_sources: sources, section_counts: counts
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
    incomplete = [
        field for field, counts in result["section_counts"].items()
        if counts["reported"] > 0
        and (counts["rendered"] is None or counts["rendered"] < counts["reported"])
    ]
    result["capture_status"] = "partial" if missing or incomplete else "captured"
    result["capture_scope"] = "rendered_overview"
    result["incomplete_sections"] = incomplete
    result["field_status"] = {
        field: "not_detected" if field in missing else "captured" for field in PROFILE_FIELDS
    }
    result["warnings"] = [
        (
            f"No se detectaron: {', '.join(missing)}. Esto no indica que estén vacíos en LinkedIn. "
            "Ejecuta rcn-agent inspect-profile para diagnosticar la lectura."
        )
    ] if missing else []
    for field in incomplete:
        counts = result["section_counts"][field]
        rendered = counts["rendered"]
        detail = f"se detectaron {rendered} elementos renderizados" if rendered is not None else (
            "no se pudo verificar cuántos elementos están renderizados"
        )
        result["warnings"].append(
            f"{field}: LinkedIn anuncia {counts['reported']} elementos; {detail}. "
            "La captura corresponde a la vista principal; no se abrió la lista completa."
        )
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
                for field, counts in current["section_counts"].items():
                    previous = result["section_counts"].get(field, {})
                    result["section_counts"][field] = {
                        "reported": counts["reported"],
                        "rendered": max(previous.get("rendered") or 0, counts["rendered"] or 0)
                        or None,
                    }
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
            section_counts: profile?.section_counts || {},
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
    expected_url = linkedin_url(driver.current_url, "job")
    last = None

    def capture(browser):
        nonlocal last
        require_linkedin_page(browser, "job")
        if linkedin_url(browser.current_url, "job") != expected_url:
            raise RuntimeError("La vacante cambió durante la captura; repite el comando.")
        last = browser.execute_script(_HELPERS + JOB_DOM + "return collectJob(arguments[0]);", expected_url)
        return last if last and last["title"] and last["description"] else None

    try:
        result = WebDriverWait(driver, JOB_WAIT_SECONDS).until(capture)
    except TimeoutException:
        missing = [field for field in ("title", "description") if not (last or {}).get(field)]
        raise RuntimeError(
            f"No se reconocieron los campos de la vacante: {', '.join(missing)}. "
            "Ejecuta rcn-agent inspect-job en esa pestaña para diagnosticarla."
        ) from None
    return {"url": expected_url, **result}


def inspect_job(driver) -> dict:
    """Diagnose the selected job without exporting form values or the page HTML."""
    require_linkedin_page(driver, "job")
    result = driver.execute_script(_HELPERS + JOB_DOM + APPLICATION_DOM + r"""
        const excluded = e => !!e.closest('aside,nav,footer,[role="contentinfo"],[role="dialog"]');
        const describe = e => ({
            tag: e.tagName.toLowerCase(), role: e.getAttribute('role'),
            class: String(e.className).slice(0, 200),
            text: (e.getAttribute('aria-label') || text(e)).slice(0, 180)
        });
        const job = collectJob(arguments[0]);
        return {
            ready_state: document.readyState,
            main_found: !!main,
            browser_title: document.title.slice(0, 240),
            top_paragraphs: jobParagraphs.slice(0, 15).map(e => ({
                ...describe(e), font_size: getComputedStyle(e).fontSize
            })),
            detected_fields: Object.fromEntries(['title','company','location','description'].map(key => [key, {
                detected: !!job?.[key], source: job?.field_sources[key] || null
            }])),
            headings: main ? [...main.querySelectorAll('h1,h2,h3,[role="heading"]')]
                .filter(e => visible(e) && !excluded(e)).slice(0, 30).map(describe) : [],
            buttons: main ? [...main.querySelectorAll('button,[role="button"]')]
                .filter(e => visible(e) && !excluded(e)).slice(0, 30).map(describe) : [],
            description_candidates: main ? ['#job-details','.jobs-description__content',
                '[data-view-name="job-details"]'].map(selector => ({
                    selector,
                    matches: [...main.querySelectorAll(selector)]
                        .filter(e => visible(e) && !excluded(e)).length
                })) : [],
            company_links: main ? [...main.querySelectorAll('a[href*="/company/"]')]
                .filter(e => visible(e) && !excluded(e)).slice(0, 5)
                .map(e => ({text: text(e).slice(0, 160)})) : [],
            dialogs: appDialogInfos().slice(0, 5).map(info => ({
                    class: String(info.element.className).slice(0, 200),
                    heading: info.title.slice(0, 180),
                    accessible_name: appName(info.element).slice(0, 180),
                    application_recognized: !!info.recognized,
                    detection: info.detection,
                    field_count: info.fields.length,
                    fields: info.fields.slice(0, 20).map(e => ({label: appQuestion(e), type: e.type || e.getAttribute('role')})),
                    actions: appActionLabels(info.element).slice(0, 15)
                }))
        };
    """, linkedin_url(driver.current_url, "job"))
    return {"url": linkedin_url(driver.current_url, "job"), **result}


def inspect_application(driver, open_dialog: bool = False) -> dict:
    require_linkedin_page(driver, "job")
    dialogs = application_dialogs(driver)
    if not dialogs and _visible_dialogs(driver):
        raise RuntimeError(
            "Hay un diálogo abierto que aún no se reconoce como formulario de Easy Apply. "
            "Ejecuta rcn-agent inspect-job sin cerrarlo para diagnosticar sus etiquetas."
        )
    if not dialogs and open_dialog:
        before = _visible_dialogs(driver)
        buttons = [
            element for element in driver.find_elements(
                By.CSS_SELECTOR, 'main button,main [role="button"],[role="main"] button,[role="main"] [role="button"]'
            )
            if element.is_displayed() and element.is_enabled()
            and any(label in (element.get_attribute("aria-label") or element.text).casefold()
                    for label in ("easy apply", "solicitud sencilla"))
        ]
        if len(buttons) != 1:
            raise RuntimeError("No se encontró un único botón visible de Easy Apply.")
        buttons[0].click()

        def newly_opened_application(browser):
            require_linkedin_page(browser, "job")
            opened = [element for element in _visible_dialogs(browser) if element not in before]
            return application_dialogs(browser, opened)

        try:
            dialogs = WebDriverWait(driver, APPLICATION_WAIT_SECONDS).until(newly_opened_application)
        except TimeoutException:
            raise RuntimeError(
                "Se pulsó Easy Apply, pero no se pudo reconocer su formulario. "
                "Si está abierto, déjalo así y ejecuta rcn-agent inspect-job."
            ) from None
        require_linkedin_page(driver, "job")
    if len(dialogs) != 1:
        raise RuntimeError("Abre un único formulario de Easy Apply o usa --open.")
    result = driver.execute_script(
        _HELPERS + APPLICATION_DOM + "return collectApplication(arguments[0]);", dialogs[0]
    )
    return {
        "url": linkedin_url(driver.current_url, "job"),
        "submitted": False,
        "scope": "visible_step_only",
        **result,
    }


def _visible_dialogs(driver) -> list:
    return driver.execute_script(
        _HELPERS + APPLICATION_DOM + "return appDialogInfos().map(info => info.element);"
    )


def application_dialogs(driver, newly_opened: list | None = None) -> list:
    return driver.execute_script(
        _HELPERS + APPLICATION_DOM + "return appDialogRoots(arguments[0]);", newly_opened or []
    )
