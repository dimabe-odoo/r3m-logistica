# -*- coding: utf-8 -*-
{
    'name': "dimabe_states",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # Data
        'data/ir_cron_cl.xml',
        # Views
        'views/custom_region.xml',
        'views/custom_commune.xml',
        'views/custom_province.xml',
        'views/res_partner.xml',
        'views/web_assets.xml',
        'views/res_company.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'qweb': [
        'static/src/xml/get_regions_button.xml'
    ]
}
