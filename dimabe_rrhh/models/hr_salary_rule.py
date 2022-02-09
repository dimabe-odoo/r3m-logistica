from odoo import models,fields,api

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    is_bonus = fields.Boolean('Ingreso Manual')

    show_in_book = fields.Boolean('Aparece en el libro de remuneraciones', default=True)

    discount_in_fee = fields.Boolean('Descuento en Cuota')

    is_permanent_discount = fields.Boolean('Descuento Fijo/Permanente')

    category_code = fields.Char('Código Categoría', related="category_id.code")

    is_other_savings = fields.Boolean('Otro Ahorro')

    order_number = fields.Integer('Secuencia en Libro de Remuneraciones')

    available_to_settlement = fields.Boolean('Disponible en Finiquito')

    @api.onchange('is_bonus')
    def onchange_method(self):
        #if not self.code:
        #    raise models.UserError('No pude definir un bono sin definir el codigo primero')
        if self.is_bonus:
            self.write({
                'condition_select':'python',
                'condition_python':f'result = (inputs.{self.code} and inputs.{self.code}.amount > 0)',
                'amount_select':'code',
                'amount_python_compute':f'result = inputs.{self.code}.amount'
            })

    @api.onchange('is_permanent_discount')
    def onchange_method_is_permanent_discount(self):
        if self.is_permanent_discount:
            self.write({
                'condition_select': 'python',
                'condition_python': f'result = (inputs.{self.code} and inputs.{self.code}.amount > 0)',
                'amount_select': 'code',
                'amount_python_compute': f'result = inputs.{self.code}.amount'
            })

    @api.onchange('is_other_savings')
    def onchange_method_is_other_saving(self):
        if self.is_other_savings:
            self.write({
                'condition_select': 'python',
                'condition_python': f'result = (inputs.{self.code} and inputs.{self.code}.amount > 0)',
                'amount_select': 'code',
                'amount_python_compute': f'result = inputs.{self.code}.amount'
            })
