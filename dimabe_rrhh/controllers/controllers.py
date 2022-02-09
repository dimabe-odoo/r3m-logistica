# -*- coding: utf-8 -*-
# from odoo import http


# class DimabeRrhh(http.Controller):
#     @http.route('/dimabe_rrhh/dimabe_rrhh/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dimabe_rrhh/dimabe_rrhh/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('dimabe_rrhh.listing', {
#             'root': '/dimabe_rrhh/dimabe_rrhh',
#             'objects': http.request.env['dimabe_rrhh.dimabe_rrhh'].search([]),
#         })

#     @http.route('/dimabe_rrhh/dimabe_rrhh/objects/<model("dimabe_rrhh.dimabe_rrhh"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dimabe_rrhh.object', {
#             'object': obj
#         })
