from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from py_linq import Enumerable
from odoo.tools import float_compare, float_is_zero
import datetime
from dateutil.relativedelta import relativedelta

class HrPaySlip(models.Model):
    _inherit = 'hr.payslip'

    _order = 'last_name'

    indicator_id = fields.Many2one('custom.indicators', string='Indicadores', required=True)

    salary_id = fields.Many2one('hr.salary.rule', 'Agregar Entrada')

    account_analytic_id = fields.Many2one('account.analytic.account', 'Centro de Costo', readonly=True)

    basic_salary = fields.Char('Sueldo Base', compute="_compute_basic_salary")

    net_salary = fields.Char('Alcance Liquido', compute="_compute_net_salary")

    worked_days_line_ids = fields.One2many(readonly=False)

    payment_term_id = fields.Many2one('custom.payslip.payment.term', 'Forma de Pago')

    loan_ids = fields.Many2many('custom.loan')

    personal_movement_ids = fields.One2many('custom.personal.movements', 'payslip_id')

    fee_id = fields.Many2one('custom.fee', string='Cuota Pagada')

    fee_ids = fields.Many2many('custom.fee')

    last_name = fields.Char('Apellido para orden', related='employee_id.last_name', store=True)

    was_payslip_undded = fields.Boolean('La Nómina volvió al estado anterior?', default=False)

    last_full_payslip = fields.Float('Última Renta Imponible 30 días')

    @api.model
    def _compute_basic_salary(self):
        for item in self:
            item.basic_salary = f"$ {int(item.line_ids.filtered(lambda a: a.code == 'SUELDO').total)}"

    @api.model
    def _compute_net_salary(self):
        for item in self:
            item.net_salary = f"$ {int(item.line_ids.filtered(lambda a: a.code == 'LIQ').total)}"

    def _get_custom_report_name(self):
        return f'Liquidación {self.employee_id.name} {self.indicator_id.name} '

    def add(self):
        for item in self:
            if item.salary_id:
                type_id = self.env['hr.payslip.input.type'].search([('code', '=', item.salary_id.code)])
                amount = 0

                if type_id:
                    if item.salary_id.amount_select == 'fix':
                        amount = item.salary_id.amount_fix
                    elif item.salary_id.code == 'COL':
                        if item.contract_id.collation_amount > 0:
                            amount = item.contract_id.collation_amount
                        else:
                            raise models.ValidationError(
                                'No se puede agregar Asig. Colación ya que está en 0 en el contrato')

                    self.env['hr.payslip.input'].create({
                        'name': item.salary_id.name,
                        'code': item.salary_id.code,
                        'contract_id': item.contract_id.id,
                        'payslip_id': item.id,
                        'input_type_id': type_id.id,
                        'amount': amount
                    })
                else:
                    input_type = self.env['hr.payslip.input.type'].create({
                        'name': item.salary_id.name,
                        'code': item.salary_id.code
                    })
                    self.env['hr.payslip.input'].create({
                        'name': item.salary_id.name.capitalize(),
                        'code': item.salary_id.code,
                        'contract_id': item.contract_id.id,
                        'payslip_id': item.id,
                        'input_type_id': input_type.id
                    })
            item.salary_id = None

    def update_other_entries(self):
        for item in self:
            item.get_permanent_discounts()
            item.get_other_savings()
            item.get_sale_documents()
            item.get_discount_overdrafts()
            loan_ids = self.env['custom.loan'].search(
                [('employee_id', '=', item.employee_id.id), ('state', '=', 'in_process')])
            #loan_ids = loan_ids.filtered(lambda a: item.date_from <= a.next_fee_date <= item.date_to)
            loans = []
            if self.can_collect_loan_discount():
                for loan in loan_ids:
                    # if not self.input_line_ids.filtered(lambda a: a.code == loan.rule_id.code and a.amount > 0):
                    if loan not in item.loan_ids:
                        type_id = self.env['hr.payslip.input.type'].search([('code', '=', loan.rule_id.code)])
                        #actual_fee = len(loan.fee_ids.filtered(lambda a: a.paid)) + 1
                        actual_fee = len(loan.fee_ids.filtered(lambda a: a.expiration_date < item.date_from)) + 1
                        if type_id:
                            amount = loan.next_fee_id.value
                            loan_fee_ids = loan.fee_ids.filtered(lambda x: x.expiration_date >= item.date_from and x.expiration_date <= item.date_to)
                            if len(loan_fee_ids) > 1:
                                amount = 0
                                actual_fee_text = ''
                                actual_fee = actual_fee-1
                                for fee in loan_fee_ids:
                                    actual_fee += 1
                                    actual_fee_text += str(actual_fee)+ '-'
                                    amount += fee.value
                            else:
                                actual_fee_text = str(actual_fee)

                            additional_info = f'Cuota {actual_fee_text}/{loan.fee_qty}'

                            self.env['hr.payslip.input'].create({
                                'additional_info': additional_info,
                                'code': loan.rule_id.code,
                                'contract_id': item.contract_id.id,
                                'payslip_id': item.id,
                                'amount': amount,
                                'input_type_id': type_id.id
                            })
                        else:
                            input_type = self.env['hr.payslip.input.type'].create({
                                'name': loan.rule_id.name,
                                'code': loan.rule_id.code
                            })
                            self.env['hr.payslip.input'].create({
                                'additional_info': f'Cuota {actual_fee}/{loan.fee_qty}',
                                'code': loan.rule_id.code,
                                'contract_id': item.contract_id.id,
                                'payslip_id': item.id,
                                'amount': loan.next_fee_id.value,
                                'input_type_id': input_type.id
                            })
                        loans.append(loan.id)
                    item.write({
                        'loan_ids': [(4, l) for l in loans]
                    })

    def clean_loan(self):
        self.write({
            'loan_ids': None
        })

    def action_payslip_done(self):
        try:
            for item in self:
                item.update_other_entries()
                item.compute_sheet()
                item.update_loan_date()
                if int(item.line_ids.filtered(lambda a: a.code == 'LIQ').total) < 0:
                    raise models.ValidationError(f'No se puede confirmar\nLa Nómina de Empleado {item.employee_id.name} tiene Alcance Liquido negativo: {item.net_salary}.')
                if item.loan_ids:
                    for loan in item.loan_ids:
                        if loan not in item.fee_ids.mapped('loan_id'):
                            if loan.next_fee_ids:
                                for next_fee in loan.next_fee_ids:
                                    item.write({
                                        'fee_ids': [(4, next_fee.id)]
                                    })

                                    next_fee.write({
                                        'paid': True,
                                    })

                                    if loan.verify_is_complete():
                                        loan.write({
                                            'state': 'done'
                                        })
                if len(item.input_line_ids.mapped('sale_employee_id')) > 0:
                    partner_id = item.employee_id.user_id.partner_id if item.employee_id.user_id.partner_id else item.employee_id.address_home_id
                    item.validation_data(partner_id)

                    move_id = self.env['account.move'].create({
                        'currency_id': self.env.user.company_id.currency_id.id,
                        'journal_id': self.env.user.company_id.sale_employee_journal_id.id,
                        'move_type': 'entry',
                        'state': 'draft',
                        'invoice_payment_term_id': self.env.user.company_id.sale_employee_payment_term_id.id,
                        'ref': 'Pago Venta Interna',
                        'date': datetime.datetime.now()
                    })

                    move_lines = []
                    debit = 0
                    credit = 0
                    for line in item.input_line_ids:
                        if line.sale_employee_id:
                            if line.sale_employee_id.state == 'to_pay':
                                line.sale_employee_id.write({
                                    'payslip_id': item.id,
                                    'move_id': move_id.id
                                })

                            if line.sale_employee_id.invoice_id.move_type == 'out_invoice':
                                transaction = 'Descuento'
                            if line.sale_employee_id.invoice_id.move_type == 'out_refund':
                                transaction = 'Devolución'


                            move_lines.append({
                                'move_id': move_id.id,
                                'move_name': move_id.name,
                                'journal_id': move_id.journal_id.id,
                                'account_id': partner_id.property_account_receivable_id.id,
                                'name': f'{transaction} Venta {line.sale_employee_id.invoice_id.name}',
                                'quantity': 1,
                                'currency_id': move_id.currency_id.id,
                                'partner_id': partner_id.id,
                                'debit': line.amount if line.sale_employee_id.invoice_id.move_type == 'out_refund' else 0,
                                'credit': line.amount if line.sale_employee_id.invoice_id.move_type == 'out_invoice' else 0,
                                'to_voucher_invoice_id': line.sale_employee_id.invoice_id.id
                            })

                    sum_debit = sum(line['debit'] for line in move_lines)
                    sum_credit = sum(line['credit'] for line in move_lines)

                    if sum_debit < sum_credit:
                        debit = sum_credit - sum_debit

                    if sum_debit > sum_credit:
                        credit = sum_debit - sum_credit

                    move_lines.append({
                        'move_id': move_id.id,
                        'move_name': move_id.name,
                        'journal_id': move_id.journal_id.id,
                        'account_id': self.env.user.company_id.sale_employee_journal_id.default_account_id.id,
                        'name': 'Venta Interna',
                        'quantity': 1,
                        'currency_id': move_id.currency_id.id,
                        'partner_id': partner_id.id,
                        'debit': debit,
                        'credit': credit,
                    })

                    self.env['account.move.line'].create(move_lines)

                    move_id.action_post()

                    for line in item.input_line_ids.mapped('sale_employee_id'):
                        invoice_line_id = line.invoice_id.line_ids.filtered(
                            lambda x: x.account_id.id == partner_id.property_account_receivable_id.id)
                        move_line_id = line.move_id.line_ids.filtered(
                            lambda x: x.to_voucher_invoice_id.id == line.invoice_id.id)

                        move_line_reconcile_ids = self.env['account.move.line'].search(
                            [('id', 'in', [invoice_line_id.id, move_line_id.id])])
                        move_line_reconcile_ids.reconcile()

                    item.update_sale_employee_state(item.input_line_ids.mapped('sale_employee_id'))

                overdraft_id = self.env['custom.payslip_overdraft'].search([('employee_id', '=', item.employee_id.id)])
                payslip_overdraft_id = item.input_line_ids.filtered(lambda a: a.code == 'SGIRO')
                if payslip_overdraft_id:
                    if not overdraft_id:
                        item.create_payslip_overdraft()

                payslip_discount_overdraft_id = item.input_line_ids.filtered(lambda a: a.code == 'SGIROMA')
                if payslip_discount_overdraft_id:
                    if overdraft_id:
                        overdraft_id.write({
                            'amount_residual': overdraft_id.amount_residual - payslip_discount_overdraft_id.amount + payslip_overdraft_id.amount,
                        })
        except Exception as e:
            raise models.ValidationError(f'{item.employee_id.display_name}')
        return super(HrPaySlip, self).action_payslip_done()

    def get_other_savings(self):
        if self.contract_id and len(self.contract_id.other_saving_ids) > 0 and self.can_collect_loan_discount():
            for item in self.contract_id.other_saving_ids:
                exist_input = self.exist_input(item.salary_rule_id.code)
                if not exist_input:
                    type_id = self.env['hr.payslip.input.type'].search([('code', '=', item.salary_rule_id.code)])
                    if type_id:
                        rate = 1
                        currency = 'CLP'
                        if item.currency == 'uf':
                            rate = self.indicator_id.mapped('data_ids').filtered(lambda x: x.type == '1' and x.last_month).value
                            currency = f'{item.amount} UF'
                        self.env['hr.payslip.input'].create({
                            'additional_info': 'Ahorro ' + currency,
                            'code': item.salary_rule_id.code,
                            'contract_id': self.contract_id.id,
                            'payslip_id': self.id,
                            'input_type_id': type_id.id,
                            'amount': item.amount * rate
                        })
                    else:
                        input_type = self.env['hr.payslip.input.type'].create({
                            'name': item.salary_rule_id.name,
                            'code': item.salary_rule_id.code
                        })

                        self.env['hr.payslip.input'].create({
                            'additional_info': 'Ahorro',
                            'code': item.salary_rule_id.code,
                            'contract_id': self.contract_id.id,
                            'payslip_id': self.id,
                            'input_type_id': input_type.id,
                            'amount': item.amount
                        })
                else:
                    exist_input.write({
                        'amount': item.amount
                    })

    def get_permanent_discounts(self):
        if self.contract_id and len(self.contract_id.permanent_discounts_ids) > 0 and self.can_collect_loan_discount():
            for item in self.contract_id.permanent_discounts_ids:
                exist_input = self.exist_input(item.salary_rule_id.code)
                if not exist_input:
                    type_id = self.env['hr.payslip.input.type'].search([('code', '=', item.salary_rule_id.code)])
                    if type_id:
                        self.env['hr.payslip.input'].create({
                            'additional_info': 'Descuento Fijo',
                            'code': item.salary_rule_id.code,
                            'contract_id': self.contract_id.id,
                            'payslip_id': self.id,
                            'input_type_id': type_id.id,
                            'amount': item.amount
                        })
                    else:
                        input_type = self.env['hr.payslip.input.type'].create({
                            'name': item.salary_rule_id.name,
                            'code': item.salary_rule_id.code
                        })

                        self.env['hr.payslip.input'].create({
                            'additional_info': 'Descuento Fijo',
                            'code': item.salary_rule_id.code,
                            'contract_id': self.contract_id.id,
                            'payslip_id': self.id,
                            'input_type_id': input_type.id,
                            'amount': item.amount
                        })
                else:
                    exist_input.write({
                        'amount': item.amount
                    })

    def get_sale_documents(self):
        if self.employee_id:
            sale_employee_ids = self.env['custom.sale_employee'].search(
                [('employee_id', '=', self.employee_id.id), ('state', '=', 'to_pay')])
            payslip_input_ids = self.env['hr.payslip.input'].search([('payslip_id', '=', self.id)]).filtered(
                lambda x: x.sale_employee_id)
            if len(sale_employee_ids) > 0:
                discount_type_id = self.env['hr.payslip.input.type'].search([('code', '=', 'DESVENTINT')])
                if not discount_type_id:
                    discount_type_id = self.env['hr.payslip.input.type'].create({
                        'name': f'Descuento Venta Interna',
                        'code': 'DESVENTINT'
                    })
                refund_type_id = self.env['hr.payslip.input.type'].search([('code', '=', 'DEVVENTINT')])
                if not refund_type_id:
                    refund_type_id = self.env['hr.payslip.input.type'].create({
                        'name': f'Devolución Venta Interna',
                        'code': 'DEVVENTINT'
                    })
                for sale_employee in sale_employee_ids:
                    if sale_employee.invoice_id.amount_residual == 0:
                        exist_input_id = self.env['hr.payslip.input'].search(
                            [('sale_employee_id', '=', sale_employee.id)])
                        if exist_input_id:
                            exist_input_id.unlink()
                    if sale_employee.state == 'to_pay' and sale_employee.invoice_id.amount_residual > 0:
                        type_id = None
                        if sale_employee.invoice_id.move_type == 'out_invoice':
                            type_id = discount_type_id
                        if sale_employee.invoice_id.move_type == 'out_refund':
                            type_id = refund_type_id
                        if type_id:
                            input_id = self.env['hr.payslip.input'].search(
                                [('sale_employee_id', '=', sale_employee.id)])
                            if not input_id:
                                self.env['hr.payslip.input'].create({
                                    'additional_info': f'{sale_employee.invoice_id.name}',
                                    'code': type_id.code,
                                    'contract_id': self.contract_id.id,
                                    'payslip_id': self.id,
                                    'input_type_id': type_id.id,
                                    'amount': sale_employee.amount_residual,
                                    'sale_employee_id': sale_employee.id
                                })
                            if input_id:
                                if input_id.payslip_id.id == self.id:
                                    input_id.write({
                                        'amount': sale_employee.amount_residual
                                    })

            if len(payslip_input_ids) > 0:
                for item in payslip_input_ids:
                    if item.sale_employee_id.state == 'paid_out' and item.sale_employee_id.amount_residual == 0:
                        item.unlink()

    def get_discount_overdrafts(self):
        if self.employee_id:
            overdraft_id = self.env['custom.payslip_overdraft'].search([('employee_id','=',self.employee_id.id)])

            if overdraft_id:
                if overdraft_id.amount_residual > 0:
                    overdraft_discount_type_id = self.env['hr.payslip.input.type'].search([('code', '=', 'SGIROMA')])
                    if not overdraft_discount_type_id:
                        overdraft_discount_type_id = self.env['hr.payslip.input.type'].create({
                            'name': 'Sobregiro mes Anterior',
                            'code': 'SGIROMA'
                        })
                    input_line_id = self.env['hr.payslip.input'].search([('payslip_id','=',self.id),('input_type_id','=',overdraft_discount_type_id.id)])
                    if not input_line_id and not self.was_payslip_undded:
                        self.env['hr.payslip.input'].create({
                            'code': overdraft_discount_type_id.code,
                            'contract_id': self.contract_id.id,
                            'payslip_id': self.id,
                            'input_type_id': overdraft_discount_type_id.id,
                            'amount': overdraft_id.amount_residual
                        })

    def create_input_overdraft(self, amount):
        if self.employee_id:
            overdraft_id = self.input_line_ids.filtered(lambda x: x.code == 'SGIRO')
            overdraft_type_id = self.env['hr.payslip.input.type'].search([('code', '=', 'SGIRO')])
            if not overdraft_type_id:
                overdraft_type_id = self.env['hr.payslip.input.type'].create({
                    'name': 'Sobregiro',
                    'code': 'SGIRO'
                })

            if overdraft_type_id and not overdraft_id:
                self.env['hr.payslip.input'].create({
                    'code': overdraft_type_id.code,
                    'contract_id': self.contract_id.id,
                    'payslip_id': self.id,
                    'input_type_id': overdraft_type_id.id,
                    'amount': abs(amount)
                })

    def create_payslip_overdraft(self):
        overdraft_id = self.env['custom.payslip_overdraft'].search([('employee_id', '=', self.employee_id.id)])
        input_id = self.input_line_ids.filtered(lambda a: a.code == 'SGIRO')
        if input_id:
            if not overdraft_id:
                self.env['custom.payslip_overdraft'].create({
                    'employee_id': self.employee_id.id,
                    'amount_residual': input_id.amount
                })


    def compute_sheet(self):
        for item in self:
            item.get_discount_overdrafts()
            res = super(HrPaySlip, item).compute_sheet()

            if int(item.line_ids.filtered(lambda a: a.code == 'LIQ').total) < 0:
                item.create_input_overdraft(int(item.line_ids.filtered(lambda a: a.code == 'LIQ').total))
                res = super(HrPaySlip, item).compute_sheet()

            return res


    def exist_input(self, salary_rule_code):
        input_type_id = self.env['hr.payslip.input.type'].search([('code', '=', salary_rule_code)])

        if input_type_id:
            payslip_input = self.env['hr.payslip.input'].search(
                [('payslip_id', '=', self._origin.id), ('input_type_id', '=', input_type_id.id)])

            return payslip_input
        else:
            False

    def custom_report_fix(self, list_report_list):

        report_linq = Enumerable(list_report_list)
        report_ids = report_linq.select(lambda x: x['id'])
        report = self.env['ir.actions.report'].search([('id', 'in', report_ids.to_list())])

        for rep in report:
            report_to_update = report_linq.first_or_default(lambda x: x['id'] == rep.id)
            if report_to_update:
                new_name = report_to_update['new_name'] if 'new_name' in report_to_update.keys() else rep.name
                new_template_name = report_to_update[
                    'template_new'] if 'template_new' in report_to_update.keys() else rep.report_name
                paperformat_id = report_to_update[
                    'paperformat_id'] if 'paperformat_id' in report_to_update.keys() else rep.paperformat_id
                print_report_name = report_to_update[
                    'print_report_name'] if 'print_report_name' in report_to_update.keys() else rep.print_report_name

                if rep.report_name != new_template_name or rep.report_file != new_template_name or rep.name != new_name or rep.paperformat_id != paperformat_id or rep.print_report_name != print_report_name:
                    rep.write({
                        'report_name': new_template_name,
                        'report_file': new_template_name,
                        'name': new_name,
                        'paperformat_id': paperformat_id,
                        'print_report_name': print_report_name
                    })
                else:
                    continue
            else:
                continue

    @api.model
    def create(self, values):
        payslip_id = self.env['hr.payslip'].search(
            [('indicator_id', '=', values['indicator_id']), ('employee_id', '=', values['employee_id'])])
        if payslip_id:
            raise models.ValidationError(
                f'Ya existe una Nómina de {payslip_id.employee_id.name} para  {payslip_id.indicator_id.name}')
        else:
            return super(HrPaySlip, self).create(values)

    def update_sale_employee_state(self, sale_employee_ids):
        for item in sale_employee_ids:
            if item.invoice_id.amount_residual == 0:
                item.write({
                    'state': 'paid_out'
                })

    def validation_data(self, partner_id):
        if not self.env.user.company_id.currency_id or not self.env.user.company_id.sale_employee_journal_id or not self.env.user.company_id.sale_employee_payment_term_id:
            message = ''
            if not self.env.user.company_id.currency_id:
                message += 'Moneda'
            if not self.env.user.company_id.sale_employee_journal_id:
                message += ', Diario'
            if not self.env.user.company_id.sale_employee_payment_term_id:
                message += ', Método de Pago'
            raise models.ValidationError(
                f'Para Venta Interna, es importante tener configurado en la compañia, pestaña RRHH:\n{message}')
        if not partner_id:
            raise models.ValidationError(
                f'Para Venta Interna, es importante tener configurado el Contacto en el Empleado(a) {self.employee_id.name}')
        else:
            if not partner_id.property_account_receivable_id:
                raise models.ValidationError(
                    f'Para Venta Interna, es importante tener configurado la Cuenta a cobrar en el Contacto del Empleado(a) {self.employee_id.name}')

    def get_extra_hour_quantity(self, code):
        for line in self.input_line_ids:
            if line.input_type_id.code == code:
                quantity_text = f'{str(int(line.amount))} hr'
                if line.amount > 1:
                    quantity_text += 's'
                return quantity_text

    def _action_create_account_move(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')

        # Add payslip without run
        payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)

        # Adding pay slips from a batch and deleting pay slips with a batch that is not ready for validation.
        payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
        for run in payslip_runs:
            if run._are_payslips_ready():
                payslips_to_post |= run.slip_ids

        # A payslip need to have a done state and not an accounting move.
        payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.move_id)

        # Check that a journal exists on all the structures
        if any(not payslip.struct_id for payslip in payslips_to_post):
            raise ValidationError(_('One of the contract for these payslips has no structure type.'))
        if any(not structure.journal_id for structure in payslips_to_post.mapped('struct_id')):
            raise ValidationError(_('One of the payroll structures has no account journal defined on it.'))

        # Map all payslips by structure journal and pay slips month.
        # {'journal_id': {'month': [slip_ids]}}
        slip_mapped_data = {
            slip.struct_id.journal_id.id: {fields.Date().end_of(slip.date_to, 'month'): self.env['hr.payslip']} for slip
            in payslips_to_post}
        for slip in payslips_to_post:
            slip_mapped_data[slip.struct_id.journal_id.id][fields.Date().end_of(slip.date_to, 'month')] |= slip

        for journal_id in slip_mapped_data:  # For each journal_id.
            for slip_date in slip_mapped_data[journal_id]:  # For each month.
                line_ids = []
                debit_sum = 0.0
                credit_sum = 0.0
                date = slip_date
                move_dict = {
                    'narration': '',
                    'ref': date.strftime('%B %Y'),
                    'journal_id': journal_id,
                    'date': date,
                }
                for slip in slip_mapped_data[journal_id][slip_date]:
                    move_dict['narration'] += slip.number or '' + ' - ' + slip.employee_id.name or ''
                    move_dict['narration'] += '\n'
                    slip_lines = slip._prepare_slip_lines_custom(date, line_ids)
                    line_ids.extend(slip_lines)

                for line_id in line_ids:  # Get the debit and credit sum.
                    debit_sum += line_id['debit']
                    credit_sum += line_id['credit']

                # The code below is called if there is an error in the balance between credit and debit sum.
                if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                    slip._prepare_adjust_line(line_ids, 'credit', debit_sum, credit_sum, date)
                elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                    slip._prepare_adjust_line(line_ids, 'debit', debit_sum, credit_sum, date)

                # Add accounting lines in the move
                move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
                move = self._create_account_move(move_dict)
                for slip in slip_mapped_data[journal_id][slip_date]:
                    slip.write({'move_id': move.id, 'date': date})

        return True

    def _prepare_slip_lines_custom(self, date, line_ids):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Payroll')
        new_lines = []

        for line in self.line_ids.filtered(lambda line: line.category_id):
            tmp_line = []
            hr_rule_category = self.env['hr.salary.rule.category'].search([])
            debit_rule_ids = hr_rule_category.filtered(lambda x: x.id in (
            self.env.ref('dimabe_rrhh.custom_hr_salary_rule_category_taxable').id,
            self.env.ref('dimabe_rrhh.custom_hr_salary_rule_category_not_taxable').id))

            credit_rule_ids = hr_rule_category.filtered(lambda x: x.id in (
            self.env.ref('dimabe_rrhh.custom_hr_salary_rule_category_discount').id,
            self.env.ref('dimabe_rrhh.custom_hr_salary_rule_category_other_discount').id,
            self.env.ref('dimabe_rrhh.custom_hr_salary_rule_forecast').id,
            (self.env.ref('dimabe_rrhh.custom_hr_salary_rule_health').id)))

            debit = 0
            credit = 0
            account_id = None

            exception_codes = []
            exception_codes.append('LIQ')
            if self.contract_id.is_fonasa == False and self.contract_id.isapre_id != False:
                exception_codes.append('ISAP')
            if self.contract_id.is_fonasa:
                exception_codes.append('FONASA')
                exception_codes.append('CAJACOMP')

            exception_rules = []
            exception_rules.append('SALUD')

            #validations
            if line.salary_rule_id.category_id.id in debit_rule_ids.ids and line.salary_rule_id.code not in exception_rules:
                if not line.salary_rule_id.account_debit or not line.salary_rule_id.account_credit:
                    raise models.ValidationError(f'No se puede confirmar la Nómina del Empleado {line.slip_id.employee_id.name}\nRegla Salarial {line.salary_rule_id.name} debe tener cuenta Deudora y Cuenta Acreedora')
            if (line.salary_rule_id.category_id.id in credit_rule_ids.ids or line.code in exception_codes) and line.salary_rule_id.code not in exception_rules:
                if not line.salary_rule_id.account_debit or not line.salary_rule_id.account_credit:
                    raise models.ValidationError(f'No se puede confirmar la Nómina del Empleado {line.slip_id.employee_id.name}\nRegla Salarial {line.salary_rule_id.name} debe tener cuenta Deudora y Cuenta Acreedora')

            debit_credit = False
            if line.salary_rule_id.account_debit and line.salary_rule_id.account_credit:
                if line.salary_rule_id.category_id.id in debit_rule_ids.ids:
                    debit = line.total
                    account_id = line.salary_rule_id.account_debit.id
                elif line.salary_rule_id.category_id.id in credit_rule_ids.ids or line.code in exception_codes:
                    credit = line.total
                    account_id = line.salary_rule_id.account_credit.id
                else:
                    debit_credit = True
            else:
                continue

            if not debit_credit:
                new_lines.append({
                    'name': line.salary_rule_id.name,
                    'debit': debit,
                    'credit': credit,
                    'account_id': account_id,
                    'employee_id':  line.slip_id.employee_id.id
                })

            else:
                new_lines.append({
                    'name': line.salary_rule_id.name,
                    'debit': line.total,
                    'credit': 0,
                    'account_id': line.salary_rule_id.account_debit.id,
                    'employee_id': line.slip_id.employee_id.id
                })

                new_lines.append({
                    'name': line.salary_rule_id.name,
                    'debit': 0,
                    'credit': line.total,
                    'account_id': line.salary_rule_id.account_credit.id,
                    'employee_id': line.slip_id.employee_id.id
                })

        return new_lines

    def get_sis_sc_license(self, rate, maximum):
        totim = self.mapped('line_ids').filtered(lambda x: x.code == 'TOTIM').total

        license_days = 0

        if len(self.personal_movement_ids) > 0:
            for license in self.personal_movement_ids:
                license_days += license.days

            if license_days > 30:
                license_days = 30
            if self.last_full_payslip:
                totim = self.last_full_payslip
            else:
                payslip_ids = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id)]).sorted(
                    lambda x: x.date_from, reverse=True)

                without_full_payslip = False
                if totim == 0:
                    for payslip in payslip_ids:
                        payslip_full_worked = payslip.mapped('worked_days_line_ids').filtered(lambda x: x.number_of_days == 30)
                        if not payslip_full_worked or len(payslip_full_worked) == 0:
                            if payslip.last_full_payslip > 0:
                                totim = payslip.last_full_payslip
                                without_full_payslip = False
                                break
                            else:
                                without_full_payslip = True

                        if payslip_full_worked or len(payslip_full_worked) > 0:
                            totim = payslip.mapped('line_ids').filtered(lambda x: x.code == 'TOTIM').total
                            without_full_payslip = False
                            break

                if without_full_payslip:
                    raise models.ValidationError(f'No existen registros de Nóminas para {self.employee_id.name} con 30 días trabajados\nFavor Ingresar el último total imponible en la pestaña Movimientos de Personal')

        if totim > maximum:
            totim = maximum
        return ((totim / 30) * license_days * rate) / 100


    def can_collect_loan_discount(self):
        licenses_days = 0
        licenses = self.personal_movement_ids.filtered(lambda x: x.personal_movements == '3')
        for license in licenses:
            licenses_days += (license.date_end - license.date_start).days + 1
        if licenses_days > 30:
            licenses_days = 30

        if self.env.user.company_id.min_licence_days:
            if licenses_days >= self.env.user.company_id.min_licence_days and licenses_days <= 30:
                return False
            else:
                return True
        else:
            raise models.ValidationError('Favor configurar el valor para Mínimo de días de Licencia para validar si se debe cobrar o no los prestamos y descuentos fijos.')


    def update_loan_date(self):
        for item in self:
            loan_ids = self.env['custom.loan'].search(
                [('employee_id', '=', item.employee_id.id), ('state', '=', 'in_process')])
            loan_ids = loan_ids.filtered(lambda a: item.date_from <= a.next_fee_date <= item.date_to)

            if loan_ids:
                if len(loan_ids)>0 and len(item.loan_ids) == 0:
                    for loan in loan_ids.mapped('fee_ids').filtered(lambda x: not x.paid):
                        loan.write({
                            'expiration_date': loan.expiration_date + relativedelta(months=1)
                        })


class HrPaySlipLine(models.Model):
    _inherit = 'hr.payslip.line'

    def _get_additional_info(self):
        payslip_input = self.env['hr.payslip.input'].search(
            [('code', '=', self.code), ('payslip_id', '=', self.slip_id.id)])
        return f' - {payslip_input.additional_info}' if payslip_input.additional_info else ''


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    indicator_id = fields.Many2one('custom.indicators', 'Indicador', required=True)

    #Ovewrite
    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': from_date.strftime('%B %Y'),
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        employees = self.with_context(active_test=False).employee_ids
        if not employees:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']

        contracts = employees._get_contracts(
            payslip_run.date_start, payslip_run.date_end, states=['open', 'close']
        ).filtered(lambda c: c.active)
        contracts._generate_work_entries(payslip_run.date_start, payslip_run.date_end)
        work_entries = self.env['hr.work.entry'].search([
            ('date_start', '<=', payslip_run.date_end),
            ('date_stop', '>=', payslip_run.date_start),
            ('employee_id', 'in', employees.ids),
        ])
        self._check_undefined_slots(work_entries, payslip_run)

        if (self.structure_id.type_id.default_struct_id == self.structure_id):
            work_entries = work_entries.filtered(lambda work_entry: work_entry.state != 'validated')
            if work_entries._check_if_error():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Some work entries could not be validated.'),
                        'sticky': False,
                    }
                }

        default_values = Payslip.default_get(Payslip.fields_get())
        payslip_values = [dict(default_values, **{
            'name': 'Payslip - %s' % (contract.employee_id.name),
            'employee_id': contract.employee_id.id,
            'credit_note': payslip_run.credit_note,
            'payslip_run_id': payslip_run.id,
            'date_from': payslip_run.date_start,
            'date_to': payslip_run.date_end,
            'contract_id': contract.id,
            'struct_id': self.structure_id.id or contract.structure_type_id.default_struct_id.id,
            'indicator_id': self.indicator_id.id
        }) for contract in contracts]

        payslips = Payslip.with_context(tracking_disable=True).create(payslip_values)
        for payslip in payslips:
            payslip._onchange_employee()

        payslips.compute_sheet()
        payslip_run.state = 'verify'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }