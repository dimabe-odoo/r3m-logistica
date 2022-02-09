from odoo import models, fields, api
from datetime import datetime


class HrLeave(models.Model):
    _inherit = 'hr.leave'
    _order = 'date_from desc'

    approve_date = fields.Date('Fecha de Aprobación')
    contract_id = fields.Many2one('hr.contract', 'Contrato')
    vacation_id = fields.Many2one('custom.vacation')
    period_start = fields.Date('Periodo Desde', related="period_id.date_start")
    period_finish = fields.Date('Periodo Hasta', related="period_id.date_finish")
    period_id = fields.Many2one('custom.contract_period', 'Periodo')
    vacation_days_remaining = fields.Integer('Saldo')


    def get_date_str(self, date):

        month = ''
        if date.strftime('%m') == '01':
            month = 'enero'
        if date.strftime('%m') == '02':
            month = 'febrero'
        if date.strftime('%m') == '03':
            month = 'marzo'
        if date.strftime('%m') == '04':
            month = 'abril'
        if date.strftime('%m') == '05':
            month = 'mayo'
        if date.strftime('%m') == '06':
            month = 'junio'
        if date.strftime('%m') == '07':
            month = 'julio'
        if date.strftime('%m') == '08':
            month = 'agosto'
        if date.strftime('%m') == '09':
            month = 'septiembre'
        if date.strftime('%m') == '10':
            month = 'octubre'
        if date.strftime('%m') == '11':
            month = 'noviembre'
        if date.strftime('%m') == '12':
            month = 'diciembre'
        day = date.strftime('%d')
        year = date.strftime('%Y')

        return f'{day} de {month} del {year}'

    def action_approve(self):
        if self.holiday_status_id.is_vacation:
            if self.period_id:
                if self.period_id.vacation_days - self.period_id.vacation_days_consumed > 0:
                    vacation_id = self.env['custom.vacation'].search(
                        [('employee_id', '=', self.employee_id.id), ('contract_id', '=', self.contract_id.id)])
                    if vacation_id:
                        if self.state == 'confirm':
                            self.write({
                                'approve_date': datetime.now().date()
                            })

                        allocation_ids = self.env['hr.leave.allocation'].search(
                            [('employee_id', '=', self.employee_id.id),
                             ('holiday_status_id', '=', self.holiday_status_id.id),
                             ('state', 'in', ['validate', 'validate1'])]).filtered(
                            lambda x: x.consumed_state in ['to_consume', 'partial']).sorted(lambda x: x.date_from)

                        days_to_consume = self.number_of_days
                        for allocation in allocation_ids:
                            if days_to_consume > 0:

                                if allocation.number_of_days - allocation.day_consumed == 0:
                                    continue

                                day_consumed = allocation.number_of_days - allocation.day_consumed

                                if day_consumed > days_to_consume:
                                    day_consumed = days_to_consume

                                allocation.write({
                                    'day_consumed': allocation.day_consumed + day_consumed
                                })

                                self.env['custom.leave_allocation_period'].create({
                                    'day_consumed': day_consumed,
                                    'leave_id': self.id,
                                    'allocation_id': allocation.id
                                })
                                days_to_consume -= day_consumed

                            else:
                                break

                        if self.period_id.vacation_days - self.period_id.vacation_days_consumed - self.number_of_days == 0:
                            self.period_id.write({
                                'full_day_consumed': True
                            })

                    else:
                        raise models.ValidationError(
                            f'No se puede registrar Ausencia {self.holiday_status_id.name}\nNo existe un Control de Vacaciones para el Empleado: {self.employee_id.name}\nContrato: {self.contract_id.name}')
                else:
                    raise models.ValidationError(f'No existen días disponbiles para el {self.period_id.display_name}')
            else:
                raise models.ValidationError('Favor Ingresar el Periodo')

        return super(HrLeave, self).action_approve()

    def action_refuse(self):
        for item in self:
            res = super(HrLeave, item).action_refuse()
            leave_allocation_period_ids = self.env['custom.leave_allocation_period'].search([('leave_id', '=', item.id)])
            number_of_days = item.number_of_days
            for allocation in leave_allocation_period_ids.mapped('allocation_id'):
                if number_of_days > 0:
                    leave_allocation_period_id = self.env['custom.leave_allocation_period'].search(
                        [('leave_id', '=', item.id), ('allocation_id', '=', allocation.id)])
                    if leave_allocation_period_id:
                        new_day_consumed = allocation.day_consumed - leave_allocation_period_id.day_consumed
                        allocation.write({
                           'day_consumed':  new_day_consumed
                        })
                        leave_allocation_period_id.unlink()

                if allocation.period_id.full_day_consumed:
                    allocation.period_id.write({
                        'full_day_consumed': False
                    })

            return res

    def get_not_valid_days(self):
        real_days = (self.date_to - self.date_from).days + 1
        not_valid_days = real_days - self.number_of_days
        return not_valid_days

    def generate_report(self):
        return self.env.ref('dimabe_rrhh.report_vacation_action').report_action(self)

    def get_vacation_progressive_to_report(self):
        leave_allocation_ids = self.env['hr.leave.allocation'].search([('period_id', '=', self.period_id.id)])

        sum_days = sum(allocation.number_of_days_display for allocation in leave_allocation_ids)

        return sum_days - self.env.user.company_id.vacation_day_for_month * len(leave_allocation_ids)


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    is_vacation = fields.Boolean('Es Vacación')


class LeaveReportCalendar(models.Model):
    _inherit = "hr.leave.report.calendar"

    description_leave = fields.Char('Descripción', compute="_compute_description_name")

    @api.depends('employee_id', 'start_datetime', 'stop_datetime')
    def _compute_description_name(self):
        for item in self:
            item.description_leave = ''
            hr_leave_id = self.env['hr.leave'].search(
                [('employee_id', '=', item.employee_id.id), ('date_from', '=', item.start_datetime),
                 ('date_to', '=', item.stop_datetime)])
            if hr_leave_id:
                item.description_leave = hr_leave_id.private_name
