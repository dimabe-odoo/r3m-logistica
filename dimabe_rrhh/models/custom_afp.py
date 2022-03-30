from odoo import models, fields


class CustomAfp(models.Model):
    _name = 'custom.afp'
    _description = 'AFP'

    code = fields.Char('Codigo', required=True)

    name = fields.Char('Nombre', required=True)

    vat = fields.Char('RUT', required=True)

    rate = fields.Float('Tasa')

    sis = fields.Float('Aporte Empresa')

    independent = fields.Float('Independientes')
