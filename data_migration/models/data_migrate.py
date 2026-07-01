from odoo import fields, api, models
import xmlrpc.client
import logging
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class DataMigrateUniqueField(models.Model):
    _name = 'data.migrate.unique.field'
    _description = 'Unique Field Mapping'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Integer('')
    config_id = fields.Many2one(
        'data.migrate',
        string="Migration Config",
        required=True,
        ondelete='cascade'
    )

    target_field_id = fields.Many2one(
        'ir.model.fields',
        string="Target Field",
        required=True,
        domain="[('model_id', '=', parent.select_model_server_02)]",
        ondelete='cascade',
    )

    source_field_id = fields.Many2one(
        'data.migrate.model.fields',
        string="Source Field",
        required=True,
        domain="[('model_id', '=', parent.select_model_server_01)]",
        ondelete='cascade',
    )


class DataMigrate(models.Model):
    _name = 'data.migrate'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    sequence = fields.Integer('')

    server_01 = fields.Many2one(
        "data.migrate.servers",
        domain=[('verified', '!=', False), ('status', '=', 'active')],
        string="Server 01",
        tracking=True
    )

    server_02 = fields.Char(
        string="Server 02",
        compute="_compute_server_02",
        readonly=True,
        tracking=True
    )

    select_model_server_01 = fields.Many2one('data.migrate.model', tracking=True)

    is_model = fields.Boolean(default=False, tracking=True)

    line_ids = fields.One2many('data.migrate.line', 'migrate_id', string="Lines")

    select_model_server_02 = fields.Many2one('ir.model')

    unique_field_ids = fields.One2many(
        'data.migrate.unique.field',
        'config_id',
        string="Unique Fields"
    )

    @api.model
    def write(self, vals):
        if 'server_01' in vals and not vals.get('server_01'):
            vals.update({
                'select_model_server_01': False,
                'select_model_server_02': False,
                'is_model': False,
            })

        return super(DataMigrate, self).write(vals)

    @api.onchange('server_01')
    def _onchange_server_01(self):
        if self.server_01:
            return {'domain': {'select_model_server_01': [('db_id', '=', self.server_01.db_id)]}}
        if not self.server_01:
            self.select_model_server_01 = False
            self.select_model_server_02 = False
            self.is_model = False
        return {'domain': {'select_model_server_01': []}}

    def _compute_server_02(self):
        config = self.env['ir.config_parameter'].sudo()
        base_url = config.get_param('web.base.url')
        for record in self:
            record.server_02 = base_url

    def get_remote_models(self):
        self.ensure_one()

        server = self.server_01

        if not server:
            raise ValidationError("plz select a server")

        common = xmlrpc.client.ServerProxy(f"{server.url}/xmlrpc/2/common")
        uid = common.authenticate(
            server.db_id.name,
            server.username,
            server.password,
            {}
        )

        if not uid:
            return False

        models_proxy = xmlrpc.client.ServerProxy(f"{server.url}/xmlrpc/2/object")

        model_list = models_proxy.execute_kw(
            server.db_id.name,
            uid,
            server.password,
            'ir.model',
            'search_read',
            [[]],
            {'fields': ['model', 'name']}
        )

        model_obj = self.env['data.migrate.model']

        created_ids = []

        for rec in model_list:
            existing = model_obj.search([
                ('model', '=', rec['model']),
                ('db_id', '=', server.db_id.id),
                ('server_id', '=', server.id)
            ], limit=1)

            if existing:
                existing.write({
                    'name': rec['name'],
                    'model': rec['model'],
                })
                created_ids.append(existing.id)

            else:
                new_rec = model_obj.create({
                    'name': rec['name'],
                    'model': rec['model'],
                    'db_id': server.db_id.id,
                    'server_id': server.id,
                })
                created_ids.append(new_rec.id)

            self.is_model = True

        return created_ids

    def get_remote_fields(self):
        self.ensure_one()

        server = self.server_01

        if not self.select_model_server_01:
            return False

        common = xmlrpc.client.ServerProxy(f"{server.url}/xmlrpc/2/common")
        uid = common.authenticate(
            server.db_id.name,
            server.username,
            server.password,
            {}
        )

        if not uid:
            return False

        models_proxy = xmlrpc.client.ServerProxy(f"{server.url}/xmlrpc/2/object")

        model_name = self.select_model_server_01.model

        field_list = models_proxy.execute_kw(
            server.db_id.name,
            uid,
            server.password,
            'ir.model.fields',
            'search_read',
            [[('model', '=', model_name)]],
            {
                'fields': ['name', 'model', 'ttype']
            }
        )

        field_obj = self.env['data.migrate.model.fields']

        created_ids = []

        for rec in field_list:

            existing = field_obj.search([
                ('field', '=', rec['name']),
                ('model_id', '=', self.select_model_server_01.id),
            ], limit=1)

            vals = {
                'name': rec['name'],
                'field': rec['name'],
                'model_id': self.select_model_server_01.id,
                'db_id': server.db_id.id,
                'server_id': server.id,
            }

            if existing:
                existing.write(vals)
                created_ids.append(existing.id)
            else:
                new_rec = field_obj.create(vals)
                created_ids.append(new_rec.id)

        return created_ids

    def _fetch_remote_records(self):
        server = self.server_01

        common = xmlrpc.client.ServerProxy(
            f"{server.url}/xmlrpc/2/common"
        )

        uid = common.authenticate(
            server.db_id.name,
            server.username,
            server.password,
            {}
        )

        models_proxy = xmlrpc.client.ServerProxy(
            f"{server.url}/xmlrpc/2/object"
        )

        field_map = {
            line.field_server_01.field: line.field_server_02.name
            for line in self.line_ids
            if line.field_server_01 and line.field_server_02
        }

        source_fields = list(field_map.keys())
        if 'id' not in source_fields:
            source_fields.append('id')

        return models_proxy.execute_kw(
            server.db_id.name,
            uid,
            server.password,
            self.select_model_server_01.model,
            'search_read',
            [[]],
            {'fields': source_fields,
             'context': {'active_test': False},
             }
        )

    def _prepare_vals(self, rec, target_obj):
        field_map = {
            line.field_server_01.field: line.field_server_02.name
            for line in self.line_ids
            if line.field_server_01 and line.field_server_02
        }

        # company_ids = self.env['res.company'].sudo().search([]).ids
        # ctx = {
        #     'active_test': False,
        #     'allowed_company_ids': company_ids,
        # }

        vals = {}
        for src_field, target_field in field_map.items():

            if target_field not in target_obj._fields:
                continue

            value = rec.get(src_field)
            field_obj = target_obj._fields[target_field]
            field_type = field_obj.type

            if field_type == 'many2one':

                if value:
                    relation_id = value[0]
                    related_model = field_obj.comodel_name
                    related_obj = self.env[related_model].sudo()

                    # related = related_obj.search(
                    #     [('migrate_id', '=', relation_id)],
                    #     limit=1
                    # )

                    related = related_obj.with_context(active_test=False).search(
                        [('migrate_id', '=', relation_id)],
                        limit=1
                    )

                    if not related:
                        if field_obj.required:
                            raise ValidationError(
                                f"Missing mapping for required field '{target_field}' "
                                f"(Model={related_model}, Source ID={relation_id})"
                            )
                        continue

                    vals[target_field] = related.id

                else:
                    if field_obj.required:
                        continue
                    vals[target_field] = False

            elif field_type == 'many2many':

                if value:
                    related_model = field_obj.comodel_name

                    related_obj = self.env[related_model].sudo()
                    # .with_context(ctx)

                    target_ids = []

                    for source_id in value:
                        related = related_obj.search(
                            [('migrate_id', '=', source_id)],
                            limit=1
                        )

                        if related:
                            target_ids.append(related.id)
                        else:
                            _logger.warning(
                                "Missing Many2many mapping: Model=%s migrate_id=%s",
                                related_model,
                                source_id
                            )

                    vals[target_field] = [(6, 0, target_ids)]

                else:
                    vals[target_field] = [(6, 0, [])]

            else:
                vals[target_field] = value

        vals['migrate_id'] = rec.get('id')

        return vals

    def migrate_create_only(self):
        self.ensure_one()

        target_model = self.select_model_server_02.model
        target_obj = self.env[target_model].sudo()

        records = self._fetch_remote_records()
        created = 0
        skipped = 0

        if not self.unique_field_ids:
            raise ValidationError("Please configure at least one unique field.")

        for rec in records:
            existing = False
            domain = []

            for line in self.unique_field_ids:
                target_field = line.target_field_id.name
                source_field = line.source_field_id.field

                value = rec.get(source_field)
                if isinstance(value, str):
                    value = value.strip()

                if value not in (False, None, ''):
                    domain.append((target_field, '=', value))

            if domain:
                existing = target_obj.with_context(active_test=False).search(domain, limit=1)

            if not existing:
                migrate_id = rec.get('id')
                if migrate_id:
                    existing = target_obj.with_context(active_test=False).search(
                        [('migrate_id', '=', migrate_id)],
                        limit=1
                    )

            if existing:
                skipped += 1
                continue

            vals = self._prepare_vals(rec, target_obj)

            if not vals:
                skipped += 1
                continue
            try:
                target_obj.create(vals)
                created += 1
            except Exception:
                self.env.cr.rollback()
                skipped += 1
                continue

        _logger.info(
            "Migration Completed | Model: %s | Created: %s | Skipped: %s | Total: %s",
            target_model,
            created,
            skipped,
            len(records)
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Migration Completed',
                'message': f"created: {created}, Skipped: {skipped}, Total: {len(records)}",
                'type': 'success',
            }
        }

    def migrate_update_only(self):
        self.ensure_one()

        target_model = self.select_model_server_02.model
        target_obj = self.env[target_model].sudo()
        records = self._fetch_remote_records()

        updated = 0
        skipped = 0

        if not self.unique_field_ids:
            raise ValidationError("Please configure at least one unique field.")

        for rec in records:
            existing = False
            domain = []

            for line in self.unique_field_ids:
                target_field = line.target_field_id.name
                source_field = line.source_field_id.field

                value = rec.get(source_field)

                if isinstance(value, str):
                    value = value.strip()

                if value not in (False, None, ''):
                    domain.append((target_field, '=', value))

            if domain:
                existing = target_obj.with_context(active_test=False).search(domain, limit=1)

            if not existing:
                migrate_id = rec.get('id')
                if migrate_id:
                    existing = target_obj.with_context(active_test=False).search(
                        [('migrate_id', '=', migrate_id)],
                        limit=1
                    )

            if not existing:
                skipped += 1
                continue

            vals = self._prepare_vals(rec, target_obj)

            if not vals:
                skipped += 1
                continue

            try:
                existing.write(vals)
                updated += 1
            except Exception:
                self.env.cr.rollback()
                skipped += 1
                continue

        _logger.info(
            "Migration Completed | Model: %s | Updated: %s | Skipped: %s | Total: %s",
            target_model,
            updated,
            skipped,
            len(records)
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Migration Completed',
                'message': f"Updated: {updated}, Skipped: {skipped}, Total: {len(records)}",
                'type': 'success',
            }
        }


class DataMigrateLine(models.Model):
    _name = 'data.migrate.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Integer('')
    migrate_id = fields.Many2one('data.migrate')
    field_server_01 = fields.Many2one(
        'data.migrate.model.fields',
        domain="[('model_id', '=', parent.select_model_server_01)]"
    )

    field_server_02 = fields.Many2one(
        'ir.model.fields',
        domain="[('model_id', '=', parent.select_model_server_02)]"
    )


class DataMigrateModel(models.Model):
    _name = 'data.migrate.model'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Technical Name", required=True)
    model = fields.Char('')
    server_id = fields.Many2one('data.migrate.servers')
    db_id = fields.Many2one('data.migrate.database', required=True)


class DataMigrateModelFields(models.Model):
    _name = 'data.migrate.model.fields'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Technical Name")
    field = fields.Char('')
    model_id = fields.Many2one('data.migrate.model')
    server_id = fields.Many2one('data.migrate.servers')
    db_id = fields.Many2one('data.migrate.database')
