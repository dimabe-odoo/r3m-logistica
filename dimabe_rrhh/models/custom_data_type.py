from odoo import models, fields 


class CustomDataType(models.Model):
    _name = 'custom.data.type'

    name = fields.Char('Nombre')
