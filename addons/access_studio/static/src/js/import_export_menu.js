/** @odoo-module **/

import { registry } from '@web/core/registry';

const cogMenuRegistry = registry.category('cogMenu');

function makeIsDisplayedWrapper(originalIsDisplayed, ruleKey) {
	return async function (env) {
		const originallyDisplayed = await originalIsDisplayed(env);
		if (!originallyDisplayed) {
			return false;
		}

		const resModel =
			env.searchModel?.resModel ||
			env.props?.resModel ||
			env.config?.resModel;
		
		if (!resModel) {
			return originallyDisplayed;
		}

        // Read from per-view cache populated by controllers; fall back to empty object
        const modelAccess = (env.sacModelAccessByModel && env.sacModelAccessByModel[resModel]) || {};
		const shouldHide = !!modelAccess[ruleKey];

		return originallyDisplayed && !shouldHide;
	};
}

try{
	const importMenuItem = cogMenuRegistry.get('import-menu');
	if (importMenuItem) {
		cogMenuRegistry.add(
			'import-menu',
			{
				...importMenuItem,
				isDisplayed: makeIsDisplayedWrapper(importMenuItem.isDisplayed, 'hide_import'),
			},
			{ force: true }
		);
	}
} catch (error) {
	console.error('Error restricting import-menu', error);
}

try{
	const exportAllMenuItem = cogMenuRegistry.get('export-all-menu');
	if (exportAllMenuItem) {
		cogMenuRegistry.add(
			'export-all-menu',
			{
				...exportAllMenuItem,
				isDisplayed: makeIsDisplayedWrapper(exportAllMenuItem.isDisplayed, 'hide_export'),
			},
			{ force: true }
		);
	}
} catch (error) {
	console.error('Error restricting export-all-menu', error);
}