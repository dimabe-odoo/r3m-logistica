from odoo import fields, models, api


class CustomFee(models.Model):
    _name = 'custom.fee'

    number = fields.Integer('Numero')

    value = fields.Monetary('Valor')

    paid = fields.Boolean('Pagado')

    currency_id = fields.Many2one('res.currency', string='Moneda',
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'CLP')]))

    expiration_date = fields.Date('Fecha de Vencimiento')

    loan_id = fields.Many2one('custom.loan')

    parent_state = fields.Char('Parent State', compute="_compute_parent_state")


    def _compute_parent_state(self):
        for item in self:
            item.parent_state = item.loan_id.state



