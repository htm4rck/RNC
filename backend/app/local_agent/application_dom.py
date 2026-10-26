"""Read-only form discovery independent of LinkedIn's generated CSS classes."""

APPLICATION_DOM = r"""
const appNormalize = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ').trim().toLowerCase();
const appName = e => e.getAttribute('aria-label') || (e.getAttribute('aria-labelledby') || '')
    .split(/\s+/).map(id => document.getElementById(id)?.textContent.trim() || '').filter(Boolean).join(' ');
const appControls = root => [...root.querySelectorAll('input,select,textarea,[role="combobox"]')]
    .filter(e => (visible(e) || e.type === 'file')
        && !['hidden','password','submit','button','reset'].includes(e.type));
const appLabelText = label => {
    const copy = label.cloneNode(true);
    copy.querySelectorAll('input,select,textarea,button,option').forEach(e => e.remove());
    return copy.textContent.trim();
};
const appQuestion = e => {
    const labels = e.labels ? [...e.labels].map(appLabelText).filter(Boolean) : [];
    const legendElement = e.closest('fieldset')?.querySelector('legend');
    const legend = legendElement ? appLabelText(legendElement) : '';
    const own = labels.join(' ') || appName(e) || e.getAttribute('placeholder') || '';
    return legend && own && legend !== own ? legend + ' — ' + own : own || legend;
};
const appSignature = /\beasy apply\b|\bapply (to|for)\b|job application|application questions|contact info|informacion de contacto|personal information|informacion personal|\bresume\b|curriculum|solicitud sencilla|solicitud de empleo|postular|candidatura/;
const appActionLabels = root => [...root.querySelectorAll('button,[role="button"],input[type="submit"]')]
    .filter(visible).map(e => appName(e) || text(e));
const appDialogInfo = root => {
    const controls = appControls(root);
    const content = appNormalize(appName(root) + ' ' + root.innerText);
    const legacy = root.matches('.jobs-easy-apply-modal') || !!root.querySelector('.jobs-easy-apply-content');
    const named = appSignature.test(content);
    const blocked = /\b(new message|message recruiter|job alert|report job|nuevo mensaje|alerta de empleo|denunciar)\b/.test(content);
    const contact = controls.some(e => /email address|phone number|correo electronico|numero de telefono/.test(
        appNormalize(appQuestion(e))
    ));
    const next = appActionLabels(root).some(label => /^(next|siguiente|continue|continuar)$/i.test(label.trim()));
    return {
        element: root, fields: controls, blocked,
        recognized: legacy || (!blocked && controls.length > 0 && (named || (contact && next))),
        title: first(root, ['h1','h2','h3','[role="heading"]']) || appName(root)
            || [...root.querySelectorAll('p')].map(text)
                .find(value => appSignature.test(appNormalize(value))) || '',
        detection: legacy ? 'legacy-marker' : named ? 'application-labels'
            : contact && next ? 'contact-step' : 'unrecognized'
    };
};
const appDialogInfos = () => [...document.querySelectorAll('dialog,[role="dialog"],[aria-modal="true"]')]
    .filter(visible).map(appDialogInfo);
const appDialogRoots = (allowNew = []) => {
    const candidates = appDialogInfos().filter(info => info.recognized
        || (!info.blocked && info.fields.length && allowNew.includes(info.element)));
    return candidates.filter(info => !candidates.some(other => other !== info
        && other.element.contains(info.element))).map(info => info.element);
};
const collectApplication = root => {
    const info = appDialogInfo(root);
    return {
        title: info.title || 'Easy Apply',
        detection: info.recognized ? info.detection : 'opened-by-easy-apply',
        fields: info.fields.slice(0,80).map(e => ({
            label: appQuestion(e), type: e.type || e.getAttribute('role') || e.tagName.toLowerCase(),
            required: !!e.required || e.getAttribute('aria-required') === 'true',
            options: e.tagName === 'SELECT' ? [...e.options].slice(0,100).map(o => o.text) : []
        })),
        actions: appActionLabels(root).slice(0,30)
    };
};
"""
