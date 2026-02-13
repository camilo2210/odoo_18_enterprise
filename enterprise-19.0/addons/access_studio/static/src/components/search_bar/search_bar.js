/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { onWillStart, useSubEnv } from '@odoo/owl';
import { SearchBar } from '@web/search/search_bar/search_bar';
import { SearchBarMenu } from '@web/search/search_bar_menu/search_bar_menu';

patch(SearchBar.prototype, {
  setup() {
    super.setup();
    this.searchBarAccessRules = {};
    const sacCache = this.env.sacSearchBarAccessByModel || {};
    useSubEnv({ sacSearchBarAccessByModel: sacCache });

    onWillStart(async () => {
      const cached = sacCache[this.env.searchModel?.resModel];
      if (cached) {
        this.searchBarAccessRules = cached;
        return;
      }
      const access = await this.orm.call('search.panel.access', 'get_cached_search_panel_access', [this.env.searchModel?.resModel]);
      this.searchBarAccessRules = access || {};
      sacCache[this.env.searchModel?.resModel] = this.searchBarAccessRules;
    });
  },

  // Hide search panel
  get hideSearchPanel() {
    return this.searchBarAccessRules?.hide_search_panel || false;
  },
});

patch(SearchBarMenu.prototype, {
  setup() {
    super.setup();
    this.searchBarAccessRules = {};
    const sacCache = this.env.sacSearchBarAccessByModel || {};
    useSubEnv({ sacSearchBarAccessByModel: sacCache });

    onWillStart(async () => {
      const cached = sacCache[this.env.searchModel?.resModel];
      if (cached) {
        this.searchBarAccessRules = cached;
        return;
      }
      const access = await this.orm.call('search.panel.access', 'get_cached_search_panel_access', [this.env.searchModel?.resModel]);
      console.log('search bar access', access);
      this.searchBarAccessRules = access || {};
      sacCache[this.env.searchModel?.resModel] = this.searchBarAccessRules;
    });
  },

  // Hide custom filter separater and add custom filter button
  get hideCustomFilter() {
    return this.searchBarAccessRules?.hide_custom_filter || false;
  },

  // Hide custom Group-By sub-menu completely
  get hideCustomGroupBy() {
    return this.searchBarAccessRules?.hide_custom_group || super.hideCustomGroupBy || false;
  },

  // Hide delete in favorites icon
  get hideDeleteInFavorites() {
    return this.searchBarAccessRules?.hide_unlink_in_favorites || false;
  },
});
