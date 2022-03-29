from odoo import models, fields

class CustomData(models.Model):
    _name = 'custom.data'
    _description = "Datos Previred"

    name = fields.Char('Nombre')

    value = fields.Float('Valor')

    code = fields.Char('Codigo')

    vat = fields.Char('Rut')

    data_type_id = fields.Many2one('custom.data.type','Tipo')

    show_vat = fields.Boolean('Visualizar Rut', compute="_compute_show_vat")

    def _compute_show_vat(self):
        for item in self:
            item.show_vat = False
            if item.data_type_id.id in [self.env.ref('dimabe_rrhh.custom_data_initial_ccaf').id, self.env.ref('dimabe_rrhh.custom_data_initial_mutuality').id]:
                item.show_vat = True
