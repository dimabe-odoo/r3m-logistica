from odoo import models, fields, api

class HrPayslipWorkedDays(models.Model):

    _inherit = 'hr.payslip.worked_days'

    number_of_days = fields.Float(readonly=False)

    @api.onchange('number_of_days')
    def _onchange_number_of_days(self):
        for item in self:
            days_not_working = item.payslip_id.contract_id.resource_calendar_id.full_days_on_month - item.number_of_days
            item.number_of_hours = (item.payslip_id.contract_id.resource_calendar_id.effective_days_on_month - days_not_working) * item.payslip_id.contract_id.resource_calendar_id.hours_per_day

    @api.depends('number_of_hours')
    def _compute_amount(self):
        for item in self:
            res = super(HrPayslipWorkedDays, self)._compute_amount()
            item.amount = item.payslip_id.contract_id.wage / 30 * item.number_of_days
            return res


    
