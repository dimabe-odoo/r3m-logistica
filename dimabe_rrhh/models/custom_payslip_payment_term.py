from odoo import models,fields

class CustomPayslipPaymentTerm(models.Model):
    _name = 'custom.payslip.payment.term'

    name = fields.Char('Forma de Pago')