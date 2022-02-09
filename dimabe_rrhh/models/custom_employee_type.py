from odoo import models, fields

class CustomEmployeeType(models.Model):

    _name = 'custom.employee.type'

    name = fields.Char('Nombre')

    code = fields.Char('Código')