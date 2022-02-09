from odoo import fields, api, models

class CustomleaveAllocationPeriod(models.Model):
    _name = 'custom.leave_allocation_period'

    consumed_in_period_id = fields.Many2one('custom.contract_period', string='Consumido en el Periodo', related='leave_id.period_id')

    leave_id = fields.Many2one('hr.leave')

    allocation_id = fields.Many2one('hr.leave.allocation')

    day_consumed = fields.Float('Días Consumidos')