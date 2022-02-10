import json

from gevent.resolver.cares import result
from odoo import fields, models, api
import requests
import urllib3
from odoo.addons import decimal_precision as dp


class CustomRegion(models.Model):
    _name = 'custom.region'
    _description = 'Region'

    name = fields.Char('Nombre')

    code = fields.Char('Codigo')

    country_id = fields.Many2one('res.country',
                                 default=lambda self: self.env['res.country'].search([('code', '=', 'CL')]))

    geo_latitude = fields.Float('Latitud', digits=dp.get_precision('Geo Location'))

    geo_longitude = fields.Float('Longitud', digits=dp.get_precision('Geo Location'))

    def get_regions(self):
        url = 'https://apis.digital.gob.cl/dpa/regiones'
        http = urllib3.PoolManager()
        res = http.request('GET', url)
        try:
            res = json.loads(res.data.decode('utf8'))
            for reg in res:
                region_id = self.env['custom.region'].search([('code', '=', reg['codigo'])])
                if not region_id:
                    self.env['custom.region'].create({
                        'code': reg['codigo'],
                        'name': reg['nombre'],
                        'geo_latitude': reg['lat'],
                        'geo_longitude': reg['lng']
                    })
        except Exception as e:
            print(e)
