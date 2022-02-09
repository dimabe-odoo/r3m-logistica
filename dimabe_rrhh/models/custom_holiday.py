from odoo import models, fields, http
from datetime import datetime
import urllib3
import json
from collections import namedtuple
DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period, week_type')
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
from pytz import timezone, UTC
import math
import pytz
from dateutil.relativedelta import relativedelta

class CustomHolidays(models.Model):
    _name = 'custom.holidays'

    name = fields.Char('Nombre')

    date = fields.Date('Fecha')

    type = fields.Selection([('Civil', 'Civil'), ('Religioso', 'Religioso')])

    inalienable = fields.Boolean('Irrenunciable')

    year = fields.Integer('Año', compute="_compute_year")

    def _compute_year(self):
        for item in self:
            item.year = item.date.year

    def set_holidays_by_year(self, year = None):
        if year == None:
            datetime.now().year
        url = 'https://apis.digital.gob.cl/fl/feriados/{}'.format(str(year))
        http = urllib3.PoolManager()
        res = http.request('GET', url)

        try:
            res = json.loads(res.data.decode('utf-8'))

            if len(res) > 0:
                if len(res) == 2:
                    if 'error' in res.keys() and 'message' in res.keys():
                        if res['error'] == True:
                            raise models.ValidationError('Error: {}'.format(res['message']))
                else:
                    for item in res:
                        if 'nombre' in item and item['nombre'] == 'Todos los Días Domingos':
                            continue
                        if 'fecha' in item:
                            holiday_id = self.env['custom.holidays'].search([('date', '=', item['fecha'])])
                            if len(holiday_id) == 0:
                                self.env['custom.holidays'].create({
                                    'name': item['nombre'],
                                    'date': item['fecha'],
                                    'type': item['tipo'],
                                    'year': datetime.strptime(item['fecha'], '%Y-%m-%d').year,
                                    'inalienable': False if item['irrenunciable'] == '0' else True
                                })
                            # new year
                            if item == res[1]:
                                date = datetime.strptime(item['fecha'], '%Y-%m-%d')
                                new_date = date + relativedelta(years=1)
                                holiday_id = self.env['custom.holidays'].search([('date', '=', new_date)])

                                if len(holiday_id) == 0:
                                    self.env['custom.holidays'].create({
                                        'name': item['nombre'],
                                        'date': new_date,
                                        'type': item['tipo'],
                                        'year': new_date.year,
                                        'inalienable': False if item['irrenunciable'] == '0' else True
                                    })
        except Exception as e:
            return f'{e} Favor contactar con el administrador de Sistema'

        self.generate_holidays(year)

    def get_holidays_by_year(self):
        init_year = self.env['hr.leave.type'].search([('is_vacation', '=', True)], limit=1)
        current_year = datetime.now().year
        error_message = ''
        if not init_year:
            self.set_holidays_by_year(current_year)
        else:
            for i in range(init_year.validity_start.year, current_year + 1):
                res_message = self.set_holidays_by_year(i)
                if res_message and len(res_message) > 0:
                    error_message += f'año: {i} - {res_message} \n'

            if len(error_message) > 0:
                return {
                'warning': {
                    'title': 'Advertencia!',
                    'message': error_message}
                }

    def generate_holidays(self, year):
        custom_holiday_ids = self.env['custom.holidays'].search([]).filtered(lambda x: x.year == year)
        resource_calendar_ids = self.env['hr.employee'].search([]).mapped('resource_calendar_id')
        for resource_calendar_id in resource_calendar_ids:
            for holiday_id in custom_holiday_ids:
                global_leave_id = resource_calendar_id.mapped('global_leave_ids').filtered(lambda x: x.date_from.year == year and x.date_from.month == holiday_id.date.month and x.date_from.day == holiday_id.date.day)
                if not global_leave_id:
                    from_hour = resource_calendar_id.attendance_ids[0].hour_from
                    to_hour = resource_calendar_id.attendance_ids[-1].hour_to

                    from_minutes = (from_hour - int(from_hour)) * 60
                    to_minutes = (to_hour - int(to_hour)) * 60

                    tz = resource_calendar_id.tz

                    leave_date_from = datetime.strptime(
                        f'{holiday_id.date.day}-{holiday_id.date.month}-{holiday_id.date.year} {int(from_hour)}:{int(from_minutes)}:00',
                        '%d-%m-%Y %H:%M:%S')
                    leave_date_to = datetime.strptime(
                        f'{holiday_id.date.day}-{holiday_id.date.month}-{holiday_id.date.year} {int(to_hour)}:{int(to_minutes)}:00',
                        '%d-%m-%Y %H:%M:%S')

                    tz_leave_date_from = fields.Datetime.to_string(
                        pytz.timezone(tz).localize(fields.Datetime.from_string(leave_date_from),
                                                   is_dst=None).astimezone(pytz.utc))
                    tz_leave_date_to = fields.Datetime.to_string(
                        pytz.timezone(tz).localize(fields.Datetime.from_string(leave_date_to),
                                                   is_dst=None).astimezone(pytz.utc))

                    work_entry_id = self.env['hr.work.entry.type'].search([('code', '=', 'LEAVE120')])

                    self.env['resource.calendar.leaves'].create({
                        'name': f'Feriado {year} - {holiday_id.name}',
                        'date_from': tz_leave_date_from,
                        'date_to': tz_leave_date_to,
                        'work_entry_type_id': work_entry_id.id if work_entry_id else None,
                        'calendar_id': resource_calendar_id.id
                    })

    def can_create_leave(self, date, attendance_ids):
        day_of_week = date.weekday()

        attendance_id = attendance_ids.filtered(lambda x: x.dayofweek == str(day_of_week))
        if attendance_id:
            return True
        return False

    #evaluar
    def custom_compute_date_from_to(self, holiday):
        if holiday['request_date_from'] and holiday['request_date_to'] and holiday['request_date_from'] > holiday['request_date_to']:
            holiday['request_date_to'] = holiday['request_date_from']
        if not holiday.request_date_from:
            holiday.date_from = False
        elif not holiday.request_unit_half and not holiday.request_unit_hours and not holiday.request_date_to:
            holiday.date_to = False
        else:
            if holiday.request_unit_half or holiday.request_unit_hours:
                holiday.request_date_to = holiday.request_date_from
            resource_calendar_id = holiday.employee_id.resource_calendar_id or self.env.company.resource_calendar_id
            domain = [('calendar_id', '=', resource_calendar_id.id), ('display_type', '=', False)]
            attendances = self.env['resource.calendar.attendance'].read_group(domain, ['ids:array_agg(id)',
                                                                                       'hour_from:min(hour_from)',
                                                                                       'hour_to:max(hour_to)',
                                                                                       'week_type', 'dayofweek',
                                                                                       'day_period'],
                                                                              ['week_type', 'dayofweek', 'day_period'],
                                                                              lazy=False)

            # Must be sorted by dayofweek ASC and day_period DESC
            attendances = sorted([DummyAttendance(group['hour_from'], group['hour_to'], group['dayofweek'],
                                                  group['day_period'], group['week_type']) for group in attendances],
                                 key=lambda att: (att.dayofweek, att.day_period != 'morning'))

            default_value = DummyAttendance(0, 0, 0, 'morning', False)

            if resource_calendar_id.two_weeks_calendar:
                # find week type of start_date
                start_week_type = int(math.floor((holiday.request_date_from.toordinal() - 1) / 7) % 2)
                attendance_actual_week = [att for att in attendances if
                                          att.week_type is False or int(att.week_type) == start_week_type]
                attendance_actual_next_week = [att for att in attendances if
                                               att.week_type is False or int(att.week_type) != start_week_type]
                # First, add days of actual week coming after date_from
                attendance_filtred = [att for att in attendance_actual_week if
                                      int(att.dayofweek) >= holiday.request_date_from.weekday()]
                # Second, add days of the other type of week
                attendance_filtred += list(attendance_actual_next_week)
                # Third, add days of actual week (to consider days that we have remove first because they coming before date_from)
                attendance_filtred += list(attendance_actual_week)

                end_week_type = int(math.floor((holiday.request_date_to.toordinal() - 1) / 7) % 2)
                attendance_actual_week = [att for att in attendances if
                                          att.week_type is False or int(att.week_type) == end_week_type]
                attendance_actual_next_week = [att for att in attendances if
                                               att.week_type is False or int(att.week_type) != end_week_type]
                attendance_filtred_reversed = list(reversed(
                    [att for att in attendance_actual_week if int(att.dayofweek) <= holiday.request_date_to.weekday()]))
                attendance_filtred_reversed += list(reversed(attendance_actual_next_week))
                attendance_filtred_reversed += list(reversed(attendance_actual_week))

                # find first attendance coming after first_day
                attendance_from = attendance_filtred[0]
                # find last attendance coming before last_day
                attendance_to = attendance_filtred_reversed[0]
            else:
                # find first attendance coming after first_day
                attendance_from = next(
                    (att for att in attendances if int(att.dayofweek) >= holiday.request_date_from.weekday()),
                    attendances[0] if attendances else default_value)
                # find last attendance coming before last_day
                attendance_to = next(
                    (att for att in reversed(attendances) if int(att.dayofweek) <= holiday.request_date_to.weekday()),
                    attendances[-1] if attendances else default_value)

            compensated_request_date_from = holiday.request_date_from
            compensated_request_date_to = holiday.request_date_to

            if holiday.request_unit_half:
                if holiday.request_date_from_period == 'am':
                    hour_from = float_to_time(attendance_from.hour_from)
                    hour_to = float_to_time(attendance_from.hour_to)
                else:
                    hour_from = float_to_time(attendance_to.hour_from)
                    hour_to = float_to_time(attendance_to.hour_to)
            elif holiday.request_unit_hours:
                hour_from = float_to_time(float(holiday.request_hour_from))
                hour_to = float_to_time(float(holiday.request_hour_to))
            elif holiday.request_unit_custom:
                hour_from = holiday.date_from.time()
                hour_to = holiday.date_to.time()
                compensated_request_date_from = holiday._adjust_date_based_on_tz(holiday.request_date_from, hour_from)
                compensated_request_date_to = holiday._adjust_date_based_on_tz(holiday.request_date_to, hour_to)
            else:
                hour_from = float_to_time(attendance_from.hour_from)
                hour_to = float_to_time(attendance_to.hour_to)

            holiday.date_from = timezone(holiday.tz).localize(
                datetime.combine(compensated_request_date_from, hour_from)).astimezone(UTC).replace(tzinfo=None)
            holiday.date_to = timezone(holiday.tz).localize(
                datetime.combine(compensated_request_date_to, hour_to)).astimezone(UTC).replace(tzinfo=None)

        return holiday
