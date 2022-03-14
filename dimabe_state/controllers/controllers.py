# -*- coding: utf-8 -*-
# from odoo import http


# class DimabeStates(http.Controller):
#     @http.route('/dimabe_states/dimabe_states/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dimabe_states/dimabe_states/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('dimabe_states.listing', {
#             'root': '/dimabe_states/dimabe_states',
#             'objects': http.request.env['dimabe_states.dimabe_states'].search([]),
#         })

#     @http.route('/dimabe_states/dimabe_states/objects/<model("dimabe_states.dimabe_states"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dimabe_states.object', {
#             'object': obj
#         })
