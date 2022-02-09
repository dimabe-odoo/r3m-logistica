from odoo import models, api, fields

class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    vacation_id = fields.Many2one('custom.vacation')
    consumed_state = fields.Selection([('to_consume', 'Por Consumir'),('partial', 'Parcial'), ('consumed', 'Consumido')], 'Estado', compute="_compute_consumed_state", default='to_consume')
    period_id = fields.Many2one('custom.contract_period', 'Periodo')
    day_consumed = fields.Float('Días Consumidos', default=0)
    consumed_in_period = fields.Char('Periodo de Consumo', compute="_compute_consumed_period")

    def consume_allocation(self):
        if self.consumed_state != 'consumed' and self.state in ['validate', 'validate1']:
            self.write({
                'consumed_state': 'consumed'
            })
            
    def action_refuse(self):
        if self.consumed_state == 'consumed':
            raise models.ValidationError('No se puede Rechazar\nAsignación se ecuentra consumida')
        
        return super(HrLeaveAllocation, self).action_refuse()

    @api.depends('day_consumed')
    def _compute_consumed_state(self):
        for item in self:
            item.consumed_state = 'to_consume'
            if item.day_consumed == item.number_of_days:
                item.consumed_state = 'consumed'
            elif item.number_of_days > item.day_consumed > 0:
                item.consumed_state = 'partial'
            else:
                item.consumed_state = 'to_consume'

    def _compute_consumed_period(self):
        for item in self:
            consumed_in_period = ''
            leave_allocation_period = self.env['custom.leave_allocation_period'].search([('allocation_id', '=', item.id)])
            if leave_allocation_period:
                if len(leave_allocation_period) > 0:
                    period_ids = leave_allocation_period.mapped('consumed_in_period_id')
                    for period_id in period_ids:
                        day_consumed = sum(line.day_consumed for line in  self.env['custom.leave_allocation_period'].search([('allocation_id', '=', item.id)]).filtered(lambda x: x.consumed_in_period_id.id == period_id.id ))
                        consumed_in_period += 'Periodo N°' + str(period_id.period_number) + '(' + str(day_consumed) +')'
                        if period_id != period_ids[-1]:
                            consumed_in_period += ' - '

            item.consumed_in_period = consumed_in_period