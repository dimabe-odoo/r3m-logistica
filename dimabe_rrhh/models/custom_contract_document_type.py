from odoo import models, fields

class CustomContractDocumenType(models.Model):
    _name = 'custom.contract.document.type'
    _description = "Tipo de Documento del Contrato"

    name = fields.Char('Nombre')