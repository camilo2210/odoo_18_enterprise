/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { onWillStart, useSubEnv } from '@odoo/owl';
import { Chatter } from '@mail/chatter/web_portal/chatter';

patch(Chatter.prototype, {
	setup() {
		super.setup();

		this.chatterAccessRules = {};
		const sacCache = this.env.sacChatterAccessByModel || {};
		useSubEnv({ sacChatterAccessByModel: sacCache });

		onWillStart(async () => {
			const cached = sacCache[this.props.threadModel];
			if (cached) {
				this.chatterAccessRules = cached;
				return;
			}
			const access = await this.orm.call('chatter.access', 'get_cached_chatter_access', [this.props.threadModel]);
			this.chatterAccessRules = access || {};
			sacCache[this.props.threadModel] = this.chatterAccessRules;
		});
	},

	get hideChatter() {
		return this.chatterAccessRules?.hide_chatter || false;
	},
	get hideSendMessage() {
		return this.chatterAccessRules?.hide_send_message || false;
	},
	get hideLogNotes() {
		return this.chatterAccessRules?.hide_log_notes || false;
	},
	get hideScheduleActivity() {
		return this.chatterAccessRules?.hide_schedule_activity || false;
	},
	get hideSearchMessageIcon() {
		return this.chatterAccessRules?.hide_search_message_icon || false;
	},
	get hideAttachmentIcon() {
		return this.chatterAccessRules?.hide_attachment_icon || false;
	},
	get hideFollowersIcon() {
		return this.chatterAccessRules?.hide_followers_icon || false;
	},
	get hideFollowUnfollow() {
		return this.chatterAccessRules?.hide_follow_unfollow || false;
	},
});
