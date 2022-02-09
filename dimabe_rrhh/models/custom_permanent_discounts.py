from odoo import api, fields, models


class CustomPermanentDiscounts(models.Model):
    _name = 'custom.permanent_discounts'

    salary_rule_id = fields.Many2one('hr.salary.rule', string="Regla Salarial",
                                     domain=[('is_permanent_discount', '=', True)])

    amount = fields.Float('Monto')

    contract_id = fields.Many2one('hr.contract', auto_join = True)
