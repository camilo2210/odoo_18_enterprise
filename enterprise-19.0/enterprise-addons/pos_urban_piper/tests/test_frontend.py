import odoo.tests
from odoo import Command
from odoo.addons.point_of_sale.tests.common import archive_products
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_urban_piper.models.pos_urban_piper_request import UrbanPiperClient
from unittest.mock import patch


@odoo.tests.tagged('post_install', '-at_install')
class TestPosUrbanPiperCommon(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        archive_products(cls.env)
        cls.env['ir.config_parameter'].set_param('pos_urban_piper.urbanpiper_username', 'demo')
        cls.env['ir.config_parameter'].set_param('pos_urban_piper.urbanpiper_apikey', 'demo')
        cls.urban_piper_config = cls.env['pos.config'].create({
            'name': 'Urban Piper',
            'module_pos_urban_piper': True,
            'urbanpiper_delivery_provider_ids': [Command.set([cls.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id])]
        })
        cls.product_1 = cls.env['product.template'].create({
            'name': 'Product 1',
            'available_in_pos': True,
            'taxes_id': [(5, 0, 0)],
            'type': 'consu',
            'list_price': 100.0,
        })


class TestFrontend(TestPosUrbanPiperCommon):

    def test_payment_method_close_session(self):
        def _mock_make_api_request(self, endpoint, method='POST', data=None, timeout=10):
            return []
        self.urban_piper_config.payment_method_ids = self.env['pos.payment.method'].search([]).filtered(lambda pm: pm.type == 'bank')
        with patch.object(UrbanPiperClient, "_make_api_request", _mock_make_api_request):
            self.urban_piper_config.with_user(self.pos_admin).open_ui()
            self.start_pos_tour('test_payment_method_close_session', pos_config=self.urban_piper_config, login="pos_admin")
