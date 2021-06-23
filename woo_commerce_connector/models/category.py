from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class WooCategory(models.Model):
    _name = 'woocommerce.category'
    _description = "Woocommerce Category"

    name = fields.Char("Category Name")
    parent_id = fields.Many2one('woocommerce.category', string="Parent Category")
    woo_id = fields.Char(string="Woo ID", readonly=True)
    instance_id = fields.Many2one('woo.commerce', string="Instance", readonly=True)

    def unlink(self):
        """
        For deleting on both instances.
        """
        for recd in self:
            if recd.woo_id:
                wcapi = recd.instance_id.get_api()
                wcapi.delete("products/categories/" + recd.woo_id, params={"force": True}).json()
        return super(WooCategory, self).unlink()

    @api.model
    def create(self, vals):
        """
         For creating on both instances.
        """
        res = super(WooCategory, self).create(vals)
        if 'woo_id' not in vals.keys() and not res.woo_id:
            _logger.info("categ create funnnnn")
            instance_id = self.instance_id.search([('active', '=', True)], limit=1)
            wcapi = instance_id.get_api()
            parent_id = False
            if vals.get('parent_id'):
                parent_id = self.env['woocommerce.category'].search([('id', '=', res.parent_id.id)])
            data = {
                "name": res.name,
                "parent": parent_id.woo_id if parent_id and parent_id.woo_id else 0
            }
            cat_res = wcapi.post("products/categories", data).json()
            print("asDEDWD", cat_res)
            res.woo_id = str(cat_res.get('id'))
            res.instance_id = instance_id.id
        return res

    def write(self,vals):
        """
         For updating on both instances.
        """
        print("fvsrssvggr", vals)
        res = super(WooCategory, self).write(vals)
        instance_id = self.instance_id.search([('active', '=', True)], limit=1)
        wcapi = instance_id.get_api()
        parent_id = False
        if self.parent_id:
            parent_id = self.env['woocommerce.category'].search([('id', '=', self.parent_id.id)])
        data = {
            "name": self.name,
            "parent": parent_id.woo_id if parent_id and parent_id.woo_id else 0
        }
        cat_res = wcapi.put("products/categories/" + str(self.woo_id), data).json()
        print("dfwerfew", cat_res)
        return res