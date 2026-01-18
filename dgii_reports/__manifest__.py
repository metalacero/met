# -*- coding: utf-8 -*-
{
    'name': 'DGII Reports (606 & 607)',
    'version': '16.0.1.0.0',
    'summary': 'Reportes 606 y 607 de DGII para República Dominicana',
    'description': """
        Módulo para generar los reportes 606 (Compras) y 607 (Ventas)
        requeridos por la Dirección General de Impuestos Internos (DGII)
        de República Dominicana.
    """,
    'author': 'Tu Empresa',
    'website': '',
    'category': 'Localization/Accounting',
    'depends': [
        'base',
        'account',
        'l10n_do_accounting',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/dgii_report_line_views.xml',
        'views/dgii_report_views.xml',
        'wizard/dgii_report_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

