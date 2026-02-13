from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.account_online_synchronization.tests.common import AccountOnlineSynchronizationCommon


@tagged('post_install', '-at_install')
class TestAccountOnlineLinkPayment(AccountOnlineSynchronizationCommon):

    @patch("odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._update_connection_status")
    def test_update_status_when_payment_enabled(self, patched_update_connection_status):
        self.account_online_link.provider_type = 'provider_A'

        patched_update_connection_status.return_value = {
            'consent_expiring_date': None,
            'is_payment_enabled': True,
            'is_payment_activated': False,
        }
        self.account_online_link._update_connection_status()
        self.assertEqual(self.account_online_link.provider_type, 'provider_A_payment')

    @patch("odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._update_connection_status")
    def test_update_status_when_payment_deactivated(self, patched_update_connection_status):
        self.account_online_link.provider_type = 'provider_A_payment_activated'

        patched_update_connection_status.return_value = {
            'consent_expiring_date': None,
            'is_payment_enabled': True,
            'is_payment_activated': False,
        }
        self.account_online_link._update_connection_status()
        self.assertEqual(self.account_online_link.provider_type, 'provider_A_payment')
