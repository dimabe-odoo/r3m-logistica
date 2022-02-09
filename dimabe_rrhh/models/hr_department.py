from odoo import fields, models, api

class HrDepartment(models.Model):
    _inherit = 'hr.department'
    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos')


