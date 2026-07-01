import requests
from odoo import models, fields, api
import xmlrpc.client


class Servers(models.Model):
    _name = 'data.migrate.servers'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    username = fields.Char()
    password = fields.Char()
    url = fields.Text(required=True, tracking=True)
    db_id = fields.Many2one(
        'data.migrate.database',
        string="Database",
        domain="[('server_id', '=', id)]", tracking=True
    )

    status = fields.Selection(
        [('active', 'Active'), ('inactive', 'Inactive')],
        default='inactive', tracking=True
    )
    verified = fields.Boolean('Is Verified')

    validation_response = fields.Text('Validation Message')

    is_db = fields.Boolean(default=False)

    @api.onchange('url')
    def _onchange_url(self):
        for rec in self:
            rec.verified = False
            rec.status = 'inactive'
            rec.is_db = False

    @api.onchange('db_id')
    def _onchange_db(self):
        for rec in self:
            rec.is_db = False

    @api.depends('url')
    def verify_server(self):
        for record in self:

            try:
                response = requests.get(record.url, timeout=5)

                record.validation_response = f"{response.status_code} - {response.reason}"

                if response.status_code == 200:
                    record.verified = True
                    record.status = 'active'
                else:
                    record.verified = False
                    record.status = 'inactive'

            except requests.exceptions.RequestException as e:
                record.validation_response = str(e)

    @api.depends('url')
    def action_fetch_databases(self):
        for record in self:
            try:
                db_service = xmlrpc.client.ServerProxy(f"{record.url}/xmlrpc/2/db")
                db_list = db_service.list()
                self.env['data.migrate.database'].search([
                    ('server_id', '=', record.id)
                ]).unlink()
                for db in db_list:
                    self.env['data.migrate.database'].create({
                        'name': db,
                        'server_id': record.id
                    })
                    self.is_db = True

            except Exception as e:
                record.validation_response = str(e)


class DataMigrateDatabase(models.Model):
    _name = 'data.migrate.database'
    _rec_name = 'name'

    name = fields.Char(required=True)
    server_id = fields.Many2one('data.migrate.servers', required=True)
