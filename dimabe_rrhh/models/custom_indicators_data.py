from odoo import models, fields


class CustomIndicators(models.Model):
    _name = 'custom.indicators.data'

    name = fields.Char('Nombre')

    value = fields.Float('Valor Calculo')

    value_show = fields.Char('Valor')

    percentage_show = fields.Char('Porcentaje')

    percentage_value = fields.Float('Valor Porcentaje')

    type = fields.Selection(
        [('1', 'UF'), ('2', 'UTM'), ('3', 'UTA'), ('4', 'Topes'), ('5', 'Renta Minima Imponible'), ('6', 'APV'),
         ('7', 'Deposito Convenido'), ('8', 'AFC'), ('9', 'AFP'),('10','Asignación Familiar')],string='Tipo')

    last_month = fields.Boolean('Ultimo Mes')

    indicator_id = fields.Many2one('custom.indicators','Indicador')

