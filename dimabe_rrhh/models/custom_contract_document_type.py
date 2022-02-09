from odoo import models, fields

class CustomContractDocumenType(models.Model):
    _name = 'custom.contract.document.type'

    name = fields.Char('Nombre')