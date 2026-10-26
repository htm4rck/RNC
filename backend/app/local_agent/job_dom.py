"""Read-only DOM helpers for legacy and SDUI job detail pages."""

JOB_DOM = r"""
const jobExcluded = e => !!e.closest('aside,nav,footer,[role="contentinfo"],[role="dialog"],dialog');
const jobText = e => !e || jobExcluded(e) ? '' : text(e);
const jobFirst = selectors => {
    if (!main) return '';
    for (const selector of selectors) {
        const value = [...main.querySelectorAll(selector)].map(jobText).find(Boolean);
        if (value) return value;
    }
    return '';
};
const jobNormalize = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ').trim().toLowerCase();
const jobTitleValid = value => !!value && !['hybrid','remote','on-site','onsite','hibrido',
    'remoto','presencial','full-time','part-time','contract','jornada completa',
    'easy apply','save','save the job'].includes(jobNormalize(value));
const jobHeadings = main ? [...main.querySelectorAll('h1,h2,h3,[role="heading"]')]
    .filter(e => jobText(e)) : [];
const aboutJobLabels = ['about the job','acerca del empleo','acerca del puesto',
    'descripcion del empleo','descripcion del puesto','sobre el empleo'];
const aboutJobHeading = jobHeadings.find(e => aboutJobLabels.includes(jobNormalize(text(e))));
const jobIntroBoundary = jobHeadings.find(e => e.tagName !== 'H1' && e.getAttribute('aria-level') !== '1');
const inJobIntro = e => jobText(e) && (!jobIntroBoundary
    || (e.compareDocumentPosition(jobIntroBoundary) & Node.DOCUMENT_POSITION_FOLLOWING));
const jobParagraphs = main ? [...main.querySelectorAll('p,[role="paragraph"]')]
    .filter(e => inJobIntro(e) && !e.closest('button,[role="button"]')) : [];
const jobBodyText = heading => {
    const root = heading.closest('section,article,[role="region"]') || heading.parentElement;
    const range = document.createRange();
    range.setStartAfter(heading);
    const next = jobHeadings.find(e => e !== heading
        && (heading.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_FOLLOWING)
        && /^(H[12])$/.test(e.tagName));
    if (next && root.contains(next)) range.setEndBefore(next);
    else range.setEnd(root, root.childNodes.length);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const lines = [];
    while (walker.nextNode()) {
        const node = walker.currentNode;
        const parent = node.parentElement;
        const value = node.nodeValue.trim();
        if (!value || !parent || !visible(parent) || jobExcluded(parent)
            || parent.closest('script,style,svg,button,input,select,textarea,.visually-hidden,.sr-only')
            || getComputedStyle(parent).visibility !== 'visible' || !range.intersectsNode(node)) continue;
        if (lines[lines.length - 1] !== value) lines.push(value);
    }
    return lines.join('\n');
};
const collectJob = canonicalUrl => {
    if (!main) return null;
    const sources = {};
    const browserParts = document.title.replace(/^\(\d+\)\s*/, '').split(/\s+\|\s+/);
    const browserJobTitle = browserParts.length >= 3 && /^linkedin$/i.test(browserParts.at(-1))
        && !/^(jobs?|empleos?|search|busqueda)\b|\bjobs in\b/i.test(browserParts[0])
        ? browserParts[0].trim() : '';
    let title = jobFirst(['.job-details-jobs-unified-top-card__job-title h1', 'h1',
        '[role="heading"][aria-level="1"]', '[data-field="job-title"]']);
    if (!jobTitleValid(title)) title = '';
    if (title) sources.title = 'title-selector';
    if (!title) {
        const link = [...main.querySelectorAll('a[href]')].find(e => {
            if (!jobTitleValid(jobText(e))) return false;
            try {
                const parsed = new URL(e.href);
                return parsed.origin === 'https://www.linkedin.com'
                    && parsed.pathname.replace(/\/$/, '') === new URL(canonicalUrl).pathname.replace(/\/$/, '');
            } catch { return false; }
        });
        if (link) { title = text(link); sources.title = 'job-link'; }
    }
    if (!title && jobTitleValid(browserJobTitle)) { title = browserJobTitle; sources.title = 'browser-title'; }
    if (!title) {
        const candidates = jobParagraphs.filter(e => !e.closest('a'))
            .map(e => ({value: text(e), size: parseFloat(getComputedStyle(e).fontSize)}))
            .filter(e => e.value.length <= 300 && jobTitleValid(e.value)).sort((a,b) => b.size - a.size);
        if (candidates[0]?.size >= 20 && (!candidates[1] || candidates[0].size > candidates[1].size)) {
            title = candidates[0].value;
            sources.title = 'intro-prominent-paragraph';
        }
    }
    let company = jobFirst(['.job-details-jobs-unified-top-card__company-name',
        '.jobs-unified-top-card__company-name', '[data-field="company"]']);
    if (company) sources.company = 'company-selector';
    if (!company) {
        const link = [...main.querySelectorAll('a[href*="/company/"]')].find(inJobIntro);
        if (link) { company = text(link); sources.company = 'intro-company-link'; }
    }
    if (!company && browserJobTitle) { company = browserParts.at(-2).trim(); sources.company = 'browser-title'; }
    let description = jobFirst(['#job-details', '.jobs-description__content']);
    if (description) sources.description = 'description-selector';
    if (!description && aboutJobHeading) {
        description = jobBodyText(aboutJobHeading);
        if (description) sources.description = 'heading:' + text(aboutJobHeading);
    }
    if (!title && description) {
        const lines = description.split('\n').map(line => line.trim()).filter(Boolean);
        const intro = lines.findIndex(line => /^(buscamos (un|una)|we are looking for (a|an))$/i.test(line));
        const role = intro >= 0 ? lines[intro + 1] : '';
        if (role && role.length <= 200 && jobTitleValid(role)) {
            title = role;
            sources.title = 'description-role';
        }
    }
    const location = jobFirst(['.job-details-jobs-unified-top-card__primary-description-container',
        '.jobs-unified-top-card__bullet', '[data-field="location"]']);
    if (location) sources.location = 'location-selector';
    return {
        title: title || '', company, location, description: description.slice(0, 24000),
        easy_apply: [...main.querySelectorAll('button,[role="button"]')].some(e =>
            jobText(e) && /easy apply|solicitud sencilla/i.test(e.getAttribute('aria-label') || text(e))),
        field_sources: sources
    };
};
"""
