from odoo import models,fields,api

class HrSalaryRule(models.Model):
    _inherit = 'res.company'

    analitic_account = fields.Selection([('1', 'Nómina'),('2', 'Contrato'),('3', 'Departamento')],'Origen Cuenta Analítica', default='3', help="Origen de Cuenta Analitica por Nómina, Contrato o Departamento, para Libro de Remuneraciones")

    sale_employee_payment_term_id = fields.Many2one('account.payment.term', 'Método de Pago Venta Interna')

    sale_employee_journal_id = fields.Many2one('account.journal', 'Diario Venta Interna')

    vacation_day_for_month = fields.Float('Días de vacaciones por mes')

    min_licence_days = fields.Integer('Mínimo de días de Licencia para no Descontar', help="Mínimo de días de licencia, para no Descontar Prestamos y Descuentos fijos")

    legal_representative_id = fields.Many2one('res.partner', 'Representante Legal')
