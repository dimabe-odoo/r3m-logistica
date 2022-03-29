from odoo import fields, models, api
from datetime import datetime


class CustomPersonalMovements(models.Model):
    _name = 'custom.personal.movements'
    _description = "Movimiento de Personal"

    personal_movements = fields.Selection([('0', 'Sin Movimiento en el Mes'),
                                           ('1', 'Contratación a plazo indefinido'),
                                           ('2', 'Retiro'),
                                           ('3', 'Subsidios (L Médicas)'),
                                           ('4', 'Permiso Sin Goce de Sueldos'),
                                           ('5', 'Incorporación en el Lugar de Trabajo'),
                                           ('6', 'Accidentes del Trabajo'),
                                           ('7', 'Contratación a plazo fijo'),
                                           ('8', 'Cambio Contrato plazo fijo a plazo indefinido'),
                                           ('11', 'Otros Movimientos (Ausentismos)'),
                                           ('12', 'Reliquidación, Premio, Bono')
                                           ], 'Movimientos Personal', default="0")

    date_start = fields.Date('Fecha Inicio')

    date_end = fields.Date('Fecha Final')

    payslip_id = fields.Many2one('hr.payslip', auto_join=True)

    days = fields.Integer('Días', compute="_compute_days")

    line_type = fields.Selection([('00', 'Línea Principal o Base'),
                                  ('01', 'Línea Adicional'),
                                  ('02', 'Segundo Contrato'),
                                  ('03', 'Movimiento de Personal Afiliado Voluntario')], 'Tipo de Línea')


    @api.model
    def create(self, values):
        main_line_type = self.env['custom.personal.movements'].search([('payslip_id', '=', values['payslip_id']), ('line_type', '=', '00')])
        if 'line_type' in values.keys():
            if values['line_type'] == '00' and main_line_type:
                raise models.ValidationError('Ya existe un movimiento personal de tipo Línea Principal o Base')
        if 'date_start' in values.keys() and 'date_end' in values.keys():
            date_start = fields.Date.from_string(values['date_start'])
            date_end = fields.Date.from_string(values['date_end'])
            if date_start > date_end:
                raise models.UserError('La fecha inicio no puede ser mayor a la fecha final')
            movement = self.env['custom.personal.movements'].search(
                [('personal_movements', '=', values['personal_movements']), ('payslip_id', '=', values['payslip_id'])])
            if movement:
                if date_start <= movement.date_end <= date_end or date_start >= movement.date_start >= date_end:
                    raise models.UserError('Ya existe un movimiento personal vigente en el rango de fecha ingresado')

        res = super(CustomPersonalMovements, self).create(values)
        return res

    def write(self, values):
        if 'line_type' in values.keys():
            if values['line_type'] == '00':
                main_line_type = self.env['custom.personal.movements'].search(
                    [('payslip_id', '=', self.payslip_id.id), ('line_type', '=', '00')])
                if main_line_type:
                    raise models.ValidationError('Ya existe un movimiento personal de tipo Línea Principal o Base')

        date_start = self.date_start
        date_end = self.date_end
        if 'date_start' in values.keys():
            date_start = fields.Date.from_string(values['date_start'])
        if 'date_end' in values.keys():
            date_end = fields.Date.from_string(values['date_end'])
        if date_start > date_end:
            raise models.UserError('La fecha inicio no puede ser mayor a la fecha final')

        return super(CustomPersonalMovements, self).write(values)

    def _compute_days(self):
        for item in self:
            item.days = 0
            if item.date_end and item.date_start and item.personal_movements != '2':
                days = int((item.date_end - item.date_start).days) + 1
                if days > 30:
                    days = 30
                item.days = days