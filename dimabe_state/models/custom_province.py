import json

from odoo import fields, models, api
import urllib3
from odoo.addons import decimal_precision as dp


class CustomProvince(models.Model):
    _name = 'custom.province'
    _description = 'Provincia'

    name = fields.Char('Nombre')

    code = fields.Char('Codigo')

    geo_latitude = fields.Float('Latitud', digits=dp.get_precision('Geo Location'))

    geo_longitude = fields.Float('Longitud', digits=dp.get_precision('Geo Location'))

    region_id = fields.Many2one('custom.region', string='Region')

    def get_provinces(self):
        url = 'https://apis.digital.gob.cl/dpa/provincias'
        http = urllib3.PoolManager()
        res = http.request('GET', url)
        try:
            res = json.loads(res.data.decode('utf-8'))
            for pro in res:
                province_id = self.env['custom.province'].search([('code', '=', pro['codigo'])])
                if not province_id:
                    self.env['custom.province'].create({
                        'code': pro['codigo'],
                        'name': pro['nombre'],
                        'geo_longitude': pro['lng'],
                        'geo_latitude': pro['lat'],
                        'region_id': self.env['custom.region'].search([('code', '=', pro['codigo_padre'])], limit=1).id
                    })
        except Exception as e:
            print(e)
