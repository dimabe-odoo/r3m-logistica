from odoo import fields, models, api
import requests
from bs4 import BeautifulSoup
from odoo.addons import decimal_precision as dp
from datetime import datetime
from ..utils.taxe_unique import getTaxeUniques


class CustomIndicators(models.Model):
    _name = 'custom.indicators'
    _order = 'create_date desc'
    _description = "Indicadores Previsionales"

    name = fields.Char('Nombre')

    data_ids = fields.One2many('custom.indicators.data', 'indicator_id', string='Datos')

    unique_tax_ids = fields.One2many('custom.unique.tax', 'indicator_id', string="Impuesto Único 2° Categoría")

    month = fields.Selection(
        [('jan', 'Enero'), ('feb', 'Febrero'), ('mar', 'Marzo'), ('apr', 'Abril'), ('may', 'Mayo'), ('jun', 'Junio'),
         ('jul', 'Julio'), ('aug', 'Agosto'), ('sep', 'Septiembre'), ('oct', 'Octubre'), ('nov', 'Noviembre'),
         ('dec', 'Diciembre')], string='Mes')

    year = fields.Float('Año', default=datetime.now().strftime('%Y'), digits='Year')

    ccaf_id = fields.Many2one('custom.data', 'Caja de Compensación')

    ccaf_rate = fields.Float('Tasa CCAF')

    national_health_fund_rate = fields.Float('Tasa Fonasa')

    ips_rate = fields.Float('Tasa IPS')

    max_taxable_health_rate = fields.Float('Tope Imponible Salud %')

    has_mutuality = fields.Boolean('Tiene Mutual', default=True)

    mutuality_id = fields.Many2one('custom.data', 'Mutual')

    mutuality_ids = fields.One2many('custom.mutuality.by.company', 'indicator_id', string='Valores por Compañia')

    institute_occupational_safety = fields.Float('ISL', help="Instituto de Seguridad Laboral")

    ccaf_type_id = fields.Integer('Tipo de CCAF',compute="_compute_ccaf_type")

    mutuality_type_id = fields.Integer('Tipo de Mutualidad',compute="_compute_mutuality_type")

    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Validado'),
    ], string=u'Estado', readonly=True, default='draft')

    cl_sanna_law = fields.Float('Ley SANNA %')

    def action_done(self):
        self.write({'state': 'done'})
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    def write(self, vals):
        month = self.month
        year = self.year
        company = self.company_id
        if 'month' in vals.keys():
            month = vals['month']
        if 'year' in vals.keys():
            year = vals['year']
        if 'company_id' in vals.keys():
            company = self.env['res.company'].search([('id', '=', vals['company_id'])])
        vals['name'] = str(month).replace('oct', 'Octubre').replace('nov', 'Noviembre').replace('dec',
                                                                                                'Diciembre').replace(
            'jan', 'Enero').replace('feb', 'Febrero').replace('mar', 'Marzo').replace('apr', 'Abril').replace('may',
                                                                                                              'Mayo').replace(
            'jun', 'Junio').replace('7', 'Julio').replace('aug', 'Agosto').replace('sep', 'Septiembre') + " " + str(
            int(year)) + " " + str(company.name)
        res = super(CustomIndicators, self).write(vals)
        return res

    @api.onchange('month', 'year', 'company_id')
    def get_name(self):
        self.name = str(self.month).replace('oct', 'Octubre').replace('nov', 'Noviembre').replace('dec',
                                                                                                  'Diciembre').replace(
            'jan', 'Enero').replace('feb', 'Febrero').replace('mar', 'Marzo').replace('apr', 'Abril').replace('may',
                                                                                                              'Mayo').replace(
            'jun', 'Junio').replace('7', 'Julio').replace('aug', 'Agosto').replace('sep', 'Septiembre') + " " + str(
            int(self.year)) + " " + self.company_id.name

    @api.model
    def _compute_ccaf_type(self):
        self.ccaf_type_id = self.env.ref('dimabe_rrhh.custom_data_initial_ccaf').id

    @api.model
    def _compute_mutuality_type(self):
        self.mutuality_type_id = self.env.ref('dimabe_rrhh.custom_data_initial_mutuality').id

    @api.model
    def create(self, vals):
        if 'company_id' not in vals.keys():
            raise models.ValidationError('La compañía es requerida')
        company_id = self.env['res.company'].search([('id', '=', vals['company_id'])])
        vals['name'] = f'{self.get_month(vals["month"])} {vals["year"]} {company_id.name}'
        last_indicator = self.env['custom.indicators'].search(
            [('year', '=', vals["year"]), ('state', '=', 'done')]).sorted(lambda x: x.create_date, reverse=True)
        if len(last_indicator) > 0:
            vals['ccaf_id'] = last_indicator[0].ccaf_id.id if last_indicator[0].ccaf_id else None
            vals['ccaf_rate'] = last_indicator[0].ccaf_rate
            vals['national_health_fund_rate'] = last_indicator[0].national_health_fund_rate
            vals['max_taxable_health_rate'] = last_indicator[0].max_taxable_health_rate
            vals['has_mutuality'] = last_indicator[0].has_mutuality
            vals['mutuality_id'] = last_indicator[0].mutuality_id.id if last_indicator[0].mutuality_id else None
            vals['cl_sanna_law'] = last_indicator[0].cl_sanna_law

        res = super(CustomIndicators, self).create(vals)

        if len(last_indicator) > 0:
            if len(last_indicator[0].mutuality_ids) > 0:
                for mutual in last_indicator[0].mutuality_ids:
                    self.env['custom.mutuality.by.company'].create({
                        'company_id': mutual.company_id.id,
                        'value': mutual.value,
                        'indicator_id': res.id
                    })

        return res

    def clear_string(self, cad):
        cad = cad.replace(".", '').replace("$", '').replace(" ", '')
        cad = cad.replace("Renta", '').replace("<", '').replace(">", '')
        cad = cad.replace("=", '').replace("R", '').replace("I", '').replace("%", '')
        cad = cad.replace(",", '.')
        cad = cad.replace("1ff8", "")
        return cad

    def validate_indicator_registered(self):
        indicator_data_ids = self.env['custom.indicators.data'].search([('indicator_id', '=', self.id)])
        if len(indicator_data_ids) > 0:
            for item in indicator_data_ids:
                item.unlink()

    def get_data(self):
        self.validate_indicator_registered()
        link = 'https://www.previred.com/web/previred/indicadores-previsionales'
        data = requests.get(link)
        soup = BeautifulSoup(data.text, 'html.parser')
        tables = soup.find_all('table')
        indicators = []
        values = []
        utm_uta = []
        for table in tables:
            if table == tables[0]:
                uf_value = self.get_table_type_1(table)
                for item in uf_value:
                    row = 0
                    for d in item['data']:
                        self.env['custom.indicators.data'].create({
                            'name': d['title'],
                            'value': d['data'],
                            'value_show': f'$ {d["data"]}',
                            'type': '1',
                            'last_month': row == 0,
                            'indicator_id': self.id
                        })
                        row += 1
            elif table == tables[1]:
                table_data = self.get_utm_uta(table)
                utm_uta = self.get_utm_uta(table)
                self.env['custom.indicators.data'].create({
                    'name': table_data['data'][0]['title'],
                    'value': d['data'],
                    'value_show': f'$ {table_data["data"][0]["value"]}',
                    'type': '2',
                    'indicator_id': self.id
                })
                self.env['custom.indicators.data'].create({
                    'name': table_data['data'][1]['title'],
                    'value': table_data['data'][1]['value'],
                    'value_show': f'$ {table_data["data"][1]["value"]}',
                    'type': '3',
                    'indicator_id': self.id
                })
            elif table == tables[2]:
                table_data = self.get_table_type_1(table)
                for item in table_data:
                    for d in item['data']:
                        self.env['custom.indicators.data'].create({
                            'name': d['title'].replace(':', ''),
                            'value': d['data'],
                            'value_show': f'$ {d["data"]}',
                            'type': '4',
                            'indicator_id': self.id
                        })
            elif table == tables[3]:
                table_data = self.get_table_type_1(table)
                for item in table_data:
                    for d in item['data']:
                        self.env['custom.indicators.data'].create({
                            'name': d['title'].replace(':', ''),
                            'value': d['data'],
                            'value_show': f'$ {d["data"]}',
                            'type': '5',
                            'indicator_id': self.id
                        })
            elif table == tables[4]:
                table_data = self.get_table_type_1(table)
                for item in table_data:
                    for d in item['data']:
                        self.env['custom.indicators.data'].create({
                            'name': d['title'].replace(':', ''),
                            'value': d['data'],
                            'value_show': f'$ {d["data"]}',
                            'type': '6',
                            'indicator_id': self.id
                        })
            elif table == tables[5]:
                table_data = self.get_table_type_1(table)
                for item in table_data:
                    for d in item['data']:
                        self.env['custom.indicators.data'].create({
                            'name': d['title'].replace(':', ''),
                            'value': d['data'],
                            'value_show': f'$ {d["data"]}',
                            'type': '7',
                            'indicator_id': self.id
                        })
            elif table == tables[6]:
                data = self.get_safe(table)
                for d in data:
                    self.env['custom.indicators.data'].create({
                        'name': d['title'],
                        'percentage_show': f'{d["value"]} %',
                        'percentage_value': d['value'],
                        'type': '8',
                        'indicator_id': self.id
                    })
            elif table == tables[7]:
                data = self.get_afp_data(table)
                for d in data:
                    self.env['custom.indicators.data'].create({
                        'name': d['title'],
                        'percentage_show': f'{d["value"]} %',
                        'percentage_value': d['value'],
                        'type': '9',
                        'indicator_id': self.id
                    })
            elif table == tables[8]:
                data = self.get_household_allowance_data(table)
                for d in data:
                    self.env['custom.indicators.data'].create({
                        'name': d['title'],
                        'value': d['value'],
                        'value_show': f'$ {d["value"]}',
                        'type': '10',
                        'indicator_id': self.id
                    })

        taxes = getTaxeUniques(self.get_month(self.month))
        if taxes:
            for item in taxes:
                self.env['custom.unique.tax'].create({
                    'salary_from': item['from'],
                    'salary_to': item['to'],
                    'factor': item['factor'],
                    'amount_to_reduce': item['discount'],
                    'indicator_id': self.id
                })
        else:
            self.createTaxesUniques(utm_uta)

    def get_household_allowance_data(self, table):
        data = []
        a_section_amount = {
            'title': 'Tramo A - Monto',
            'value': self.clear_string(table.select("strong")[4].get_text())
        }
        data.append(a_section_amount)
        a_section_max = {
            'title': 'Tramo A - Tope',
            'value': self.clear_string(table.select("strong")[5].get_text())[1:]
        }
        data.append(a_section_max)

        b_section_amount = {
            'title': 'Tramo B - Monto',
            'value': self.clear_string(table.select("strong")[6].get_text())
        }
        data.append(b_section_amount)
        b_section_max = {
            'title': 'Tramo B - Tope',
            'value': self.clear_string(table.select("strong")[7].get_text())[6:]
        }
        data.append(b_section_max)

        c_section_amount = {
            'title': 'Tramo C - Monto',
            'value': self.clear_string(table.select("strong")[8].get_text())
        }
        data.append(c_section_amount)
        c_section_max = {
            'title': 'Tramo C - Tope',
            'value': self.clear_string(table.select("strong")[9].get_text())[6:]
        }
        data.append(c_section_max)

        return data

    def get_afp_data(self, table):
        data = []
        afp_rate_capital = {
            'title': 'Tasa Afp Capital',
            'value': self.clear_string(table.select("strong")[8].get_text())
        }
        data.append(afp_rate_capital)
        sis_rate_capital = {
            'title': 'Tasa SIS Capital',
            'value': self.clear_string(table.select("strong")[9].get_text())
        }
        data.append(sis_rate_capital)
        sis_rate_independent_capital = {
            'title': 'Tasa SIS Independiente Capital',
            'value': self.clear_string(table.select("strong")[10].get_text())
        }
        data.append(sis_rate_independent_capital)

        afp_rate_cuprum = {
            'title': 'Tasa Afp Cuprum',
            'value': self.clear_string(
                table.select("strong")[11].get_text().replace(" ", '').replace("%", '').replace("1ff8", ''))
        }
        data.append(afp_rate_cuprum)
        sis_rate_cuprum = {
            'title': 'Tasa SIS Cuprum',
            'value': self.clear_string(table.select("strong")[12].get_text())
        }
        data.append(sis_rate_cuprum)
        sis_rate_independent_cuprum = {
            'title': 'Tasa SIS Independiente Cuprum',
            'value': self.clear_string(table.select("strong")[13].get_text())
        }
        data.append(sis_rate_independent_cuprum)

        afp_rate_habitat = {
            'title': 'Tasa Afp Habitat',
            'value': self.clear_string(table.select("strong")[14].get_text())
        }
        data.append(afp_rate_habitat)
        sis_rate_habitat = {
            'title': 'Tasa SIS Habitat',
            'value': self.clear_string(table.select("strong")[15].get_text())
        }
        data.append(sis_rate_habitat)
        sis_rate_independent_habitat = {
            'title': 'Tasa SIS Independiente Habitat',
            'value': self.clear_string(table.select("strong")[16].get_text())
        }
        data.append(sis_rate_independent_habitat)

        afp_rate_planvital = {
            'title': 'Tasa Afp PlanVital',
            'value': self.clear_string(table.select("strong")[17].get_text())
        }
        data.append(afp_rate_planvital)
        sis_rate_planvital = {
            'title': 'Tasa SIS PlanVital',
            'value': self.clear_string(table.select("strong")[18].get_text())
        }
        data.append(sis_rate_planvital)
        sis_rate_independent_planvital = {
            'title': 'Tasa SIS Independiente PlanVital',
            'value': self.clear_string(table.select("strong")[19].get_text())
        }
        data.append(sis_rate_independent_planvital)

        afp_rate_provida = {
            'title': 'Tasa Afp Provida',
            'value': self.clear_string(
                table.select("strong")[20].get_text().replace(" ", '').replace("%", '').replace("1ff8", ''))
        }
        data.append(afp_rate_provida)
        sis_rate_provida = {
            'title': 'Tasa SIS Provida',
            'value': self.clear_string(table.select("strong")[21].get_text())
        }
        data.append(sis_rate_provida)
        sis_rate_independent_provida = {
            'title': 'Tasa SIS Independiente Provida',
            'value': self.clear_string(table.select("strong")[22].get_text())
        }
        data.append(sis_rate_independent_provida)

        afp_rate_modelo = {
            'title': 'Tasa Afp Modelo',
            'value': self.clear_string(table.select("strong")[23].get_text())
        }
        data.append(afp_rate_modelo)
        sis_rate_modelo = {
            'title': 'Tasa SIS Modelo',
            'value': self.clear_string(table.select("strong")[24].get_text())
        }
        data.append(sis_rate_modelo)

        sis_rate_independent_modelo = {
            'title': 'Tasa SIS Independiente Modelo',
            'value': self.clear_string(table.select("strong")[25].get_text())
        }
        data.append(sis_rate_independent_modelo)

        afp_rate_uno = {
            'title': 'Tasa Afp Uno',
            'value': self.clear_string(table.select("strong")[26].get_text())
        }
        data.append(afp_rate_uno)
        sis_rate_uno = {
            'title': 'Tasa SIS Uno',
            'value': self.clear_string(table.select("strong")[27].get_text())
        }
        data.append(sis_rate_uno)
        sis_rate_independent_uno = {
            'title': 'Tasa SIS Independiente Uno',
            'value': self.clear_string(table.select("strong")[28].get_text())
        }
        data.append(sis_rate_independent_uno)

        return data

    def get_safe(self, table):
        data = []
        contract_undefined_employer = {'title': 'Contrato Plazo Indefinido Empleador',
                                       'value': self.clear_string(table.select("strong")[5].get_text())}
        data.append(contract_undefined_employer)

        contract_undefined_employee = {'title': 'Contrato Plazo Indefinido Trabajador',
                                       'value': self.clear_string(table.select("strong")[6].get_text())}
        data.append(contract_undefined_employee)

        contract_fixed_term_employer = {'title': 'Contrato Plazo Fijo Empleador',
                                        'value': self.clear_string(table.select("strong")[7].get_text())}
        data.append(contract_fixed_term_employer)

        contract_undefined_eleven_or_more = {'title': 'Plazo Indefinido 11 años o más',
                                             'value': self.clear_string(table.select("strong")[9].get_text())}
        data.append(contract_undefined_eleven_or_more)

        private_home_worker = {'title': 'Trabajador Casa Particular',
                               'value': self.clear_string(table.select("strong")[11].get_text())}
        data.append(private_home_worker)
        return data

    def get_utm_uta(self, table):
        title_principal = f"{table.find_all('td')[0].get_text()} {table.find_all('td')[3].get_text()}"
        list = []
        title = ''
        value = 0.0
        for td in table.find_all('td'):
            if td == table.find_all('td')[0] or td == table.find_all('td')[3]:
                continue
            else:
                if self.clear_string(td.get_text()).isdigit():
                    value = float(self.clear_string(td.get_text()))
                else:
                    title = self.clear_string(td.get_text())
                if value != 0.0:
                    list.append({
                        'title': title,
                        'value': value
                    })
        list[0]['title'] = 'UTM'
        return {'title': title_principal, 'data': list}

    def get_table_type_1(self, table):
        values = []
        uf = []
        title = ''
        value = 0.0
        subtitle = ''
        for td in table.find_all('td'):
            if td == table.select('td')[0]:
                title = td.get_text()
            else:
                if '$' in td.get_text():
                    value = float(self.clear_string(td.get_text()))
                else:
                    subtitle = td.get_text()
                if value == 0.0:
                    continue
                values.append({
                    'title': subtitle,
                    'data': value
                })
                value = 0.0
                subtitle = ''
        uf.append({
            'title': title,
            'data': values
        })
        return uf

    def get_month(self, month):
        if 'jan' == month:
            return 'Enero'
        elif 'feb' == month:
            return 'Febrero'
        elif 'mar' == month:
            return 'Marzo'
        elif 'apr' == month:
            return 'Abril'
        elif 'may' == month:
            return 'Mayo'
        elif 'jun' == month:
            return 'Junio'
        elif 'jul' == month:
            return 'Julio'
        elif 'aug' == month:
            return 'Agosto'
        elif 'sep' == month:
            return 'Septiembre'
        elif 'oct' == month:
            return 'Octubre'
        elif 'nov' == month:
            return 'Noviembre'
        elif 'dec' == month:
            return 'Diciembre'

    def createTaxesUniques(self, utm_uta):
        utm = 0
        if len(utm_uta['data']) > 0:
            for item in utm_uta['data']:
                if item['title'] == 'UTM':
                    utm = item['value']
        if utm != 0:
            self.clean_unique_tax_registered()
            self.env['custom.unique.tax'].create({
                'salary_from': utm * 13.5 + 0.01,
                'salary_to': utm * 30,
                'factor': 0.04,
                'amount_to_reduce': utm * 0.54,
                'indicator_id': self.id
            })

            self.env['custom.unique.tax'].create({
                'salary_from': utm * 30 + 0.01,
                'salary_to': utm * 50,
                'factor': 0.08,
                'amount_to_reduce': utm * 1.74,
                'indicator_id': self.id
            })

            self.env['custom.unique.tax'].create({
                'salary_from': utm * 50 + 0.01,
                'salary_to': utm * 70,
                'factor': 0.135,
                'amount_to_reduce': utm * 4.49,
                'indicator_id': self.id
            })

            self.env['custom.unique.tax'].create({
                'salary_from': utm * 70 + 0.01,
                'salary_to': utm * 90,
                'factor': 0.23,
                'amount_to_reduce': utm * 11.14,
                'indicator_id': self.id
            })

            self.env['custom.unique.tax'].create({
                'salary_from': utm * 90 + 0.01,
                'salary_to': utm * 120,
                'factor': 0.304,
                'amount_to_reduce': utm * 17.8,
                'indicator_id': self.id
            })

            self.env['custom.unique.tax'].create({
                'salary_from': utm * 120 + 0.01,
                'salary_to': utm * 310,
                'factor': 0.35,
                'amount_to_reduce': utm * 23.32,
                'indicator_id': self.id
            })

            self.env['custom.unique.tax'].create({
                'salary_from': utm * 310 + 0.01,
                'salary_to': 0,
                'factor': 0.4,
                'amount_to_reduce': utm * 38.82,
                'indicator_id': self.id
            })
        else:
            raise models.ValidationError('Hay un problema con obtener el valor de UTM')

    def clean_unique_tax_registered(self):
        unique_tax_ids = self.env['custom.unique.tax'].search([('indicator_id', '=', self.id)])
        if len(unique_tax_ids) > 0:
            for item in unique_tax_ids:
                item.unlink()

    def get_indicator_name(self):
        month = self.get_month(self.month)
        return f'{month} {int(self.year)}'

    def get_selection_label(self, object, field_name, field_value):
        return _(dict(self.env[object].fields_get(allfields=[field_name])[field_name]['selection'])[field_value])
