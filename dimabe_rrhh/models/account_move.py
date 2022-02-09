from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, values):
        if 'journal_id' in values.keys():
            payroll_structure_ids = self.env['hr.payroll.structure'].sudo().search([])
            if values['journal_id'] == payroll_structure_ids[0].journal_id.id:
                if 'line_ids' in values.keys():
                    self.validate_all_account_analytic(values['line_ids'])
                    for line in values['line_ids']:
                        if line[2]['employee_id']:
                            line[2]['analytic_account_id'] = self.get_analytic_account_id(line[2]['employee_id'])
        return super(AccountMove, self).create(values)

    def get_line_by_acount(self, values, account, account_quantity, lines_unique, lines_dupplied):
        for line in values['line_ids']:
            if account_quantity > 0 and line[2]['credit'] > 0 and account == line[2]['account_id']:
                exist = False
                for s in lines_dupplied:
                    if s[2]['account_id'] == account:
                        exist = True
                if not exist:
                    return line
                else:
                    return None
            elif account == line[2]['account_id'] and line[2]['credit'] == 0 and  line not in lines_unique:
                return line

    def get_name_account(self, account):
        return self.env['account.account'].search([('id','=',account)]).name


    def partner_employee(self, partner_id):
        user_id = self.env['res.users'].search([('partner_id', '=', partner_id)])
        employee_id = None
        if user_id:
            employee_id = self.env['hr.employee'].search([('user_id', '=', user_id.id)])

        if not employee_id:
            employee_id = self.env['hr.employee'].search([('address_home_id', '=', partner_id)])

        return employee_id

    @api.onchange('amount_residual')
    def onchange_amount_residual(self):
        for item in self:
            sale_employee_id = self.env['custom.sale_employee'].search([('invoice_id', '=', self.id)])
            if sale_employee_id:
                if item.amount_residual == 0:
                    sale_employee_id.write({
                        'state': 'paid_out'
                    })
                if item.amount_residual > 0:
                    sale_employee_id.write({
                        'state': 'to_pay'
                    })

    def get_analytic_account_id(self, id):
        analytic_account_id = None
        employee_id = self.env['hr.employee'].search([('id','=', id)])
        contract_id = self.env['hr.contract'].search([('employee_id', '=', id), ('state', '=', 'open')])
        if self.env.user.company_id.analitic_account == '1':
            analytic_account_id = employee_id.account_analytic_id.id
        elif self.env.user.company_id.analitic_account == '2':
            analytic_account_id = contract_id.analytic_account_id.id
        elif self.env.user.company_id.analitic_account == '3':
            analytic_account_id = employee_id.department_id.analytic_account_id.id

        return analytic_account_id

    def validate_all_account_analytic(self, line_ids):
        validate = False
        employees = []
        for line in line_ids:
            if line[2]['employee_id']:
                employees.append(line[2]['employee_id'])
        employee_ids = self.env['hr.employee'].search([('id', 'in', employees)])
        employees_not_account_analytic = []
        for employee_id in employee_ids:
            if self.env.user.company_id.analitic_account == '1':
                if not employee_id.account_analytic_id:
                    employees_not_account_analytic.append(employee_id)
            elif self.env.user.company_id.analitic_account == '2':
                contract_id = self.env['hr.contract'].search(
                    [('employee_id', '=', employee_id.id), ('state', '=', 'open')])
                if not contract_id.analytic_account_id:
                    employees_not_account_analytic.append(employee_id)
            elif self.env.user.company_id.analitic_account == '3':
                if not employee_id.department_id.analytic_account_id:
                    employees_not_account_analytic.append(employee_id)

        if len(employees_not_account_analytic) > 0:
            employees_text = ''
            for line in employees_not_account_analytic:
                employees_text += f'\n{line.display_name}'

            raise models.ValidationError(f'Favor configurar el Centro de Costo (Cuenta Analítica) de Los siguientes empleados\n{employees_text}')



    class AccountMoveLine(models.Model):
    
        _inherit = 'account.move.line'

        employee_id = fields.Many2one('hr.employee', 'Empleado')

        employee_vat = fields.Char('RUT', related='employee_id.identification_id')
