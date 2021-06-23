from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class WooBrand(models.Model):
    _name = 'product.brand'
    _rec_name = 'brand'

    brand = fields.Char("Brands")
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
                brand_woo_id = False
                for attrs in attributes:
                    if attrs.get('name') == 'Brand':
                        brand_woo_id = attrs.get('id')
                wcapi.delete("products/attributes/" + str(brand_woo_id) + "/terms/" + recd.woo_id, params={"force": True}).json()
        return super(WooBrand, self).unlink()

    @api.model
    def create(self, vals):
        """
         For creating on both instances.
        """
        res = super(WooBrand, self).create(vals)
        print("awefdrewferf", self.woo_id)
        if 'woo_id' not in vals.keys() and not res.woo_id:
            _logger.info("brand create funnnn")
            instance_id = self.instance_id.search([('active', '=', True)], limit=1)
            wcapi = instance_id.get_api()
            attributes = wcapi.get("products/attributes").json()
            brand_woo_id = False
            for attrs in attributes:
                if attrs.get('name') == 'Brand':
                    brand_woo_id = attrs.get('id')
            data = {
                "name": res.brand,
            }
            attr_res = wcapi.post("products/attributes/" + str(brand_woo_id) + "/terms", data).json()
            print("asDEDWD", attr_res)
            res.woo_id = str(attr_res.get('id'))
            res.instance_id = instance_id.id
        return res

    def write(self, vals):
        """
            For updating on both instances.
        """
        res = super(WooBrand, self).write(vals)
        instance_id = self.instance_id.search([('active', '=', True)], limit=1)
        wcapi = instance_id.get_api()
        attributes = wcapi.get("products/attributes").json()
        brand_woo_id = False
        for attrs in attributes:
            if attrs.get('name') == 'Brand':
                brand_woo_id = attrs.get('id')
        data = {
            "name": self.brand,
        }
        attr_res = wcapi.put("products/attributes/" + str(brand_woo_id) + "/terms/" + str(self.woo_id), data).json()
        print("dfwerfew", attr_res)
        return res

