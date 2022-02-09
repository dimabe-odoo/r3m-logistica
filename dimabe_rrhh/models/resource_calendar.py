from odoo import models,fields,api

class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    full_days_on_month = fields.Integer('Máximo de Días/Mes', help="Cantidad máxima de días trabajados para la nómina")

    effective_days_on_month = fields.Integer('Días/Mes Efectivos', help="Cantidad máxima efectiva de días trabajados para la nómina")
