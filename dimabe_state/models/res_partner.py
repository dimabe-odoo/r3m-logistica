from odoo import fields, models, api
import urllib3
import requests


class ResPartner(models.Model):
    _inherit = 'res.partner'

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
        return super(ResPartner, self).create(values)

    def write(self, values):
        if 'commune_id' in values.keys():
            commune_id = self.env['custom.commune'].search([('id', '=', values['commune_id'])])
            if 'region_id' not in values.keys():
                values['region_id'] = commune_id.region_id.id
            if 'province_id' not in values.keys():
                values['province_id'] = commune_id.province_id.id

        return super(ResPartner, self).write(values)

    def geo_localize(self):
        address = f'{self.street}, {self.commune_id.name} {self.province_id.name} {self.region_id.name}'.replace(' ',
                                                                                                                 '+')
        api_key = self.env['ir.config_parameter'].search([('key', '=', 'base_geolocalize.google_map_api_key')]).value
        url = f'https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}'
        response = requests.get(url)
        result = response.json()
        latitude = result['results'][0]['geometry']['location']['lat']
        longitude = result['results'][0]['geometry']['location']['lng']
        self.write({
            'partner_latitude': latitude,
            'partner_longitude': longitude
        })