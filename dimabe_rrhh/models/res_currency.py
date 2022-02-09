from odoo import models, fields, api

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def amount_to_text(self, amount):
        res = super(ResCurrency, self).amount_to_text(amount)
        if amount > 1 and 'Peso' in res:
            res_formated = res.replace("Peso", "Pesos")
            return res_formated
        return res