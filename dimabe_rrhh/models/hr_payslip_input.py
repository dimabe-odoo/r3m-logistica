from odoo import fields, models, api


class HrPaySlipInput(models.Model):
    _inherit = 'hr.payslip.input'

    additional_info = fields.Char('Información Adicional')

    sale_employee_id = fields.Many2one('custom.sale_employee', 'Venta Interna Empleado')

    category_id = fields.Many2one(
        comodel_name='hr.salary.rule.category',
        string='Categoria',
        required=False)


class HrPaySlipInputType(models.Model):
    _inherit = 'hr.payslip.input.type'

    category_id = fields.Many2one(
        comodel_name='hr.salary.rule.category',
        string='Categoria',
        required=False)

    @api.model
    def create(self, values):
        result = super(HrPaySlipInputType, self).create(values)
        for res in result:
            rule = self.env['hr.salary.rule'].sudo().search([('code', '=', res.code)])
            if not rule:
                self.env['hr.salary.rule'].sudo().create({
                    'name': res.name,
                    'code': res.code,
                    'condition_select': 'python',
                    'condition_python': f'result = (inputs.{res.code} and inputs.{res.code}.amount > 0)',
                    'amount_select': 'code',
                    'amount_python_compute': f'result = inputs.{res.code}.amount',
                    'struct_id': res.struct_ids[0].id if len(res.struct_ids) > 0 else None,
                    'category_id': res.category_id.id,
                })
        return result