from odoo import api, fields, models
import xlsxwriter
from datetime import datetime
import base64
from collections import Counter
import io
import csv
from dateutil import relativedelta
import time


class WizardHrPayslip(models.TransientModel):
    _name = "wizard.hr.payslip"
    _description = 'XLSX Report'

    indicator_id = fields.Many2one('custom.indicators', string="Indicador")

    company_id = fields.Many2one('res.partner', domain=lambda self: [
        ('id', 'in', self.env['hr.employee'].sudo().search([('active', '=', True)]).mapped('address_id').mapped('id'))])

    date_from = fields.Date('Fecha Inicial', required=True, default=lambda self: time.strftime('%Y-%m-01'))
    date_to = fields.Date('Fecha Final', required=True, default=lambda self: str(
        datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    def generate_remuneration_book(self):
        file_name = 'temp'
        #file_name = 'C:/Users/Desarrollo/Downloads/temp.xls'
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet(self.company_id.name)
        number_format = workbook.add_format({'num_format': '#,###'})
        indicators = self.env['custom.indicators'].sudo().search([('id', '=', f'{self.indicator_id.id}')])
        if not indicators:
            raise models.ValidationError(f'No existen datos del mes de {self.indicator_id.name}')
        if indicators.state != 'done':
            raise models.ValidationError(
                f'Los indicadores previsionales del mes de {indicators.name} no se encuentran validados')
        row = 13
        col = 0

        # payslips = self.env['hr.payslip'].sudo().search(
        #    [('indicator_id', '=', indicators.id), ('state', 'in', ['done', 'draft']),('employee_id.address_id.id','=',self.company_id.id), ('name', 'not like', 'Devolución:')])

        payslips = self.env['hr.payslip'].sudo().search([('indicator_id', '=', self.indicator_id.id), ('name', 'not like', 'Devolución:')])

        totals = self.env['hr.payslip.line'].sudo().search([('slip_id', 'in', payslips.mapped('id'))]).filtered(
            lambda a: a.total > 0)

        totals_result = []
        payslips = totals.mapped('slip_id')
        bold_format = workbook.add_format({'bold': True})
        worksheet.write(0, 0, self.company_id.name, bold_format)

        payslips = self.env['hr.payslip'].search([('id', 'in', payslips.ids)]).sorted(lambda x: x.last_name)
        worksheet.write(2, 0, self.company_id.street, bold_format)
        worksheet.write(3, 0, self.company_id.city, bold_format)
        worksheet.write(4, 0, self.company_id.country_id.name, bold_format)
        worksheet.write(5, 0, self.company_id.vat, bold_format)
        worksheet.write(6, 0, 'Fecha Informe : ' + datetime.today().strftime('%d-%m-%Y'), bold_format)
        worksheet.write(7, 0, self.indicator_id.month, bold_format)
        worksheet.write(8, 0, 'Fichas : Todas', bold_format)
        worksheet.write(9, 0, 'Área de Negocio : Todas las Áreas de Negocios', bold_format)
        worksheet.write(10, 0, 'Centro de Costo : Todos los Centros de Costos', bold_format)
        worksheet.write(11, 0, 'Total Trabajadores : ' + str(len(payslips)), bold_format)
        for pay in payslips:
            rules = self.env['hr.salary.rule'].sudo().search(
                [('id', 'in', payslips.mapped('line_ids').filtered(lambda x: x.total > 0).mapped('salary_rule_id').mapped('id'))],
                order='order_number')

            worksheet.write(row, 0, pay.employee_id.display_name)
            worksheet.write(12, 0, 'Nombre', bold_format)
            long_name = max(payslips.mapped('employee_id').mapped('display_name'), key=len)
            worksheet.set_column(row, 0, len(long_name))

            worksheet.write(12, 1, 'Rut', bold_format)
            worksheet.write(row, 1, pay.employee_id.identification_id)
            long_rut = max(payslips.mapped('employee_id').mapped('identification_id'), key=len)
            worksheet.set_column(row, 1, len(long_rut))
            
            worksheet.write(12, 2, 'Dias Trabajados:', bold_format)
            worksheet.write(row, 2, self.get_worked_days(pay))
            long_const = self.get_max_analytic_account(payslips)
            worksheet.set_column(row, 2, len(long_const))
            worksheet.write(12, 4, 'Sueldo Base', bold_format)
            worksheet.write(row, 4, pay.employee_id.contract_id.wage)
            worksheet.write(12, 5, 'Cant. Horas Extras', bold_format)
            worksheet.write(row, 5, self.get_qty_extra_hours(payslip=pay))
            totals_result.append({5: self.get_qty_extra_hours(payslip=pay)})
            worksheet.write(12, 6, 'Valor Horas Extras', bold_format)
            col = 7
            for rule in rules:
                if rule.code == 'SUELDO':
                    worksheet.write(12, 3, 'Sueldo Ganado', bold_format)
                    total_amount = self.env["hr.payslip.line"].sudo().search(
                        [("slip_id", "=", pay.id), ("salary_rule_id", "=", rule.id)]).total
                    worksheet.write(row, 3, total_amount, number_format)
                    totals_result.append({col: total_amount})
                    continue
                if not rule.show_in_book:
                    continue
                if not totals.filtered(lambda a: a.salary_rule_id.id == rule.id):
                    continue
                if rule.code == 'HEX50':
                    total_amount = self.env["hr.payslip.line"].sudo().search(
                        [("slip_id", "=", pay.id), ("salary_rule_id", "=", rule.id)]).total
                    worksheet.write(row, 6, total_amount, number_format)
                    totals_result.append({6: total_amount})
                    continue
                elif rule.code == 'HEXDE':
                    worksheet.write(12, col, 'Cant. Horas Descuentos', bold_format)
                    worksheet.write(row, col, self.get_qty_discount_hours(payslip=pay))
                    totals_result.append({col: self.get_qty_discount_hours(payslip=pay)})
                    col += 1
                    worksheet.write(12, col, 'Monto Horas Descuentos', bold_format)
                    total_amount = self.env["hr.payslip.line"].sudo().search(
                        [("slip_id", "=", pay.id), ("salary_rule_id", "=", rule.id)]).total
                    worksheet.write(row, col, total_amount, number_format)
                    totals_result.append({col: total_amount})
                else:
                    total_amount = self.env["hr.payslip.line"].sudo().search(
                        [("slip_id", "=", pay.id), ("salary_rule_id", "=", rule.id)]).total
                    worksheet.write(12, col, rule.name, bold_format)
                    worksheet.write(row, col, total_amount, number_format)
                    totals_result.append({col: total_amount})
                col += 1
            ac = self.get_analytic_account_by_paysip(pay)
            if ac != None:
                ac_name = ac.name
            else:
                ac_name = ''     
            worksheet.write(12, col, 'Centro de Costo', bold_format)
            worksheet.write(row, col, ac_name)  
            worksheet.write(12, col + 1, 'Fecha Ingreso', bold_format)
            worksheet.write(row, col + 1, pay.employee_id.contract_id.date_start.strftime('%d-%m-%Y'))  
            worksheet.write(12, col + 2, 'Fecha Finiquito', bold_format)
            worksheet.write(row, col + 2, '')
            worksheet.write(12, col + 3, 'Tipo Contrato', bold_format)
            worksheet.write(row, col + 3, pay.employee_id.contract_id.type_id.name)  
            col = 0
            row += 1
        counter = Counter()
        for item in totals_result:
            counter.update(item)
        total_dict = dict(counter)
        worksheet.write(row, 0, 'Totales', bold_format)
        number_bold_format = workbook.add_format({'num_format': '#,###', 'bold': True})
        for k in total_dict:
            worksheet.write(row, k, total_dict[k], number_bold_format)
        col = 0
        row += 1
        workbook.close()
        with open(file_name, "rb") as file:
            file_base64 = base64.b64encode(file.read())

        file_name = 'Libro de Remuneraciones {}'.format(indicators.name)
        attachment_id = self.env['ir.attachment'].sudo().create({
            'name': file_name,
            'datas': file_base64
        })
        action = {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
            'target': 'current',
        }
        return action

    def action_generate_csv(self):
        employee_model = self.env['hr.employee']
        payslip_model = self.env['hr.payslip']
        payslip_line_model = self.env['hr.payslip.line']
        company_country = self.env.user.company_id.country_id
        sex_data = {'male': "M", 'female': "F", }
        output = io.StringIO()
        # _logger = logging.getLogger(__name__)

        writer = csv.writer(output, delimiter=';', quotechar="'", quoting=csv.QUOTE_NONE)

        payslip_recs = payslip_model.sudo().search(
            [('date_from', '=', self.date_from), ('state', '!=', 'cancel'), ('state', '!=', 'draft'),
             ('employee_id.address_id', '=', self.company_id.id), ('contract_id.type_id.name', '!=', 'Sueldo Empresarial')])

        date_start = self.date_from
        date_stop = self.date_to
        date_start_format = date_start.strftime("%m%Y")
        date_stop_format = date_stop.strftime("%m%Y")
        line_employee = []
        rut = ""
        rut_dv = ""
        rut_emp = ""
        rut_emp_dv = ""

        try:
            rut_emp, rut_emp_dv = self.env.user.company_id.vat.split("-")
            rut_emp = rut_emp.replace('.', '')
        except:
            pass
        if len(payslip_recs) > 0:
            for payslip in payslip_recs:
                payslip_line_recs = payslip_line_model.sudo().search([('slip_id', '=', payslip.id)])
                rut = ""
                rut_dv = ""
                subsidy_payer_rut = ""
                subsidy_payer_rut_dv = ""
                try:
                    rut, rut_dv = payslip.employee_id.identification_id.split("-")
                except Exception as e:
                    raise models.ValidationError(f'Rut {payslip.employee_id.identification_id} no tiene el formato correcto, favor corregir el empleado {payslip.employee_id.name}')

                try:
                    subsidy_payer = None
                    mnsj = ''
                    if payslip.contract_id.is_fonasa:
                        if payslip.indicator_id.ccaf_id:
                            subsidy_payer = payslip.indicator_id.ccaf_id
                        else:
                            mnsj = f'La Compañia {self.env.user.company_id.name} para el indicador {payslip.indicator_id.name} no tiene asignada La Caja de Compensación'
                    if not payslip.contract_id.is_fonasa:
                        if payslip.contract_id.isapre_id:
                            subsidy_payer = payslip.contract_id.isapre_id
                        else:
                            mnsj = f'El Empleado {payslip.employee_id.display_name} no tiene asignado la Isapre'
                    if subsidy_payer:
                        subsidy_payer_rut, subsidy_payer_rut_dv = subsidy_payer.vat.split("-")
                    else:
                        raise models.ValidationError(mnsj)
                except Exception as e:
                    if subsidy_payer:
                        raise models.ValidationError(
                            f'Rut {subsidy_payer.vat} de {subsidy_payer.name} no tiene el formato correcto, favor corregir')
                    else:
                        raise models.ValidationError(mnsj)

                rut = rut.replace('.', '')
                try:
                    if len(payslip.personal_movement_ids) == 0:
                        self.env['custom.personal.movements'].create({
                            'personal_movements': '0',
                            'payslip_id': payslip.id
                        })
                    for personal_movement in payslip.personal_movement_ids:
                        if not personal_movement.line_type:
                            personal_movement.write({
                                'line_type': self.get_line_type(payslip.personal_movement_ids, personal_movement)
                            })

                        line_employee = [
                            # 1 RUT SIN DIGITO NI PUNTOS NI GUION
                            self._shorten_str(rut, 11),
                            # 2 DIGITO VERIFICADOR
                            self._shorten_str(rut_dv, 1),
                            # 3 APELLIDO
                            self._format_str(payslip.employee_id.last_name.upper(), 30) if payslip.employee_id.last_name else '',
                            # 4 SEGUNDO APELLIDO
                            self._format_str(payslip.employee_id.mothers_name.upper(),
                                             30) if payslip.employee_id.mothers_name else '',
                            # 5 NOMBRES
                            "%s %s" % (self._format_str(payslip.employee_id.first_name.upper(), 15),
                                       self._format_str(payslip.employee_id.middle_name.upper(),
                                                        15) if payslip.employee_id.middle_name else ''),
                            # 6 SEXO
                            sex_data.get(payslip.employee_id.gender, '') if payslip.employee_id.gender else '',
                            # 7 NACION
                            self.get_nacionality(payslip.employee_id.country_id.id),
                            # 8 TIPO PAGO
                            self.get_pay_method(payslip.employee_id),
                            # 9 PERIODO DESDE
                            date_start_format,
                            # 10 PERIOD HASTA
                            date_stop_format,
                            # 11 REGIMEN
                            self.get_provisional_regime(payslip.contract_id),
                            # 12 TIPO TRABAJADOR
                            payslip.employee_id.employee_type_id.code,
                            # 13 DIAS TRABAJADOS
                            str(round(self.get_worked_days(payslip and payslip[0] or False))),
                            # 14 TIPO LINEA
                            personal_movement.line_type,#self.get_line_type(payslip.personal_movement_ids, personal_movement),
                            # 15 COD MOVI
                            personal_movement.personal_movements,
                            # 16 FECHA DESDE MOVIMIENTO PERSONAL (Si declara mov. personal 1, 3, 4, 5, 6, 7, 8 y 11 Fecha Desde es obligatorio y debe estar dentro del periodo de remun)
                            personal_movement.date_start.strftime("%d/%m/%Y") if personal_movement.personal_movements != '0' else '00/00/0000',
                            # 17 FECHA HASTA MOVIMIENTO PERSONAL
                            personal_movement.date_end.strftime("%d/%m/%Y") if personal_movement.personal_movements != '0' else '00/00/0000',
                            # 18 TRAMO FAM
                            payslip.contract_id.section_id.name[6:7] if payslip.contract_id.section_id else '',
                            # 19 CARGAS SIMPLES
                            payslip.contract_id.simple_charge,
                            # 20 CARGA MAT
                            payslip.contract_id.maternal_charge,
                            # 21 CARBA INV
                            payslip.contract_id.disability_charge,
                            # 22 ASIG FAMILIAR
                            self.get_payslip_lines_value(payslip, 'ASIGFAM') if self.get_payslip_lines_value(payslip,
                                                                                                             'ASIGFAM') else '0',
                            # 23 ASIG RETRO
                            self.get_payslip_lines_value(payslip, 'ASFRETRO') if self.get_payslip_lines_value(payslip,
                                                                                                              'ASFRETRO') else '0',
                            # 24 REINT CARGAS
                            str(round(float(self.get_payslip_lines_value(payslip, 'RCFAM')))),
                            # 25 SUBSIDIO TRABAJADOR JOVEN
                            'N' if not payslip.contract_id.young_worker_allowance else 'S',
                            # 26 AFP
                            payslip.contract_id.afp_id.code if payslip.contract_id.afp_id.code else '00',
                            # 27 IMPO AFP
                            str(round(float(self.get_taxable_afp(payslip and payslip[0] or False,
                                                                 self.get_payslip_lines_value(payslip, 'TOTIM'),
                                                                 self.get_payslip_lines_value(payslip,
                                                                                              'IMPLIC'))))),
                            # 28 COT AFP
                            str(round(float(self.get_payslip_lines_value(payslip, 'PREV'))) if self.get_payslip_lines_value(payslip,'PREV') else '0'),
                            # 29 APORTE SIS
                            str(round(float(self.get_payslip_lines_value(payslip, 'SIS'))) if self.get_payslip_lines_value(payslip,'PREV') else '0'),
                            # 30 AHORRO VOLUNTARIO AFP
                            str(self.get_afp_saving(payslip.contract_id)),
                            # 31 Renta Imp. Sust.AFP
                            '0',
                            # 32 Tasa Pactada (Sustit.)
                            '0',
                            # 33 Aporte Indemn. (Sustit.)
                            '0',
                            # 34 N Periodos (Sustit.)
                            '0',
                            # 35 Periodo desde (Sustit.)
                            '0',
                            # 36 Periodo Hasta (Sustit.)
                            '0',
                            # 37 Puesto de Trabajo Pesado
                            ' ',
                            # 38 % Cotizacion Trabajo Pesado
                            '0',
                            # 39 Cotizacion Trabajo Pesado
                            '0',
                            # 40 codigo INS APVI
                            payslip.contract_id.apv_id.code if self.get_payslip_lines_value(payslip, 'APV') and self.get_payslip_lines_value(payslip, 'APV') != '0' else '0',
                            # 41 NUM CONTRATO APVI
                            '0',
                            # 42 FORMA DE PAGO APVI
                            payslip.contract_id.apv_payment_term if self.get_payslip_lines_value(payslip, 'APV') else '0',
                            # 43 COTIZACION APVI
                            str(round(float(self.get_payslip_lines_value(payslip, 'APV')))) if str(
                                round(float(self.get_payslip_lines_value(payslip, 'APV')))) else '0',
                            # 44 COTIZACION DEPOSITO CONV
                            ' ',
                            # 45 Codigo Institucion Autorizada APVC
                            '0',
                            # 46 Numero de Contrato APVC
                            '0',
                            # 47 Forma de Pago APVC
                            '0',
                            # 48 Cotizacion Trabajador APVC
                            '0',
                            # 49 Cotizacion Empleador APVC
                            '0',
                            # 50 RUT Afiliado Voluntario 9 (11)
                            '0',
                            # 51 DV Afiliado Voluntario
                            ' ',
                            # 52 Apellido Paterno VOLUNTARIO
                            ' ',
                            # 53 Apellido Materno VOLUNTARIO
                            '',
                            # 54 Nombres VOLUNTARIO
                            ' ',
                            # 55 CODIGO MOVIMIENTO PERSONAL VOLUNTARIO
                            # Código Glosa
                            # 0 Sin Movimiento en el Mes
                            # 1 Contratación a plazo indefinido
                            # 2 Retiro
                            # 3 Subsidios
                            # 4 Permiso Sin Goce de Sueldos
                            # 5 Incorporación en el Lugar de Trabajo
                            # 6 Accidentes del Trabajo
                            # 7 Contratación a plazo fijo
                            # 8 Cambio Contrato plazo fijo a plazo indefinido
                            # 11 Otros Movimientos (Ausentismos)
                            # 12 Reliquidación, Premio, Bono
                            # TODO LIQUIDACION
                            '0',
                            # 56 Fecha inicio movimiento personal (dia-mes-año)
                            '0',
                            # 57 Fecha fin movimiento personal (dia-mes-año)
                            '0',
                            # 58 Codigo de la AFP
                            '0',
                            # 59 Monto Capitalizacion Voluntaria
                            '0',
                            # 60 Monto Ahorro Voluntario
                            '0',
                            # 61 Numero de periodos de cotizacion
                            '0',
                            # 62 Codigo EX-Caja Regimen
                            '0',
                            # 63 Tasa Cotizacion Ex-Caja Prevision
                            '0',
                            # 64 RENTA IMPONIBLE IPS-FONASA
                            self.get_total_taxable_fonasa(payslip, self.get_payslip_lines_value(payslip, 'TOTIM'), self.get_payslip_lines_value(payslip, 'FONASA')),
                            # 65 COTIZACION OBLIGATORIO IPS
                            '0',
                            # 66 RENTA IMPONIBL DESAHUCIO
                            '0',
                            # 67 CODIGO EX-CAJA REGIMEN DESHAUCIO
                            '0',
                            # 68 TASA COTIZACION DESAHUCIO
                            '0',
                            # 69 COTIZACION DESHAUCIO
                            '0',
                            # 70 COTIZACION FONASA
                            self.get_payslip_lines_value(payslip, 'FONASA') if payslip.contract_id.is_fonasa else '0',
                            # 71 COTIZACION ACC. TRABAJO ISL
                            str(round(float(self.get_payslip_lines_value(payslip, 'ISL')))) if self.get_payslip_lines_value(
                                payslip, 'ISL') else '0',
                            # 72 BONIFICACION LEY 15386
                            '0',
                            # 73 DESCUENTO POR CARGAS FAMILIARES EN IPS
                            '0',
                            # 74 BONOS GOBIERNO
                            '0',
                            # 75 CODIGO INSTITUCION DE SALUD
                            payslip.contract_id.isapre_id.code if payslip.contract_id.is_fonasa is False else '07',
                            # 76 NUMERO DEL FUN
                            '' if payslip.contract_id.is_fonasa is True else payslip.contract_id.fun_number if payslip.contract_id.fun_number else '',
                            # 77 RENTA IMPONIBLE ISAPRE
                            '0' if payslip.contract_id.is_fonasa is True else self.get_taxable_health(
                                payslip and payslip[0] or False, self.get_payslip_lines_value(payslip, 'TOTIM')),

                            # 78 MONEDA DEL PLAN PACTADO ISAPRE
                            '1' if payslip.contract_id.currency_isapre_id.name == 'CLP' or payslip.contract_id.is_fonasa is True else '2',
                            # 79 COTIZACION PACTADA
                            '0' if payslip.contract_id.is_fonasa is True else payslip.contract_id.isapre_agreed_quotes_uf,
                            # 80 COTIZACION OBLIGATORIA ISAPRE
                            '0' if payslip.contract_id.is_fonasa is True else
                            str(round(float(self.get_payslip_lines_value(payslip, 'SALUD')))),
                            # 81 COTIZACION ADICIONAL VOLUNTARIA
                            '0' if payslip.contract_id.is_fonasa is True else str(
                                round(float(self.get_payslip_lines_value(payslip, 'ADISA')))),
                            # 82 MONTO GARANTIA EXPLICITA DE SALUD
                            '0',
                            # 83 CODIGO CCAF
                            payslip.indicator_id.ccaf_id.code if payslip.indicator_id.ccaf_id.code else '00',
                            # 84 RENTA IMPONIBLE CCAF
                            self.verify_ccaf(self.get_payslip_lines_value(payslip, 'TOTIM'),
                                             payslip.indicator_id.mapped('data_ids').filtered(lambda a: 'AFP' in a.name and a.type == '4').value) if self.get_payslip_lines_value(
                                payslip, 'TOTIM') else "0",
                            # 85 CREDITOS PERSONALES CCAF
                            self.get_payslip_lines_value(payslip, 'PCCAF') if self.get_payslip_lines_value(payslip, 'PCCAF') else '0',
                            # 86 DESCUENTO DENTAL CCAF
                            self.get_payslip_lines_value(payslip, 'DDCCAF') if self.get_payslip_lines_value(payslip, 'DDCCAF') else '0',
                            # 87 DESCUENTOS POR LEASING
                            self.get_payslip_lines_value(payslip, 'ACCAF') if self.get_payslip_lines_value(payslip, 'ACCAF') else '0',
                            # 88 DESCUENTOS POR SEGURO DE VIDA CCAF
                            self.get_payslip_lines_value(payslip, 'DSVCCAF') if self.get_payslip_lines_value(payslip, 'DSVCCAF') else '0',
                            # 89 OTROS DESCUENTOS CCAF
                            self.get_payslip_lines_value(payslip, 'ODESCCAF') if self.get_payslip_lines_value(payslip, 'ODESCCAF') else '0',
                            # 90 COTIZACION A CCAF DE NO AFILIADOS A ISAPRES
                            self.get_payslip_lines_value(payslip, 'CAJACOMP') if self.get_payslip_lines_value(payslip, 'CAJACOMP') else '0',
                            # 91 DESCUENTOS CARGAS FAMILIARES CCAF
                            self.get_payslip_lines_value(payslip, 'DCFCCAF') if self.get_payslip_lines_value(payslip, 'DCFCCAF') else '0',
                            # 92 Otros descuentos CCAF 1 (USO FUTURO)
                            '0',
                            # 93 Otros descuentos CCAF 2 (USO FUTURO)
                            '0',
                            # 94 Bonos Gobierno  CCAF (USO FUTURO)
                            '0',
                            # 95 CODIGO SUCURSAL CCAF (USO FUTURO)
                            '0',
                            # 96 CODIGO MUTUALIDAD
                            payslip.indicator_id.mutuality_id.code if payslip.indicator_id.has_mutuality and payslip.indicator_id.mutuality_id.code else "00",
                            # 97 RENTA IMPOBILE MUTUAL
                            self.get_mutuality_taxable(payslip and payslip[0] or False,
                                                       self.get_payslip_lines_value(payslip, 'TOTIM')),
                            # 98 COTIZACION ACCIDENTE DEL TRABAJO
                            str(round(float(self.get_payslip_lines_value(payslip, 'MUT')))) if self.get_payslip_lines_value(payslip,
                                                                                                                            'MUT') else '0',
                            # 99 CODIGO DE SUCURSAL PAGO MUTUAL
                            '0',
                            # 100 RENTA IMPONIBLE SEGUR CESANTIA
                            self.get_mutuality_taxable(payslip and payslip[0] or False, self.get_payslip_lines_value(payslip, 'TOTIM')),
                            # 101 APORTE TRABAJADOR SEGURO CESANTIA
                            str(round(float(self.get_payslip_lines_value(payslip, 'SECE')))) if self.get_payslip_lines_value(
                                payslip, 'SECE') else '0',
                            # 102 APORTE EMPLEADO SEGURO CESANTIA
                            self.get_payslip_lines_value(payslip, 'SECEEMP') if self.get_payslip_lines_value(payslip, 'SECEEMP') else '0',
                            # 103 RUT PAGADORA SUBSIDIO
                            self._shorten_str(subsidy_payer_rut, 11),
                            # 104 DV RUT PAGADORA SUBSIDIO
                            self._shorten_str(subsidy_payer_rut_dv, 1),
                            # 105 Centro de costos Trabajador
                            '0'
                        ]

                        writer.writerow([str(l) for l in line_employee])
                except Exception as e:
                    raise models.ValidationError(f'Error {e}')
        else:
            raise models.ValidationError(f'No existen Nóminas entre periodo {self.date_from} - {self.date_to}')

        file_name = "Previred_{}{}.txt".format(self.date_to,
                                               self.company_id.display_name.replace('.', ''))
        attachment_id = self.env['ir.attachment'].sudo().create({
            'name': file_name,
            'datas': base64.encodebytes(output.getvalue().encode())
        })

        action = {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
            'target': 'self',
        }
        return action

    def generate_centralization_book(self):
        file_name = 'temp'
        #file_name = 'C:/Users/Desarrollo/Downloads/temp.xls'
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet(self.company_id.name)
        number_format = workbook.add_format({'num_format': '#,###'})
        indicators = self.env['custom.indicators'].sudo().search([('id', '=', f'{self.indicator_id.id}')])
        if not indicators:
            raise models.ValidationError(f'No existen datos del mes de {self.indicator_id.name}')
        if indicators.state != 'done':
            raise models.ValidationError(
                f'Los indicadores previsionales del mes de {indicators.name} no se encuentran validados')
        row = 1
        col = 0

        payslips = self.env['hr.payslip'].sudo().search([('indicator_id', '=', self.indicator_id.id),('state','=','done')])

        bold_format = workbook.add_format({'bold': True})

        hr_rule_category = self.env['hr.salary.rule.category'].search([])
        debit_rule_ids = hr_rule_category.filtered(lambda x: x.id in (
            self.env.ref('dimabe_rrhh.custom_hr_salary_rule_category_taxable').id,
            self.env.ref('dimabe_rrhh.custom_hr_salary_rule_category_not_taxable').id))

        credit_rule_ids = hr_rule_category.filtered(lambda x: x.id in (
            self.env.ref('dimabe_rrhh.custom_hr_salary_rule_category_discount').id,
            self.env.ref('dimabe_rrhh.custom_hr_salary_rule_category_other_discount').id,
            self.env.ref('dimabe_rrhh.custom_hr_salary_rule_forecast').id,
            (self.env.ref('dimabe_rrhh.custom_hr_salary_rule_health').id)))

        move_line_ids = payslips.mapped('move_id')[0].mapped('line_ids')

        account_struct_id = payslips.mapped('struct_id')[0].journal_id.default_account_id

        for line in payslips.mapped('line_ids').filtered(lambda x: x.total > 0):
            debit = 0
            credit = 0
            account_id = None

            exception_codes = []
            exception_codes.append('LIQ')
            if line.slip_id.contract_id.is_fonasa == False and line.slip_id.contract_id.isapre_id != False:
                exception_codes.append('ISAP')
            if line.slip_id.contract_id.is_fonasa:
                exception_codes.append('FONASA')
                exception_codes.append('CAJACOMP')

            debit_credit = False
            if line.salary_rule_id.account_debit and line.salary_rule_id.account_credit:
                if line.salary_rule_id.category_id.id in debit_rule_ids.ids:
                    debit = line.total
                    account_id = line.salary_rule_id.account_debit
                elif line.salary_rule_id.category_id.id in credit_rule_ids.ids or line.code in exception_codes:
                    credit = line.total
                    account_id = line.salary_rule_id.account_credit
                else:
                    debit_credit = True
            else:
                continue


            col = 0
            worksheet.write(0, 0, 'Cuenta', bold_format)
            worksheet.write(0, 1, 'Nombre', bold_format)
            worksheet.write(0, 2, 'CC', bold_format)
            worksheet.write(0, 3, 'Nombre CC', bold_format)
            worksheet.write(0, 4, 'Debe', bold_format)
            worksheet.write(0, 5, 'Haber', bold_format)
            worksheet.write(0, 6, 'Rut', bold_format)
            worksheet.write(0, 7, 'DV', bold_format)
            
            analytic_account_id = None

            if self.env.user.company_id.analitic_account == '1':
                analytic_account_id = line.slip_id.analytic_account_id
            if self.env.user.company_id.analitic_account == '2':
                analytic_account_id = line.slip_id.contract_id.analytic_account_id
            if self.env.user.company_id.analitic_account == '3':
                analytic_account_id = line.slip_id.employee_id.department_id.analytic_account_id

            if not debit_credit:
                worksheet.write(row, col, account_id.code)
                col += 1
                worksheet.write(row, col, account_id.name)
                col += 1
                worksheet.write(row, col, analytic_account_id.code if analytic_account_id.code else '')
                col += 1
                worksheet.write(row, col, analytic_account_id.name if analytic_account_id.name else '')
                col += 1
                worksheet.write(row, col, debit)
                col += 1
                worksheet.write(row, col, credit)
                col += 1
                worksheet.write(row, col, line.slip_id.employee_id.identification_id.split('-')[0] if line.slip_id.employee_id.identification_id else '')
                col += 1
                worksheet.write(row, col, line.slip_id.employee_id.identification_id.split('-')[1] if line.slip_id.employee_id.identification_id else '')
                row += 1

            else:

                worksheet.write(row, col, line.salary_rule_id.account_debit.code)
                col += 1
                worksheet.write(row, col, line.salary_rule_id.account_debit.name)
                col += 1
                worksheet.write(row, col, analytic_account_id.code if analytic_account_id.code else '')
                col += 1
                worksheet.write(row, col, analytic_account_id.name if analytic_account_id.name else '')
                col += 1
                worksheet.write(row, col, line.total)
                col += 1
                worksheet.write(row, col, 0)
                col += 1
                worksheet.write(row, col, line.slip_id.employee_id.identification_id.split('-')[0] if line.slip_id.employee_id.identification_id else '')
                col += 1
                worksheet.write(row, col, line.slip_id.employee_id.identification_id.split('-')[1] if line.slip_id.employee_id.identification_id else '')
                row += 1

                col = 0
                worksheet.write(row, col, line.salary_rule_id.account_credit.code)
                col += 1
                worksheet.write(row, col, line.salary_rule_id.account_credit.name)
                col += 1
                worksheet.write(row, col,  analytic_account_id.code if analytic_account_id.code else '')
                col += 1
                worksheet.write(row, col, analytic_account_id.name if analytic_account_id.name else '')
                col += 1
                worksheet.write(row, col, 0)
                col += 1
                worksheet.write(row, col, line.total)
                col += 1
                worksheet.write(row, col, line.slip_id.employee_id.identification_id.split('-')[ 0] if line.slip_id.employee_id.identification_id else '')
                col += 1
                worksheet.write(row, col, line.slip_id.employee_id.identification_id.split('-')[ 1] if line.slip_id.employee_id.identification_id else '')
                row += 1

        if account_struct_id.id in move_line_ids.mapped('account_id').ids:
            col = 0
            worksheet.write(row, col, account_struct_id.code)
            col += 1
            worksheet.write(row, col, account_struct_id.name)
            col += 1
            worksheet.write(row, col, '')
            col += 1
            worksheet.write(row, col, '')
            col += 1
            worksheet.write(row, col, move_line_ids.filtered(lambda x: x.account_id.id == account_struct_id.id)[0].debit)
            col += 1
            worksheet.write(row, col, move_line_ids.filtered(lambda x: x.account_id.id == account_struct_id.id)[0].credit)
            col += 1
            worksheet.write(row, col, '')
            col += 1
            worksheet.write(row, col, '')
            row += 1

        workbook.close()
        with open(file_name, "rb") as file:
            file_base64 = base64.b64encode(file.read())

        file_name = 'Libro de Centralización {}'.format(indicators.name)
        attachment_id = self.env['ir.attachment'].sudo().create({
            'name': file_name,
            'datas': file_base64
        })
        action = {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
            'target': 'current',
        }
        return action


    @api.model
    def get_worked_days(self, payslip):
        worked_days = 0
        if payslip:
            for line in payslip.worked_days_line_ids:
                if line.code == 'WORK100':
                    worked_days = line.number_of_days
        return worked_days

    @api.model
    def get_qty_extra_hours(self, payslip):
        worked_days = 0
        if payslip:
            for line in payslip.input_line_ids:
                if line.code == 'HEX50':
                    worked_days = line.amount
        return worked_days

    @api.model
    def get_qty_discount_hours(self, payslip):
        worked_days = 0
        if payslip:
            for line in payslip.input_line_ids:
                if line.code == 'HEXDE':
                    worked_days = line.amount
        return worked_days

    @api.model
    def _shorten_str(self, text, size=1):
        c = 0
        shorten_text = ""
        while c < size and c < len(text):
            shorten_text += text[c]
            c += 1
        return shorten_text

    @api.model
    def _format_str(self, text, size=1):
        c = 0
        formated_text = ""
        special_chars = [
            ['á', 'a'],
            ['é', 'e'],
            ['í', 'i'],
            ['ó', 'o'],
            ['ú', 'u'],
            ['ñ', 'n'],
            ['Á', 'A'],
            ['É', 'E'],
            ['Í', 'I'],
            ['Ó', 'O'],
            ['Ú', 'U'],
            ['Ñ', 'N']]

        while c < size and c < len(text):
            formated_text += text[c]
            c += 1
        for char in special_chars:
            try:
                formated_text = formated_text.replace(char[0], char[1])
            except:
                pass
        return formated_text

    @api.model
    def get_nacionality(self, country):
        if country == 46:
            return 0
        else:
            return 1

    @api.model
    def get_pay_method(self, employee):
        # 01 Remuneraciones del mes
        # 02 Gratificaciones
        # 03 Bono Ley de Modernizacion Empresas Publicas
        # TODO: en base a que se elije el tipo de pago???
        return 1

    @api.model
    def get_provisional_regime(self, contract):
        if contract.is_pensionary is True:
            return 'SIP'
        else:
            return 'AFP'

    @api.model
    def get_line_type(self, personal_movement_ids, personal_movement):
        # 00 Linea Principal o Base
        # 01 Linea Adicional
        # 02 Segundo Contrato
        # 03 Movimiento de Personal Afiliado Voluntario
        if personal_movement_ids[0] == personal_movement:
            return '00'
        return '01'

    @api.model
    def get_payslip_lines_value(self, obj, rule):
        val = 0
        lines = self.env['hr.payslip.line']
        details = lines.search([('slip_id', '=', obj.id), ('code', '=', rule)])
        val = round(details.total)
        return val

    @api.model
    def get_taxable_afp(self, payslip, TOTIM, LIC):
        LIC_2 = float(LIC)
        TOTIM_2 = float(TOTIM)
        if LIC_2 > 0:
            TOTIM = LIC
        if payslip.contract_id.is_pensionary is True:
            return '0.0'
        elif TOTIM_2 >= round(
                payslip.indicator_id.mapped('data_ids').filtered(lambda a: 'AFP' in a.name and a.type == '4').value):
            return str(round(float(
                payslip.indicator_id.mapped('data_ids').filtered(lambda a: 'AFP' in a.name and a.type == '4').value)))
        else:
            return str(round(float(round(TOTIM_2))))

    @api.model
    def verify_ips(self, TOTIM, TOPE):
        if float(TOTIM) > (TOPE):
            data = round(float(TOPE))
            return data
        else:
            return TOTIM

    @api.model
    def get_taxable_health(self, payslip, TOTIM):
        result = 0
        if float(TOTIM) >= round(
                payslip.indicator_id.mapped('data_ids').filtered(lambda a: 'AFP' in a.name and a.type == '4').value):
            return str(round(float(
                payslip.indicator_id.mapped('data_ids').filtered(lambda a: 'AFP' in a.name and a.type == '4').value)))
        else:
            return str(round(float(TOTIM)))

    @api.model
    def get_mutuality_taxable(self, payslip, TOTIM):
        if payslip.indicator_id.has_mutuality is False:
            return 0
        elif payslip.contract_id.type_id.code == 4:  # SUELDO EMPRESARIAL
            return 0
        elif float(TOTIM) >= round(
                payslip.indicator_id.mapped('data_ids').filtered(lambda a: 'AFP' in a.name and a.type == '4').value):
            return round(
                payslip.indicator_id.mapped('data_ids').filtered(lambda a: 'AFP' in a.name and a.type == '4').value)
        else:
            return round(float(TOTIM))

    @api.model
    def get_taxable_unemployment_insurance(self, payslip, TOTIM, LIC):
        LIC_2 = float(LIC)
        TOTIM_2 = float(TOTIM)
        if TOTIM_2 < payslip.indicator_id.mapped('data_ids').filtered(
                lambda a: a.type == 5 and 'Trab. Dependientes e Independientes' in a.name).value:
            return 0
        if LIC_2 > 0:
            TOTIM = LIC
        if payslip.contract_id.is_pensionary is True:
            return 0
        elif payslip.contract_id.type_id.code == 4:  # 'Sueldo Empresarial'
            return 0
        elif TOTIM_2 >= round(payslip.indicator_id.mapped('data_ids').filtered(
                lambda a: a.type == 4 and 'Para Seguro de Cesantía' in a.name).value):
            return str(round(
                float(round(payslip.indicator_id.mapped('data_ids').filtered(
                    lambda a: a.type == 4 and 'Para Seguro de Cesantía' in a.name).value))))
        else:
            return str(round(float(round(TOTIM_2))))

    @api.model
    def verify_quotation_afc(self, TOTIM, indicator, contract):
        totimp = float(TOTIM)
        if contract.type_id.code == 2:  # Plazo Fijo
            return round(totimp * indicator.mapped('data_ids').filtered(
                lambda a: a.name == 'Contrato Plazo Fijo Empleador').percentage_value / 100)
        elif contract.type_id.code == 1:  # Plazo Indefinido
            return round(totimp * indicator.mapped('data_ids').filtered(
                lambda a: a.name == 'Contrato Plazo Indefinido Empleador').percentage_value / 100)
        else:
            return 0

    @api.model
    def verify_ccaf(self, TOTIM, TOPE):
        if TOTIM:
            TOTIM_2 = float(TOTIM)
            if TOTIM_2 > (TOPE):
                data = round(float(TOPE))
                return str(data)
            else:
                return str(TOTIM)
        else:
            return "0"

    @api.model
    def get_afp_saving(self, contract):
        for saving in contract.other_saving_ids:
            if saving.salary_rule_id.code == 'AAFP':
                return saving.amount
        return 0

    @api.model
    def get_employee_id(self, move):
        employee_id = self.env['hr.payslip'].search([('move_id','=',move)]).employee_id
        return employee_id

    @api.model
    def get_total_taxable_fonasa(self, payslip, TOTIM, fonasa):
        if fonasa > 0 or not payslip.indicator_id.has_mutuality:
            maximus = payslip.indicator_id.mapped('data_ids').filtered(lambda a: a.type =='4' and 'IPS' in a.name).value
            if TOTIM > maximus:
                return maximus
            return TOTIM
        return 0

    @api.model
    def get_analytic_account_by_paysip(self, pay):
        if pay.account_analytic_id and self.env.user.company_id.analitic_account == '1':
            return pay.account_analytic_id
        elif pay.contract_id.analytic_account_id and self.env.user.company_id.analitic_account == '2':
            return pay.contract_id.analytic_account_id
        elif pay.contract_id.department_id.analytic_account_id and self.env.user.company_id.analitic_account == '3':
            return pay.contract_id.department_id.analytic_account_id     
        return None

    @api.model
    def get_max_analytic_account(self, payslips):
        if self.env.user.company_id.analitic_account == '1':
            return max(payslips.mapped('account_analytic_id').mapped('name'), key=len)
        elif self.env.user.company_id.analitic_account == '2':
            return max(payslips.mapped('contract_id').mapped('analytic_account_id').mapped('name'), key=len)
        elif self.env.user.company_id.analitic_account == '3':
            return max(
                payslips.mapped('contract_id').mapped('department_id').mapped('analytic_account_id').mapped('name'),
                key=len)
        return ''
