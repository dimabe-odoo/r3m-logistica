from odoo import api, fields, models


class CustomOtherSavings(models.Model):
    _name = 'custom.other_savings'

    salary_rule_id = fields.Many2one('hr.salary.rule', string="Regla Salarial",
                                     domain=[('is_other_savings', '=', True)])

    amount = fields.Float('Monto')

    contract_saving_id = fields.Many2one('hr.contract', auto_join = True)

    currency = fields.Selection([('uf', 'UF'), ('clp', 'Pesos')], string='Tipo de Moneda', default="uf")