from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import *
import pandas as pd
from odoo.addons import decimal_precision as dp
from ..utils.roundformat_clp import round_clp


class CustomSettlement(models.Model):
    _name = 'custom.settlement'
    _rec_name = 'employee_id'
    _description = "Finiquito"

    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True
    )

    contract_id = fields.Many2one(
        'hr.contract',
        string='Contrato',
        required=True
    )

    fired_id = fields.Many2one(
        'custom.fired',
        string='Causal de Despido',
        required=True
    )

    article_causal = fields.Selection('Articulo', related='fired_id.article')

    date_start = fields.Date('Fecha inicio contrato', related='contract_id.date_start')

    date_notification = fields.Date('Fecha notificación de despido', default=date.today())

    date_settlement = fields.Date('Fecha finiquito', required=True)

    period_service = fields.Char('Periodo de servicio', compute='compute_period', readonly=True)

    vacation_days = fields.Float('Dias de Obtenidos', compute='compute_vacation_days', readonly=True)

    vacation_days_taken = fields.Float('Dias Tomados', compute='compute_vacation_days', readonly=True)

    days_pending = fields.Float('Dias Pendientes', compute='compute_vacation_days')

    type_contract = fields.Many2one('custom.data', 'Tipo de Contrato', related="contract_id.type_id")

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
    )

    wage = fields.Monetary('Sueldo Base', related='contract_id.wage', currency_field='currency_id',
                           digits='Paypoll')

    reward_selection = fields.Selection([
        ('Yes', 'Si'),
        ('No', 'No'),
        ('Edit', 'Editar')
    ], string='Gratificacion', default='Yes')

    collation_amount = fields.Float('Colación', digits='Payroll')

    mobilization_amount = fields.Float('Movilización', digits='Payroll')

    pending_remuneration_payment = fields.Monetary('Remuneraciones Pendientes', digits='Payroll')

    compensation_warning = fields.Monetary('Indemnización Aviso Previo', compute='compute_warning',
                                           digits='Payroll')

    compensation_years = fields.Monetary('Indemnización Años de Servicio', compute='compute_years',
                                         digits='Payroll')

    compensation_vacations = fields.Monetary('Indemnización Vacaciones Proporcionales', compute='compute_vacations',
                                             digits='Payroll')

    settlement = fields.Monetary('Finiquito', digits='Payroll')

    years = fields.Integer('Años', compute='compute_years')

    current_user = fields.Many2one('res.users', 'Current User', default=lambda self: self.env.user)

    reward_value = fields.Monetary('Gratificación', compute="compute_reward")

    non_working_days = fields.Float('Días Inhábiles ', compute="compute_no_working_days")

    compensation_vacations_days = fields.Float('Total Vacaciones Proporcionales', compute="compute_vacations")

    state = fields.Selection([('draft', 'Borrador'), ('done', 'Realizado')],
                             default='draft', tracking=True)

    line_ids = fields.One2many('custom.settlement.line', 'settlement_id')


    @api.onchange('date_settlement')
    def compute_period(self):
        for item in self:
            period = relativedelta(item.date_settlement, item.date_start)
            item.period_service = '{} años , {} meses , {} dias'.format(period.years, period.months, (period.days + 1))

    @api.onchange('date_settlement')
    def compute_vacation_days(self):
        for item in self:
            item.vacation_days = 0
            item.days_pending = 0
            vacation_id = self.env['custom.vacation'].search(
                [('employee_id', '=', item.employee_id.id), ('contract_id', '=', item.contract_id.id)])
            if vacation_id:
                period = relativedelta(item.date_settlement, item.date_start)
                item.vacation_days = round(15 * period.years + (
                            period.months * item.env.user.company_id.vacation_day_for_month + (
                                period.days + 1) / 30 * item.env.user.company_id.vacation_day_for_month), 2)
                item.vacation_days_taken = int(sum(line.number_of_days for line in
                                                   vacation_id.leave_allocation_line_ids.filtered(
                                                       lambda x: x.consumed_state in ['consumed', 'partial'])))
                item.days_pending = item.vacation_days - item.vacation_days_taken

    @api.onchange('reward_selection')
    def compute_reward(self):
        for item in self:
            if item.reward_selection == 'Yes' or item.reward_selection == 'Edit':
                if item.date_settlement:
                    indicator_id = self.env['custom.indicators'].search([('year', '=', item.date_settlement.year), (
                    'month', '=', self.get_month(int(item.date_settlement.month)))])
                    if indicator_id:
                        minimum = indicator_id.mapped('data_ids').filtered(
                            lambda a: a.name == 'Trab. Dependientes e Independientes').value

                        if item.contract_id.type_id.code == 4:
                            item.reward_value = 0
                        elif item.wage > round(minimum * 4.75 / 12):
                            item.reward_value = round(minimum * 4.75 / 12)
                        else:
                            item.reward_value = round(item.wage * 0.25)

                    else:
                        raise models.ValidationError('Indicador no encontrado')
                else:
                    item.reward_value = 0
            else:
                item.reward_value = 0

    def compute_vacations(self):
        for item in self:
            daily = item.wage / 30
            item.compensation_vacations_days = item.days_pending + item.non_working_days
            item.compensation_vacations = round(item.compensation_vacations_days * daily)
            item.calculate_settlement()

    @api.onchange('date_notification')
    def compute_warning(self):
        for item in self:
            item.compensation_warning = 0
            if item.date_settlement:
                warning = abs(self.date_notification - self.date_settlement).days + 1
                if warning < 30 and item.fired_id.article == '161':
                    item.compensation_warning = round(
                        (item.wage + item.reward_value) + (item.collation_amount + item.mobilization_amount))
            item.calculate_settlement()

    @api.onchange('date_settlement')
    def compute_years(self):
        for item in self:
            item.compensation_years = 0
            period = relativedelta(item.date_settlement, item.date_start)
            years = period.years
            if period.months >= 6:
                years += 1
            if item.fired_id.article == '161':
                item.compensation_years = round(
                    (item.wage + item.reward_value) + (item.collation_amount + item.mobilization_amount)) * years
            item.years = years
            item.calculate_settlement()

    @api.onchange('date_settlement')
    @api.depends('vacation_days_taken')
    def compute_no_working_days(self):
        for item in self:
            item.non_working_days = item.get_weekend()

    @api.depends('date_settlement', 'pending_remuneration_payment', 'reward_selection', 'fired_id')
    def calculate_settlement(self):
        for item in self:
            discount_other_entries = sum(line.amount for line in item.mapped('line_ids').filtered(lambda x: x.rule_id.category_id.code in ['DES', 'ODES']))
            sum_other_entries = sum(line.amount for line in item.mapped('line_ids').filtered(lambda x: x.rule_id.category_id.code in ['NOTIMP', 'IMP'])) #evaluar si va el IMP
            item.settlement = item.pending_remuneration_payment + item.compensation_vacations + item.compensation_warning + item.compensation_years + sum_other_entries - discount_other_entries

    @api.onchange('date_settlement')
    def onchange_method(self):
        for item in self:
            payslip = self.env['hr.payslip'].search(
                [('date_from', '>', item.date_start), ('date_from', '<', item.date_settlement),
                 ('contract_id', '=', item.contract_id.id)])
            vacation = payslip.mapped('worked_days_line_ids').filtered(lambda a: 'Vacaciones' in a.name).mapped(
                'number_of_days')
            item.vacation_days_taken = sum(vacation)

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        for item in self:
            item.collation_amount = item.contract_id.collation_amount
            item.mobilization_amount = item.contract_id.mobilization_amount

    def button_done(self):
        for item in self:
            item.calculate_settlement()
            if not item.contract_id.date_end or item.contract_id.date_end != item.date_settlement:
                item.contract_id.write({
                    'date_end': item.date_settlement
                })

            for line in item.line_ids:
                if line.loan_id:
                    fee_ids = line.loan_id.mapped('fee_ids').filtered(lambda x: not x.paid)
                    sum_fee = sum(fee.value for fee in fee_ids)
                    if line.amount == sum_fee:
                        for fee in fee_ids:
                            fee.write({
                                'paid': True
                            })
                        line.loan_id.write({
                            'state': 'done'
                        })
                    else:
                        raise models.ValidationError(f'El monto en el finiquito {line.amount} es distinto a lo adeudad en el prestamo {sum_fee}')

            item.write({
                'state': 'done'
            })
            # evaluate if only date the contract cancel automatic

    def get_weekend(self):
        if self.date_settlement:
            days = round(self.days_pending)
            date_after = self.date_settlement + timedelta(days=days)
            date_settlement = self.date_settlement + timedelta(days=1)
            saturdays = pd.date_range(start=date_settlement, end=date_after, freq='W-SAT').strftime('%m/%d/%Y').tolist()
            models._logger.error(saturdays)
            sundays = pd.date_range(start=date_settlement, end=date_after, freq='W-SUN').strftime('%m/%d/%Y').tolist()
            models._logger.error(sundays)
            holiday = self.env['custom.holidays'].search([('date', '>', date_settlement), ('date', '<', date_after)])
            weeekend = sorted(sorted(saturdays) + sorted(sundays))
            return len(weeekend) + len(holiday)

    def get_month(self, month):
        if month == 1:
            return 'ene'
        if month == 2:
            return 'feb'
        if month == 3:
            return 'mar'
        if month == 4:
            return 'apr'
        if month == 5:
            return 'may'
        if month == 6:
            return 'jun'
        if month == 7:
            return 'jul'
        if month == 8:
            return 'aug'
        if month == 9:
            return 'sep'
        if month == 10:
            return 'oct'
        if month == 11:
            return 'nov'
        return 'dec'

    def roundclp(self, value):
        return round_clp(value)

    def intro_text(self):
        if not self.env.user.company_id.legal_representative_id:
            raise models.ValidationError('Debe configurar el representante legal de la empresa')
        if not self.env.user.company_id.legal_representative_id:
            raise models.ValidationError('El representante legal no cuenta con un RUT registrado')
        text = f'En {self.env.user.company_id.city}, a {self.date_settlement.day} de' \
                f' {self.get_month_text(self.date_settlement.month)} de {self.date_settlement.year}, entre {self.employee_id.display_name}, R.U.T.' \
                f' {self.vat_cl_formated(self.employee_id.identification_id)}, en adelante, también, {self.env.user.company_id.name},' \
                f' representado por {self.get_referential_sex()} {self.env.user.company_id.legal_representative_id.display_name}, R.U.T.' \
                f' {self.vat_cl_formated(self.env.user.company_id.legal_representative_id.vat)} domiciliado en {self.env.user.company_id.partner_id.street},' \
                f' comuna de {self.env.user.company_id.partner_id.city}., ciudad de {self.env.user.company_id.partner_id.city}., ' \
                f'por una parte; y la otra, {self.get_referential_sex()} {self.employee_id.display_name}, R.U.T. {self.vat_cl_formated(self.employee_id.identification_id)}.,' \
                f' domiciliado en {self.employee_id.address_home_id.street},comuna de {self.employee_id.address_home_id.city}., ' \
                f'en adelante, también, {self.employee_id.display_name}, se deja testimonio y se ha acordado el finiquito que consta de las siguientes cláusulas:'

        return text
    def first_item(self):
        return f'PRIMERO: El trabajador prestó servicios al empleador desde el {self.date_start.day} de {self.get_month_text(self.date_start.month)} de' \
               f' {self.date_start.year} hasta el {self.date_settlement.day} de {self.get_month_text(self.date_settlement.month)} de {self.date_settlement.year}, ' \
               f'fecha esta última en que su contrato de trabajo ha terminado por {self.fired_id.name}, causal(es) señalada(s) en el Código del Trabajo, Artículo ' \
               f'[{self.fired_id.article}-{self.fired_id.sequence}].'

    def second_item_1(self):
        return f'SEGUNDO: {self.get_referential_sex()} {self.employee_id.display_name} declara recibir en este acto, a su entera satisfacción, de parte de' \
               f' {self.env.user.company_id.legal_representative_id.display_name} la suma de $ {self.roundclp(self.settlement)}, según la liquidación que se señala a continuación:'

    def second_item_2(self):
        return f'{self.get_referential_sex()} {self.employee_id.display_name} declara haber analizado y estudiado detenidamente dicha liquidación, aceptándola en todas sus partes, sin tener observación alguna que formularle.'

    def third_item(self):
        return f'TERCERO: En consecuencia, el empleador paga a {self.get_referential_sex()} {self.employee_id.display_name} en dinero efectivo ' \
               f'contra el Banco {self.employee_id.bank_account_id.bank_id.name} N° Cuenta {self.employee_id.bank_account_id.acc_number}, la suma de $ {self.roundclp(self.settlement)} ({self.env.user.company_id.currency_id.amount_to_text(self.settlement)}), ' \
               f'que el trabajador declara recibir en este acto a su entera satisfacción. Las partes dejan constancia que la referida suma cubre el total de ' \
               f'haberes especificados en la liquidación señalada en el numerando SEGUNDO del presente finiquito.'

    def fourth_item(self):
        return f'CUARTO: {self.get_referential_sex()} {self.employee_id.display_name} deja constancia que durante el tiempo que prestó servicios a {self.env.user.company_id.name}, recibió oportunamente el total de las remuneraciones,' \
               f' beneficios y demás prestaciones convenidas de acuerdo a su contrato de trabajo, clase de trabajo ejecutado y disposiciones legales pertinentes, ' \
               f'y que en tal virtud el empleador nada le adeuda por tales conceptos, ni por horas extraordinarias, asignación familiar, feriado, indemnización por ' \
               f'años de servicios, imposiciones previsionales, así como por ningún otro concepto, ya sea legal o contractual, derivado de la prestación de sus ' \
               f'servicios, de su contrato de trabajo o de la terminación del mismo. En consecuencia, {self.get_referential_sex()} {self.employee_id.display_name} ' \
               f'declara que no tiene reclamo alguno que formular en contra de {self.env.user.company_id.name}, renunciando a todas las acciones que pudieran emanar ' \
               f'del contrato que los vinculó.'

    def fifth_item(self):
        return f'QUINTO: En virtud de lo anteriormente expuesto, {self.get_referential_sex()} {self.employee_id.display_name} manifiesta expresamente que {self.env.user.company_id.name} nada le adeuda en relación con los servicios prestados,' \
               f' con el contrato de trabajo o con motivo de la terminación del mismo, por lo que libre y espontáneamente, y con el pleno y cabal conocimiento de sus' \
               f' derechos, otorga a su empleador, el más amplio, completo, total y definitivo finiquito por los servicios prestados o la terminación de ellos, ya ' \
               f'diga relación con remuneraciones, cotizaciones previsionales, de seguridad social o de salud, subsidios, beneficios contractuales adicionales a las ' \
               f'remuneraciones, indemnizaciones, compensaciones, o con cualquiera causa o concepto.'

    def final_item(self):
        return f'Para constancia, las partes firman el presente finiquito en tres ejemplares, quedando uno en poder de cada una de ellas, ' \
               f'y en cumplimiento de la legislación vigente, {self.get_referential_sex()} {self.employee_id.display_name} lo lee, firma y lo ratifica.'

    def get_referential_sex(self):
        if self.employee_id.gender == 'male':
            return 'Don'
        if self.employee_id.gender == 'female':
            return 'Doña'
        else:
            return 'Don(a)'

    def get_month_text(self, month):
        if month == 1:
            return 'enero'
        if month == 2:
            return 'febrero'
        if month == 3:
            return 'marzo'
        if month == 4:
            return 'abril'
        if month == 5:
            return 'mayo'
        if month == 6:
            return 'junio'
        if month == 7:
            return 'julio'
        if month == 8:
            return 'agosto'
        if month == 9:
            return 'septiembre'
        if month == 10:
            return 'octubre'
        if month == 11:
            return 'noviembre'
        return 'diciembre'

    def vat_cl_formated(self, vat):
        t = vat.split('-')
        t = '{:,}'.format(int(t[0].replace('.', '').replace(',',''))).replace(',', '.') + '-' + t[1]
        return t

    def update_other_entries(self):
        loan_ids = self.env['custom.loan'].search([('employee_id', '=', self.employee_id.id), ('state','=','in_process')]).filtered(lambda x: x.rule_id.available_to_settlement)

        if loan_ids:
            for loan in loan_ids:
                fee_ids = loan.mapped('fee_ids').filtered(lambda x: not x.paid)
                amount = sum(fee.value for fee in fee_ids)
                if amount > 0:
                    line_loan_id = self.env['custom.settlement.line'].search([('settlement_id', '=', self.id), ('loan_id', '=', loan.id)])
                    if not line_loan_id:
                        self.env['custom.settlement.line'].create({
                            'settlement_id': self.id,
                            'rule_id': loan.rule_id.id,
                            'amount': amount,
                            'loan_id': loan.id,
                            'description': f'{loan.rule_id.name} - {len(fee_ids)} cuotas de {loan.fee_value}'
                        })


class CustomSettlementLine(models.Model):
    _name = 'custom.settlement.line'
    _description = 'Finiquito'

    settlement_id = fields.Many2one('custom.settlement')

    rule_id = fields.Many2one('hr.salary.rule', 'Regla')

    category_id = fields.Char('Categoría', related="rule_id.category_id.name")

    amount = fields.Monetary('Monto', digits='Payroll')

    loan_id = fields.Many2one('custom.loan')

    description = fields.Char('Descripción')

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
    )