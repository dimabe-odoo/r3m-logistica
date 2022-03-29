from odoo import fields, models, api
from dateutil.relativedelta import relativedelta as relative
from odoo.tools.config import config
from datetime import date, datetime
from dateutil import relativedelta
from py_linq import Enumerable


class CustomLoan(models.Model):
    _name = 'custom.loan'
    _description = 'Prestamo'
    _inherit = ['mail.thread']
    _rec_name = 'display_name'

    display_name = fields.Char('Nombre a mostrar')

    type_of_loan = fields.Selection([('new', 'Nuevo'), ('in_process', 'En proceso')], default='new',
                                    string='Tipo de Prestamo', required=True)

    employee_id = fields.Many2one('hr.employee', string='Empleado')

    fee_qty = fields.Integer('Cantidad de Cuota', tracking=True)

    fee_value = fields.Monetary('Valor de Cuota', tracking=True)

    fee_remaining = fields.Integer('Cuota Restantes', tracking=True, compute="compute_fee_remaining")

    loan_total = fields.Monetary('Total a prestar', tracking=True)

    currency_id = fields.Many2one('res.currency', string='Moneda',
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'CLP')]))

    date_start = fields.Date(default=datetime.today(),required=True)

    date_start_old = fields.Date()

    interest = fields.Float('Interes')

    fee_ids = fields.One2many('custom.fee', 'loan_id')

    next_fee_id = fields.Many2one('custom.fee', compute='compute_next_fee')

    next_fee_date = fields.Date('Proxima Cuota', related='next_fee_id.expiration_date')

    rule_id = fields.Many2one('hr.salary.rule', string='Regla', domain=[('discount_in_fee', '=', True)],required=True)

    indicator_id = fields.Many2one('custom.indicators', string="Indicador que se inciara")

    state = fields.Selection([('draft', 'Borrador'), ('in_process', 'En Proceso'), ('done', 'Finalizado')],
                             default='draft', tracking=True)
    next_fee_ids = fields.Many2many('custom.fee', compute='compute_next_fee')

    def compute_fee_remaining(self):
        for item in self:
            if item.state == 'in_process':
                item.fee_remaining = len(item.fee_ids.filtered(lambda a: not a.paid))
            else:
                item.fee_remaining = 0

    def compute_next_fee(self):
        for item in self:
            if len(item.fee_ids.filtered(lambda a: not a.paid)) > 0 and item.state != 'done':
                item.next_fee_id = item.fee_ids.filtered(lambda a: not a.paid)[0]
                item.next_fee_ids = item.fee_ids.filtered(lambda a: not a.paid and a.expiration_date == item.next_fee_id.expiration_date)
            else:
                item.next_fee_id = None
                item.next_fee_ids = None

    def write(self, values):
        if 'fee_value' in values.keys():
            if values['fee_value'] == 0:
                raise models.ValidationError('El valor de la cuota debe ser mayor a 0')
        res = super(CustomLoan, self).write(values)

        return res

    def recalculate_loan(self):
        for fee in self.fee_ids:
            fee.unlink()
        if self.type_of_loan == 'new':
            data = self.calculate_fee(loan=self, qty=self.fee_qty)
        else:
            months = self.get_months_diff(date1=self.date_start_old, date2=self.date_start)
            if months > self.fee_qty:
                self.write({
                    'state': 'done'
                })
            data = self.calculate_fee(loan=self,qty=self.fee_qty,months=months)
            self.message_post(
                body=f"Se recalcula prestamo que se encuentra en proceso , la cual se encuentra en la cuota N° {self.next_fee_id.number}")
        self.write({
            'loan_total': data
        })

    def verify_is_complete(self):
        if all(self.fee_ids.mapped('paid')):
            return True
        else:
            return False

    @api.model
    def create(self, values):
        if values['fee_value'] == 0:
            raise models.ValidationError('El valor de la cuota debe ser mayor a 0')
        employee = self.env['hr.employee'].search([('id','=',values['employee_id'])])
        values['display_name'] = f'Prestamo de {employee.display_name}'
        res = super(CustomLoan, self).create(values)
        months = 0

        if res.type_of_loan == 'in_process':
            months = self.get_months_diff(res.date_start_old, res.date_start)
            data = self.calculate_fee(loan=res,qty=res.fee_qty, months=months)
            res.loan_total = round(data)
        else:
            data = self.calculate_fee(loan=res,qty=res.fee_qty)
            res.loan_total = round(data)
        if res.type_of_loan == 'in_process':
            loan = res
            if months > res.fee_qty:
                res.state = 'done'
            res.message_post(
                body=f"Se creado prestamo que se encuentra en proceso , la cual se encuentra en la cuota N° {res.next_fee_id.number}")
        return res

    def get_months_diff(self, date1, date2):
        r = relativedelta.relativedelta(date2, date1)
        print(r)
        months = r.months + (r.years * 12)
        return months

    def button_confirm(self):
        for item in self:
            item.write({
                'state': 'in_process'
            })

    def calculate_fee(self, loan, qty, months=0):
        index = 0
        for fee in range(qty):
            self.env['custom.fee'].create({
                'loan_id': loan.id,
                'value': loan.fee_value,
                'expiration_date': loan.date_start + relative(
                    months=index) if loan.type_of_loan == 'new' else loan.date_start_old + relative(
                    months=index),
                'number': index + 1
            })
            index += 1
        if loan.type_of_loan == 'in_process':
            remaing = 1
            for paid in loan.fee_ids:
                if remaing <= months + 1:
                    paid.write({
                        'paid': True
                    })
                remaing += 1
        return sum(loan.fee_ids.mapped('value'))


