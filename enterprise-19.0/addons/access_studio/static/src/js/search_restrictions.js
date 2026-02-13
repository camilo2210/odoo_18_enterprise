/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SearchModel } from "@web/search/search_model";

const modelToRules = new Map();
async function getHiddenRules(searchModel) {
    const resModel = searchModel.resModel;
    if (modelToRules.has(resModel)) return modelToRules.get(resModel);
    const result = await searchModel.orm.call(
        "search.panel.access",
        "get_cached_search_panel_access",
        [resModel],
        {}
    );
    const rules = {
        hideFilters: new Set(result?.hideFilters || []),
        hideGroups: new Set(result?.hideGroups || []),
    };
    modelToRules.set(resModel, rules);
    return rules;
}

function removeHiddenItems(items, rules) {
	if (!Array.isArray(items) || !rules) return items;
	return items.filter((it) => {
		const name = it?.name;
		if (!name) return true;
		if (it.type === "filter") return !rules.hideFilters.has(name);
		if (it.type === "groupBy") return !rules.hideGroups.has(name);
		return true;
	});
}

function removeHiddenFacets(facets, rules) {
	if (!Array.isArray(facets) || !rules) return facets;
	return facets.filter((f) => {
		const name = f?.item?.name;
		if (!name) return true;
		if (f.type === "filter") return !rules.hideFilters.has(name);
		if (f.type === "groupBy") return !rules.hideGroups.has(name);
		return true;
	});
}

patch(SearchModel.prototype, {
    async load(...args) {
        const res = await super.load(...args);
        const rules = await getHiddenRules(this);
        
        // Mark hidden items invisible and collect their ids
        const hiddenIds = new Set();
        for (const [id, item] of Object.entries(this.searchItems)) {
            const name = item?.name;
            if (!name) continue;
            const hideFilter = (item.type === "filter" || item.type === "dateFilter") && rules.hideFilters.has(name);
            const hideGroup = (item.type === "groupBy" || item.type === "dateGroupBy") && rules.hideGroups.has(name);
            if (hideFilter || hideGroup) {
                item.invisible = "True";
                hiddenIds.add(Number(id));
            }
        }

        // Purge active query entries pointing to hidden items
        if (Array.isArray(this.query) && hiddenIds.size) {
            this.query = this.query.filter((q) => !hiddenIds.has(q.searchItemId));
            if (this._checkOrderByCountStatus) this._checkOrderByCountStatus();
            if (this._notify) this._notify();
        }
        return res;
    },

    addFacet(item, ...rest) {
		const rules = modelToRules.get(this.resModel);
		const name = item?.name;
        if (rules && name) {
            if (item.type === "filter" && rules.hideFilters.has(name)) return;
            if ((item.type === "groupBy" || item.type === "dateGroupBy") && rules.hideGroups.has(name)) return;
        }
		return this._super(item, ...rest);
	},
});
