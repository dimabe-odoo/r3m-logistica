from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    commune_id = fields.Many2one('custom.commune', string='Comuna')

    region_id = fields.Many2one('custom.region', string='Region')

    province_id = fields.Many2one('custom.province', string='Provincia')

    @api.onchange('commune_id')
    def onchange_commune_id(self):
        self.region_id = self.commune_id.region_id
        self.province_id = self.commune_id.province_id
        if not self.country_id:
            self.country_id = self.commune_id.region_id.country_id
        self.city = self.commune_id.name

    @api.model
    def create(self, values):
        if 'commune_id' in values.keys():
            commune_id = self.env['custom.commune'].search([('id', '=', values['commune_id'])])
            if 'region_id' not in values.keys():
                values['region_id'] = commune_id.region_id.id
            if 'province_id' not in values.keys():
                values['province_id'] = commune_id.province_id.id
        return super(ResCompany, self).create(values)

    def write(self, values):
        if 'commune_id' in values.keys():
            commune_id = self.env['custom.commune'].search([('id', '=', values['commune_id'])])
            if 'region_id' not in values.keys():
                values['region_id'] = commune_id.region_id.id
            if 'province_id' not in values.keys():
                values['province_id'] = commune_id.province_id.id
            self.partner_id.write({
                'commune_id': values['commune_id'],
                'region_id': values['region_id'],
                'province_id': values['province_id']
            })
        return super(ResCompany, self).write(values)
