from odoo import models,fields

class CustomIsapre(models.Model):
    _name = 'custom.isapre'
    _description = "ISAPRE"

    code = fields.Char()

    name = fields.Char()

    vat = fields.Char()