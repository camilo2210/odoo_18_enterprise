# -*- coding: utf-8 -*-
# from odoo import http


# class MyCustomModule(http.Controller):
#     @http.route('/my_custom_module/my_custom_module', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/my_custom_module/my_custom_module/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('my_custom_module.listing', {
#             'root': '/my_custom_module/my_custom_module',
#             'objects': http.request.env['my_custom_module.my_custom_module'].search([]),
#         })

#     @http.route('/my_custom_module/my_custom_module/objects/<model("my_custom_module.my_custom_module"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('my_custom_module.object', {
#             'object': obj
#         })

