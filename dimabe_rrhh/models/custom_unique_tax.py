from odoo import models, fields, api

class CustomUniqueTax(models.Model):
    _name = "custom.unique.tax"

    salary_from = fields.Float('Desde')

    salary_to = fields.Float('Hasta')

    factor = fields.Float('Factor')

    amount_to_reduce = fields.Float('Cantidad a rebajar')

    indicator_id = fields.Many2one('custom.indicators', string="Indicador")