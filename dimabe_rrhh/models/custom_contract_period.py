from odoo import models, fields, api

class CustomContractPeriod(models.Model):
    _name = 'custom.contract_period'
    _rec_name = 'display_name'
    _description = "Periodo del Contrato"
    _order = 'date_start desc'

    employee_id = fields.Many2one('hr.employee', 'Empleado')

    contract_id = fields.Many2one('hr.contract', 'Contrato')

    period_number = fields.Integer('N° Periodo')

    date_start = fields.Date('Fecha Inicio')

    date_finish = fields.Date('Fecha Termino')

    vacation_id = fields.Many2one('custom.vacation')

    vacation_days = fields.Integer('Días Registrados', compute="_compute_vacation_days")

    vacation_days_consumed = fields.Integer('Días Consumidos', compute="_compute_vacation_days")

    vacation_days_remaining = fields.Integer('Días Restantes', compute="_compute_vacation_days")

    display_name = fields.Char('Referencia', compute="_compute_display_name")

    vacation_days_to_approve = fields.Float('Días por Aprobar',  compute="_compute_vacation_days")

    full_day_consumed = fields.Boolean('Periodo Completo Consumido', compute="_compute_full_day_consumed", default=False, store=True)

    def _compute_vacation_days(self):
        for item in self:
            leave_allocation_ids = self.env['hr.leave.allocation'].search([('employee_id', '=', item.employee_id.id)]).filtered(lambda x: x.period_id.id == item.id)
            item.vacation_days = sum(line.number_of_days for line in leave_allocation_ids)
            leave_ids = self.env['hr.leave'].search([('period_id', '=', item.id), ('state', 'in', ['validate', 'validate1'])])
            item.vacation_days_consumed = sum(line.number_of_days for line in leave_ids)
            item.vacation_days_to_approve = 0
            tmpl_leave_ids = self.env['hr.leave'].search([('period_id', '=', item.id),  ('state', '=', 'confirm')])
            if tmpl_leave_ids:
                item.vacation_days_to_approve = sum(tmpl_days.number_of_days for tmpl_days in tmpl_leave_ids)
            item.vacation_days_remaining = item.vacation_days - item.vacation_days_consumed - item.vacation_days_to_approve

    def _compute_display_name(self):
        for item in self:
            date_start = item.date_start.strftime("%d/%m/%Y")
            date_finish = item.date_finish.strftime("%d/%m/%Y")
            days_to_approve = ''
            if item.vacation_days_to_approve > 0:
                days_to_approve = f' (Días por Aprobar: {int(item.vacation_days_to_approve)})'
            item.display_name = f'Periodo N°{item.period_number}:  {date_start} - {date_finish}  (Días Restantes: {item.vacation_days_remaining}){days_to_approve}'

    @api.depends('vacation_days_remaining')
    def _compute_full_day_consumed(self):
        for item in self:
            if item.vacation_days_remaining == 0:
                item.full_day_consumed = True