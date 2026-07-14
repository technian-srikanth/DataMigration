{
    'name': 'Data Migration',
    'version': '19.0.0.1.3',
    'depends': ['base', 'mail','contacts', 'stock', 'sale', 'account', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/view_data_migrate_servers.xml',
        'views/view_data_migrate.xml',
        'views/menus.xml'
    ]
}
