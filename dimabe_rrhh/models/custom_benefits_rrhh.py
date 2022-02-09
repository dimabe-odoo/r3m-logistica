from odoo import models, fields


class CustomBenefitsRRHH(models.Model):
    _name = 'custom.benefits.rrhh'

    code = fields.Char(string='Codigo', required=True)

    name = fields.Char(string='Nombre', required=True)

    data_type_id = fields.Many2one('custom.data.type')

    type = fields.Selection(
        [('afp', 'AFP'), ('safe', 'Cia Seguro de Vida'), ('mutual', 'Fondos Mutuos'), ('broker', 'Corredor de Bolsa'),
         ('bank', 'Banco')], string='Tipo')
