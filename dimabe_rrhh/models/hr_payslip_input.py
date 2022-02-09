from odoo import fields, models, api


class HrPaySlipInput(models.Model):
    _inherit = 'hr.payslip.input'

    additional_info = fields.Char('Información Adicional')

    sale_employee_id = fields.Many2one('custom.sale_employee', 'Venta Interna Empleado')

