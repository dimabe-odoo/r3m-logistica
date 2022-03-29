import datetime
from dateutil import rrule
from datetime import timedelta, time
from odoo import api, models, fields
import pytz
from dateutil.relativedelta import relativedelta

class CustomVacation(models.Model):
    _name = 'custom.vacation'
    _rec_name = 'employee_id'
    _description = "Vacaciones"

    employee_id = fields.Many2one('hr.employee', 'Empleado', required=True)

    contract_id = fields.Many2one('hr.contract', string='Contrato', required=True)

    date_start = fields.Date('Fecha de inicio', related="contract_id.date_start")

    max_vacations = fields.Integer('Máximo de Días de Vacaciones', help="Máximo de Días de Vacaciones por Año", compute="_compute_max_vacations")

    vacations_remaining = fields.Integer('Días Restantes', help="Días de Vacaciones Restantes", compute="_compute_vacations_data", default=0)

    vacations_history_total = fields.Integer('Días de Vacaciones Historicos', compute="_compute_vacations_data",  help="Días de vacaciones historicos generados")

    leave_type_id = fields.Many2one('hr.leave.type', 'Tipo de Ausencia', required=True)

    leave_allocation_line_ids = fields.One2many('hr.leave.allocation', 'vacation_id', 'Asignaciones')

    leave_ids = fields.One2many('hr.leave', 'vacation_id', 'Vacaciones')

    period_ids = fields.One2many('custom.contract_period', 'vacation_id')

    progressive_vacation_by_period = fields.Integer('Vacaciones Progresivas por Periodo', compute="_compute_get_progressive_vacation")

    leave_date_from = fields.Date('Desde')

    leave_date_to = fields.Date('hasta')

    leave_name = fields.Char('Descripción')

    leave_period_id = fields.Many2one('custom.contract_period', 'Periodo')

    leave_number_of_days = fields.Float('N° Días', compute="_compute_number_of_days")

    @api.depends('leave_date_from', 'leave_date_to', 'employee_id')
    def _compute_number_of_days(self):
        for item in self:
            if item.leave_date_from and item.leave_date_to:
                from_hour = int(item.contract_id.resource_calendar_id.attendance_ids[0].hour_from)
                to_hour = int(item.contract_id.resource_calendar_id.attendance_ids[-1].hour_to)

                from_minutes = (from_hour - int(from_hour)) * 60
                to_minutes = (to_hour - int(to_hour)) * 60

                leave_date_from = datetime.datetime.strptime(
                    f'{item.leave_date_from.day}/{item.leave_date_from.month}/{item.leave_date_from.year} {from_hour}:{from_minutes}:00',
                    '%d/%m/%Y %H:%M:%S')
                leave_date_to = datetime.datetime.strptime(
                    f'{item.leave_date_to.day}/{item.leave_date_to.month}/{item.leave_date_to.year} {to_hour}:{to_minutes}:00',
                    '%d/%m/%Y %H:%M:%S')

                tz = item.employee_id.tz

                tz_leave_date_from = pytz.timezone(tz).localize(fields.Datetime.from_string(leave_date_from),
                                                                is_dst=None).astimezone(pytz.utc)
                tz_leave_date_to = pytz.timezone(tz).localize(fields.Datetime.from_string(leave_date_to),
                                                              is_dst=None).astimezone(pytz.utc)
                item.leave_number_of_days = item.employee_id._get_work_days_data_batch(tz_leave_date_from, tz_leave_date_to)[item.employee_id.id]['days']
            else:
                item.leave_number_of_days = 0

    def _compute_vacations_data(self):
        for item in self:
            item.vacations_remaining = int(sum(line.number_of_days for line in item.leave_allocation_line_ids.filtered(lambda x: x.consumed_state == 'to_consume')))
            item.vacations_history_total = int(sum(line.number_of_days for line in item.leave_allocation_line_ids))

    def _compute_max_vacations(self):
        for item in self:
            item.max_vacations = 0
            if self.env.user.company_id.vacation_day_for_month:
                item.max_vacations = self.env.user.company_id.vacation_day_for_month * 12 + item.progressive_vacation_by_period
            else:
                raise models.ValidationError(f'No se encuentra registrado los días de vacaiones por Año en la compañia {self.env.user.company_id.name}')

    def update_vacation_lines(self):
        for item in self:
            if item.date_start:
                date_now = datetime.date.today()
                date_start = item.date_start + relativedelta(months=1)
                months = rrule.rrule(rrule.MONTHLY, dtstart=date_start, until=date_now).count()
                if date_start.day > date_now.day and date_now.month == date_start.month:
                    months -= 1

                year = date_start.year
                month = date_start.month
                day = date_start.day

                for seq in range(months):
                    if year <= date_now.year:
                        if seq == months and day > date_now.day:
                            continue

                        leave_allocation_id = self.env['hr.leave.allocation'].search([('employee_id','=',item.employee_id.id), ('holiday_status_id', '=', item.leave_type_id.id), ('vacation_id', '=', item.id)])
                        leave_allocation_id = leave_allocation_id.filtered(lambda x: x.date_from.day == day and x.date_from.month == month and x.date_from.year == year)
                        if not leave_allocation_id:
                            number_of_days = self.env.user.company_id.vacation_day_for_month
                            if item.contract_id.first_progressive_vacation_date:
                                if item.contract_id.first_progressive_vacation_date.day == date_start.day and item.contract_id.first_progressive_vacation_date.month == month and item.contract_id.first_progressive_vacation_date.year == year:
                                    number_of_days += 1

                                else:
                                    number_of_days += self.get_progressive_vacation(day, month)

                            hour_from = self.contract_id.resource_calendar_id.mapped('attendance_ids')[0].hour_from
                            from_minutes = (hour_from - int(hour_from)) * 60
                            date_from = datetime.datetime.strptime(f'{day}-{month}-{year} {int(hour_from)}:{int(from_minutes)}:00','%d-%m-%Y %H:%M:%S')

                            if self.env.context['tz']:
                                tz = self.env.context['tz']
                            else:
                                tz = item.employee_id.tz

                            tz_date_from = fields.Datetime.to_string(pytz.timezone(tz).localize(fields.Datetime.from_string(date_from), is_dst=None).astimezone(pytz.utc))

                            new_leave_allocation_id = self.env['hr.leave.allocation'].create({
                                'name': f'Asignación día de vacación {date_start.day}-{month}-{year}',
                                'holiday_status_id': item.leave_type_id.id,
                                'holiday_type': 'employee',
                                'employee_id': item.employee_id.id,
                                'allocation_type': 'regular',
                                'number_of_days': number_of_days,
                                'date_from': tz_date_from,
                                'vacation_id': item.id
                            })
                            new_leave_allocation_id.action_approve()

                    if month == 12:
                        month = 0
                        year += 1

                    month += 1


            leave_allocation_ids = self.env['hr.leave.allocation'].search([('employee_id','=', item.employee_id.id), ('holiday_status_id','=',item.leave_type_id.id), ('state', 'in', ['validate','validate1'])]).sorted(key=lambda x: x.date_from)
            years = []
            for allocation in leave_allocation_ids:
                if allocation.date_from.year not in years:
                    years.append(allocation.date_from.year)

            period_number = 1
            for year in years:
                start_period = leave_allocation_ids.filtered(lambda x: x.date_from.day == date_start.day and x.date_from.month == date_start.month and x.date_from.year == year)
                first_period = False
                contract_period_ids = self.env['custom.contract_period'].search([('vacation_id', '=', item.id), ('employee_id', '=', item.employee_id.id), ('contract_id', '=', item.contract_id.id)])
                if len(contract_period_ids) == 0:
                    first_period = True

                if start_period or first_period:
                    period_id = self.env['custom.contract_period'].search([('employee_id','=',item.employee_id.id), ('contract_id', '=', item.contract_id.id)])
                    period_id = period_id.filtered(lambda x: x.date_start.day == item.date_start.day and x.date_start.month == item.date_start.month and x.date_start.year == year)
                    if not period_id:
                        self.env['custom.contract_period'].create({
                            'employee_id': item.employee_id.id,
                            'contract_id': item.contract_id.id,
                            'date_start': datetime.datetime.strptime(f'{item.date_start.day}-{item.date_start.month}-{year}', '%d-%m-%Y').date(),
                            'date_finish': datetime.datetime.strptime(f'{item.date_start.day}-{item.date_start.month}-{year + 1}', '%d-%m-%Y').date(),
                            'period_number': period_number,
                            'vacation_id': item.id
                        })
                period_number += 1


            for line in leave_allocation_ids:
                period_ids = self.env['custom.contract_period'].search([('employee_id', '=', item.employee_id.id),('contract_id', '=', item.contract_id.id)]).sorted(lambda x: x.date_start)
                for period in period_ids:
                    if period.date_start <= line.date_from.date() <= period.date_finish:
                        line.write({
                            'period_id': period.id
                        })
                        break



    def get_progressive_vacation(self, day, month):
        progressive_vacation = 0
        if self.employee_id.contract_id.type_id.code == '3':
            if day == self.contract_id.date_start.day and self.contract_id.date_start.month == month:
                    progressive_vacation = self.progressive_vacation_by_period
        return progressive_vacation


    def _compute_get_progressive_vacation(self):
        for item in self:
            progressive_vacation_by_period = 0
            first_progressive_vacation_date = item.employee_id.contract_id.first_progressive_vacation_date
            if first_progressive_vacation_date:
                allocation_ids = item.leave_allocation_line_ids
                if len(allocation_ids.filtered(lambda x: x.date_from.date() < first_progressive_vacation_date)):
                    progressive_vacation_by_period = 0

                before_allocation_ids = allocation_ids.filtered(lambda x: x.date_from.date() >= first_progressive_vacation_date)
                if len(before_allocation_ids) > 0:
                    progressive_vacation_by_period = int(len(before_allocation_ids) / 12) + 1
                    '''
                    if len(before_allocation_ids) < 36:
                        progressive_vacation_by_period = 1
                    if 36 <= len(before_allocation_ids) < 72:
                        progressive_vacation_by_period = 2
                    if len(before_allocation_ids) >= 72:
                        progressive_vacation_by_period = 3
                        
                    '''

            item.progressive_vacation_by_period = progressive_vacation_by_period

    def update_vacations_lines(self):
        vacation_ids = self.env['custom.vacation'].search([])
        for vacation in vacation_ids:
            if vacation.contract_id.state == 'open':
                vacation.update_vacation_lines()

    @api.model
    def create(self, values):
        vacation_id = self.env['custom.vacation'].search([('employee_id', '=', values['employee_id']), ('contract_id', '=', values['contract_id'])])

        if vacation_id:
            raise models.ValidationError(f'No se puede crear el control de vacaciones.\nYa existe un control de vacaciones para {vacation_id.employee_id.display_name} con el contrato {vacation_id.contract_id.name}')

        return super(CustomVacation, self).create(values)

    def generate_leave(self):
        hour_to = self.contract_id.resource_calendar_id.mapped('attendance_ids')[-1].hour_to
        hour_from = self.contract_id.resource_calendar_id.mapped('attendance_ids')[0].hour_from

        from_minutes = (hour_from - int(hour_from)) * 60
        to_minutes = (hour_to - int(hour_to)) * 60

        leave_date_from = datetime.datetime.strptime(f'{self.leave_date_from.day}-{self.leave_date_from.month}-{self.leave_date_from.year} {int(hour_from)}:{int(from_minutes)}:00', '%d-%m-%Y %H:%M:%S')
        leave_date_to = datetime.datetime.strptime(f'{self.leave_date_to.day}-{self.leave_date_to.month}-{self.leave_date_to.year} {int(hour_to)}:{int(to_minutes)}:00', '%d-%m-%Y %H:%M:%S')

        tz_leave_date_from = fields.Datetime.to_string(pytz.timezone(self.env.context['tz']).localize(fields.Datetime.from_string(leave_date_from), is_dst=None).astimezone(pytz.utc))
        tz_leave_date_to = fields.Datetime.to_string(pytz.timezone(self.env.context['tz']).localize(fields.Datetime.from_string(leave_date_to), is_dst=None).astimezone(pytz.utc))

        name = 'Vacación'

        if self.leave_period_id and self.leave_period_id.vacation_days_remaining < self.leave_number_of_days:
            raise models.ValidationError(f'No quedan días disponibles para el periodo seleccionado.\n\n{self.leave_period_id.display_name}')

        if self.leave_name:
            name = self.leave_name

        vacation_days_remaining = self.leave_period_id.vacation_days - self.leave_period_id.vacation_days_consumed - self.leave_number_of_days
        leave_id = self.env['hr.leave'].create({
            'name': name,
            'date_from': tz_leave_date_from,
            'date_to': tz_leave_date_to,
            'request_date_from': tz_leave_date_from,
            'request_date_to': tz_leave_date_to,
            'holiday_type': 'employee',
            'employee_id': self.employee_id.id,
            'contract_id': self.contract_id.id,
            'holiday_status_id': self.leave_type_id.id,
            'vacation_id': self.id,
            'period_id': self.leave_period_id.id,
            'vacation_days_remaining': int(vacation_days_remaining)
        })

        self.write({
            'leave_date_from': None,
            'leave_date_to': None,
            'leave_name': None,
            'leave_period_id': None
        })