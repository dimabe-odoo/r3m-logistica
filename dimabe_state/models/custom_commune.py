import json

from odoo import fields, models, api
from odoo.addons import decimal_precision as dp
import urllib3


class CustomCommune(models.Model):
    _name = 'custom.commune'
    _description = 'Comuna'

    name = fields.Char('Nombre')

    code = fields.Char("Codigo")

    province_id = fields.Many2one('custom.province', string='Provincia')

    region_id = fields.Many2one('custom.region', string='Region')

    geo_latitude = fields.Float('Latitud',digits=dp.get_precision('Geo Location'))

    geo_longitude = fields.Float('Longitud',digits=dp.get_precision('Geo Location'))

    def get_communes(self):
        url = 'https://apis.digital.gob.cl/dpa/comunas'
        http = urllib3.PoolManager()
        res = http.request('GET', url)
        try:
            res = json.loads(res.data.decode('utf-8'))
            for com in res:
                commune_id = self.env['custom.commune'].search([('code', '=', com['codigo'])])
                if not commune_id:
                    province_id = self.env['custom.province'].search([('code', '=', com['codigo_padre'])], limit=1)
                    self.env['custom.commune'].create({
                        'code': com['codigo'],
                        'name': com['nombre'],
                        'geo_latitude': com['lat'],
                        'geo_longitude': com['lng'],
                        'province_id': province_id.id,
                        'region_id': province_id.region_id.id
                    })
        except Exception as e:
            print(e)
