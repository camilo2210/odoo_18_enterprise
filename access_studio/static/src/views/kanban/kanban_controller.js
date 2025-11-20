/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { useService } from '@web/core/utils/hooks';
import { onWillStart, useSubEnv } from '@odoo/owl';

patch(KanbanController.prototype, {
	setup() {
		super.setup();
		this.modelAccess = {};

		// Initialize per-view env cache synchronously in setup
		const sacCache = this.env.sacModelAccessByModel || {};
		useSubEnv({ sacModelAccessByModel: sacCache });

		const orm = useService('orm');
		onWillStart(async () => {
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
});


