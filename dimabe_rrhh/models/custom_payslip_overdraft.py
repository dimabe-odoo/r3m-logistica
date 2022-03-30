from odoo import fields, api, models

class CustomPaylsipOverdraft(models.Model):
    _name = 'custom.payslip_overdraft'
    _description = 'Sobregiro de Nomina'

    employee_id = fields.Many2one('hr.employee', 'Empleado', required=True)

    amount_residual = fields.Float('Saldo')

    @api.model
    def create(self, values):
        if 'employee_id' in values.keys():
            overdraft_id = self.env['custom.payslip_overdraft'].search([('employee_id','=',values['employee_id'])])
            if overdraft_id:
                raise models.ValidationError(f'No se puede generar un Sobregiro para el Empleado {overdraft_id.employee_id.name}\nYa se encuentra registrado.')

        return super(CustomPaylsipOverdraft, self).create(values)