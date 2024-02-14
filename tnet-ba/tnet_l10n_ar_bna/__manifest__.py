# -*- coding: utf-8 -*-

{
    'name': "Tecnicanet BNA Currencies",
    'version': '15.0.0',
    'description': """Sincronización de tasas de cambio con el sitio del Banco de la Nación Argentina""",
    'summary': "Sincronización de tasas de cambio con el sitio del Banco de la Nación Argentina",
    'author': 'Luis Trajtenberg',
    'website': 'https://www.tecnicanet.com',
    'category': "Accounting",
    'depends': ['base', 'account', 'currency_rate_live'],
    'data': [
        "data/bna_data.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/bna_menues_views.xml",
        "views/account_bna_currencies_views.xml",
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
}
