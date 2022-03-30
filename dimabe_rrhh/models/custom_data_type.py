from odoo import models, fields 


class CustomDataType(models.Model):
    _name = 'custom.data.type'
    _description = "Tipo de Datos de Previred"

    name = fields.Char('Nombre')
