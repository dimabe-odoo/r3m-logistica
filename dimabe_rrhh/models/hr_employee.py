from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_type_id = fields.Many2one('custom.employee.type', 'Tipo de Empleado')

    first_name = fields.Char("Nombre")

    last_name = fields.Char("Apellido")

    middle_name = fields.Char("Segundo Nombre", help='Employees middle name')

    mothers_name = fields.Char("Segundo Apellido", help='Employees mothers name')

    marital = fields.Selection(selection_add=[('civilunion', 'Unión Civil')])

    @api.model
    def _get_computed_name(self, last_name, first_name, last_name2=None, middle_name=None):
        names = []
        if first_name:
            names.append(first_name)
        if middle_name:
            names.append(middle_name)
        if last_name:
            names.append(last_name)
        if last_name2:
            names.append(last_name2)
        return " ".join(names)

    @api.onchange('first_name', 'mothers_name', 'middle_name', 'last_name')
    def get_name(self):
        if self.first_name and self.last_name:
            self.name = self._get_computed_name(self.last_name, self.first_name, self.mothers_name, self.middle_name)

    def generate_vacation_by_employee(self):
        vacation_id = self.env['custom.vacation'].search([('employee_id', '=', self.id)])

        if not vacation_id:
            contract_id = self.env['hr.contract'].search(
                [('employee_id', '=', self.id), ('state', '!=', 'cancel')])
            leave_type_id = self.env['hr.leave.type'].search([('is_vacation', '=', True)])
            vacation_id = self.env['custom.vacation'].create({
                'employee_id': self.id,
                'contract_id': contract_id.id,
                'leave_type_id': leave_type_id[0].id
            })

            vacation_id.update_vacation_lines()

    def get_reverse_full_name(self):
        return f'{self.last_name} {self.mothers_name} {self.first_name} {self.middle_name}'
