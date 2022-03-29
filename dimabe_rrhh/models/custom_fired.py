from odoo import models, fields


class CustomFired(models.Model):
    _name = 'custom.fired'
    _rec_name = 'display_name'
    _description = "Causal de Despido"

    name = fields.Char('Nombre', required=True)

    description = fields.Text('Descripcion', required=True)

    article = fields.Selection(
        [('159', 'Artículo 159'), ('160', 'Artículo 160'), ('161', 'Artículo 161'), (('163', 'Artículo 163'))],
        string="Artículo")

    display_name = fields.Char('Referencia', compute="_compute_display_name")

    sequence = fields.Integer('Secuencia', required=True)

    def _compute_display_name(self):
        for item in self:
            item.display_name = f'[{item.article}-{str(item.sequence)}] - {item.name}'
