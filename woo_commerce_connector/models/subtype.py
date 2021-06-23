from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class SubType(models.Model):
    _name = 'product.subtype'
    _description = "Product attribute"
    _rec_name = 'subtype'

    subtype = fields.Char("Subtype", readonly=True)
    description = fields.Char("Description", readonly=True)
    slug = fields.Char("Slug", readonly=True)
    count = fields.Char("Count", readonly=True)
    woo_id = fields.Char(string="Woo ID", readonly=True)
    instance_id = fields.Many2one('woo.commerce', string="Instance", readonly=True)

    def unlink(self):
        """
        For deleting on both instances.
        """
        for recd in self:
            if recd.woo_id:
                wcapi = recd.instance_id.get_api()
                attributes = wcapi.get("products/attributes").json()
                subtype_woo_id = False
                for attrs in attributes:
                    if attrs.get('name') == 'Sub Type':
                        subtype_woo_id = attrs.get('id')
                wcapi.delete("products/attributes/" + str(subtype_woo_id) + "/terms/" + recd.woo_id, params={"force": True}).json()
        return super(SubType, self).unlink()

    @api.model
    def create(self, vals):
        """
         For creating on both instances.
        """
        res = super(SubType, self).create(vals)
        if 'woo_id' not in vals.keys() and not res.woo_id:
            _logger.info("subtype create funnnn")
            instance_id = self.instance_id.search([('active', '=', True)], limit=1)
            wcapi = instance_id.get_api()
            attributes = wcapi.get("products/attributes").json()
            subtype_woo_id = False
            for attrs in attributes:
                if attrs.get('name') == 'Sub Type':
                    subtype_woo_id = attrs.get('id')
            data = {
                "name": res.subtype,
            }
            attr_res = wcapi.post("products/attributes/" + str(subtype_woo_id) + "/terms", data).json()
            print("asDEDWD", attr_res)
            res.woo_id = str(attr_res.get('id'))
            res.instance_id = instance_id.id
        return res

    def write(self, vals):
        """
            For updating on both instances.
        """
        res = super(SubType, self).write(vals)
        instance_id = self.instance_id.search([('active', '=', True)], limit=1)
        wcapi = instance_id.get_api()
        subtype_woo_id = False
        attributes = wcapi.get("products/attributes").json()
        for attrs in attributes:
            if attrs.get('name') == 'Sub Type':
                subtype_woo_id = attrs.get('id')
        data = {
            "name": self.subtype,
        }
        attr_res = wcapi.put("products/attributes/" + str(subtype_woo_id) + "/terms/" + str(self.woo_id), data).json()
        print("dfwerfew", attr_res)
        return res
