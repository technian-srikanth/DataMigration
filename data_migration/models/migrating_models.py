from odoo import fields, models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    migrate_id = fields.Integer(index=True)
    xml_id = fields.Char(index=True)


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    migrate_id = fields.Integer('')


class ResCountry(models.Model):
    _inherit = 'res.country'

    migrate_id = fields.Integer('')


class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    migrate_id = fields.Integer('')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    migrate_id = fields.Integer('')


class ResCompany(models.Model):
    _inherit = 'res.company'

    migrate_id = fields.Integer('')


class ResUser(models.Model):
    _inherit = 'res.users'

    migrate_id = fields.Integer('')


class StockRule(models.Model):
    _inherit = 'stock.rule'

    migrate_id = fields.Integer('')


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    migrate_id = fields.Integer('')


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    migrate_id = fields.Integer('')


class StockRoute(models.Model):
    _inherit = 'stock.route'

    migrate_id = fields.Integer('')


class StockLocation(models.Model):
    _inherit = 'stock.location'

    migrate_id = fields.Integer('')


class StoreStorageCategory(models.Model):
    _inherit = 'stock.storage.category'

    migrate_id = fields.Integer('')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    migrate_id = fields.Integer('')


class Product(models.Model):
    _inherit = 'product.product'

    migrate_id = fields.Integer('')


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    migrate_id = fields.Integer('')


class AccountTax(models.Model):
    _inherit = 'account.tax'

    migrate_id = fields.Integer('')


class AccountAccount(models.Model):
    _inherit = 'account.account'

    migrate_id = fields.Integer('')


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    migrate_id = fields.Integer('')


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    migrate_id = fields.Integer('')


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    migrate_id = fields.Integer('')


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    migrate_id = fields.Integer('')


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    migrate_id = fields.Integer('')
