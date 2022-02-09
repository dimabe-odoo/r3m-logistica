from odoo import models,fields

class CustomIsapre(models.Model):
    _name = 'custom.isapre'

    code = fields.Char()

    name = fields.Char()

    vat = fields.Char()