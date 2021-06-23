from odoo import models, fields, api


class WooAttribute(models.Model):
    _name = 'woo.attribute'

    name = fields.Char("Name", readonly=True)
    woo_id = fields.Char(string="Woo ID", readonly=True)
    instance_id = fields.Many2one('woo.commerce', string="Instance", readonly=True)
    display_type = fields.Selection([
        ('radio', 'Radio'),
        ('select', 'Select'),
        ('color', 'Color')], default='radio', required=True, help="The display type used in the Product Configurator.")