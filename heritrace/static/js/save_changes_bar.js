// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
// SPDX-License-Identifier: ISC

class SaveChangesBar {
    constructor() {
        this.bar = document.getElementById('saveChangesBar');
        this.status = document.getElementById('saveChangesStatus');
        this.roots = [...document.querySelectorAll('.triples, .custom-properties-section')];
        this.active = false;
        this.saving = false;
        this.saved = false;
        this.observer = new MutationObserver(() => this.update());
        this.resizeObserver = new ResizeObserver(() => {
            document.documentElement.style.setProperty('--save-bar-height', `${this.bar.offsetHeight}px`);
        });
        $(this.roots).on('input change', 'input, select, textarea', () => this.update());
    }

    snapshot() {
        return JSON.stringify(this.roots.map(root => ({
            items: [...root.querySelectorAll('[data-repeater-item], .custom-property')]
                .filter(item => !item.closest('.repeater-template'))
                .map(item => [
                    item.getAttribute('data-old-object-id'),
                    item.getAttribute('data-temp-id'),
                    item.classList.contains('marked-for-deletion')
                ]),
            fields: [...root.querySelectorAll('input, select, textarea')]
                .filter(field => !field.closest('.repeater-template'))
                .map(field => [field.id, $(field).val(), field.checked])
        })));
    }

    hasChanges() {
        return this.active && this.snapshot() !== this.initialState;
    }

    start() {
        this.initialState = this.snapshot();
        this.active = true;
        this.saving = false;
        this.saved = false;
        this.bar.hidden = false;
        document.documentElement.classList.add('entity-editing');
        this.resizeObserver.observe(this.bar);
        this.roots.forEach(root => this.observer.observe(root, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ['class', 'value']
        }));
        this.update();
    }

    stop() {
        this.active = false;
        this.observer.disconnect();
        this.resizeObserver.disconnect();
        this.bar.hidden = true;
        document.documentElement.classList.remove('entity-editing');
        document.documentElement.style.removeProperty('--save-bar-height');
    }

    setSaving(saving) {
        this.saving = saving;
        this.update();
    }

    setSaved() {
        this.saved = true;
        this.saving = false;
        this.update();
    }

    update() {
        if (!this.active) return;
        const changed = this.hasChanges();
        const state = this.saving ? 'saving' : this.saved ? 'saved' : changed ? 'unsaved' : 'unchanged';
        const message = this.bar.dataset[state];
        if (this.status.textContent !== message) this.status.textContent = message;
        $('#saveChangesBtn')
            .attr('aria-busy', String(this.saving))
            .prop('disabled', this.saving || this.saved || !changed);
        $('#cancelChangesBtn, #editEntityBtn').prop('disabled', this.saving || this.saved);
    }
}

const saveChangesBar = new SaveChangesBar();
