from odoo import models,fields

class CustomPayslipPaymentTerm(models.Model):
    _name = 'custom.payslip.payment.term'
    _description = "Forma de Pago Nomina"

    name = fields.Char('Forma de Pago')