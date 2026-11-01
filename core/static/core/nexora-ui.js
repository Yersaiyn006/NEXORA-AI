/* NEXORA UI: navigation only; business actions remain in existing page scripts. */
(() => {
    'use strict';
    const toggle = document.querySelector('.nx-menu');
    const side = document.querySelector('.nx-sidebar');
    const backdrop = document.querySelector('.nx-backdrop');
    const main = document.querySelector('main');
    const closeButton = document.querySelector('.nx-drawer-close');
    function close(restoreFocus = false) {
        document.body.classList.remove('nx-menu-open');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
        if (backdrop) backdrop.hidden = true;
        if (main) main.inert = false;
        if (restoreFocus && toggle) toggle.focus();
    }
    if (toggle && side && backdrop) {
        toggle.addEventListener('click', () => {
            if (document.body.classList.contains('nx-menu-open')) return close(true);
            document.body.classList.add('nx-menu-open');
            toggle.setAttribute('aria-expanded', 'true');
            backdrop.hidden = false;
            if (main) main.inert = true;
            closeButton.focus();
        });
        backdrop.addEventListener('click', () => close(true));
        closeButton.addEventListener('click', () => close(true));
        document.addEventListener('keydown', event => {
            if (!document.body.classList.contains('nx-menu-open')) return;
            if (event.key === 'Escape') return close(true);
            if (event.key !== 'Tab') return;
            const controls = [...side.querySelectorAll('a[href],button:not(:disabled)')]
                .filter(element => element.getClientRects().length);
            const first = controls[0], last = controls[controls.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault(); last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault(); first.focus();
            }
        });
        side.querySelectorAll('a').forEach(link => link.addEventListener('click', () => close()));
        matchMedia('(min-width: 1001px)').addEventListener('change', event => {
            if (event.matches) close();
        });
    }
    document.querySelectorAll('main').forEach(element => element.classList.add('nx-enter'));
})();
