/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { ListController } from '@web/views/list/list_controller';
import { useService } from '@web/core/utils/hooks';
import { onWillStart, useSubEnv } from '@odoo/owl';

patch(ListController.prototype, {
	setup() {
		super.setup();
		this.modelAccess = {};

		// Initialize per-view env cache synchronously in setup
		const sacCache = this.env.sacModelAccessByModel || {};
		useSubEnv({ sacModelAccessByModel: sacCache });

		const orm = useService('orm');
		onWillStart(async () => {
			// Use cache if available; otherwise fetch and cache
			const cached = sacCache[this.props.resModel];
			if (cached) {
				this.modelAccess = cached;
				return;
			}
			const access = await orm.call(
				'model.access',
				'get_cached_model_access',
				[this.props.resModel],
				{ context: this.props.context }
			);
			this.modelAccess = access || {};
			sacCache[this.props.resModel] = this.modelAccess;
		});
	},

	getStaticActionMenuItems() {
		const menuItems = super.getStaticActionMenuItems();
		const access = this.modelAccess;

		const menuPatches = [
			{ key: 'export', rule: 'hide_export' },
			{ key: 'archive', rule: 'hide_archive' },
			{ key: 'unarchive', rule: 'hide_unarchive' },
			{ key: 'duplicate', rule: 'hide_duplicate' },
			{ key: 'delete', rule: 'hide_unlink' },
		];

		for (const { key, rule } of menuPatches) {
			if (menuItems[key]) {
				const originalisAvailable = menuItems[key].isAvailable;
				menuItems[key].isAvailable = () =>
					!access[rule] && originalisAvailable();
			}
		}

		return menuItems;
	},
});