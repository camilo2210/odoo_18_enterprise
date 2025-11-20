/** @odoo-module **/

import { FormController } from '@web/views/form/form_controller';
import { patch } from '@web/core/utils/patch';
import { onWillStart, useSubEnv } from '@odoo/owl';

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.modelAccess = {};

        // Initialize per-view env cache synchronously in setup
        const sacCache = this.env.sacModelAccessByModel || {};
        useSubEnv({ sacModelAccessByModel: sacCache });

        onWillStart(async () => {
            // Use cache if available; otherwise fetch once and cache
            const cached = sacCache[this.props.resModel];
            if (cached) {
                this.modelAccess = cached;
                return;
            }
            const access = await this.orm.call('model.access', 'get_cached_model_access', [this.props.resModel]);
            this.modelAccess = access || {};
            sacCache[this.props.resModel] = this.modelAccess;
        });
    },

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        const accessRules = this.modelAccess;

        const menuConfig = [
            { key: 'archive', rule: 'hide_archive' },
            { key: 'unarchive', rule: 'hide_unarchive' },
            { key: 'duplicate', rule: 'hide_duplicate' },
            { key: 'addPropertyFieldValue', rule: 'hide_add_property' },
        ];

        for (const { key, rule } of menuConfig) {
            if (menuItems[key]) {
                const originalIsAvailable = menuItems[key].isAvailable;
                menuItems[key].isAvailable = () =>
                  !accessRules[rule] && originalIsAvailable();
            }
        }

        return menuItems;
    },
});
