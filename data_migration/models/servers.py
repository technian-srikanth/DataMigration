import requests
import xmlrpc.client
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Servers(models.Model):
    _name = 'data.migrate.servers'
    _description = 'Data Migration Servers'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char()
    username = fields.Char()
    password = fields.Char()
    url = fields.Text(required=True, tracking=True)

    db_id = fields.Many2one(
        'data.migrate.database',
        string="Database",
        tracking=True
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
        if self.url:
            self.verify_server()

    @api.model
    def write(self, vals):
        res = super(Servers, self).write(vals)
        if 'url' in vals:
            self.verify_server()
        return res

    @api.onchange('db_id')
    def _onchange_db(self):
        for rec in self:
            rec.is_db = False

    def verify_server(self):
        """Helper method to validate connection to the URL"""
        for record in self:
            if not record.url:
                continue
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
                record.verified = False
                record.status = 'inactive'

    def action_fetch_databases(self):
        """Action button method to pull databases via XML-RPC"""
        for record in self:
            if not record.url:
                continue
            try:
                # Clean up URL trailing slashes if any
                base_url = record.url.strip().rstrip('/')
                db_service = xmlrpc.client.ServerProxy(f"{base_url}/xmlrpc/2/db")
                db_list = db_service.list()

                # Clear old fetched databases for this server
                self.env['data.migrate.database'].search([
                    ('server_id', '=', record.id)
                ]).unlink()

                # Create new database records
                for db in db_list:
                    self.env['data.migrate.database'].create({
                        'name': db,
                        'server_id': record.id
                    })

                # Corrected from 'self' to 'record'
                record.is_db = True

            except Exception as e:
                record.validation_response = str(e)


class DataMigrateDatabase(models.Model):
    _name = 'data.migrate.database'
    _description = 'Data Migration Databases'
    _rec_name = 'name'

    name = fields.Char(required=True)
    server_id = fields.Many2one('data.migrate.servers', required=True, ondelete='cascade')
