# -*- coding: utf-8 -*-
import requests
from odoo import models, fields, api, _
import logging
import base64
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    def write(self, vals_list):
        res = super(StockQuantInherit, self).write(vals_list)
        if 'inventory_quantity' in vals_list.keys():
            instance_id = self.product_tmpl_id.instance_id
            if instance_id:
                woo_id = self.product_id.woo_var_id
                tmpl_woo_id = self.product_tmpl_id.woo_id
                wcapi = instance_id.get_api()
                if self.location_id == instance_id.location_id:
                    stock = vals_list['inventory_quantity']
                    data = {
                        'manage_stock': True,
                        'stock_quantity': stock
                    }
                    wcapi.put("products/" + tmpl_woo_id + "/variations/" + woo_id, data)
        return res


class ProductTemplateAttributeLineInherit(models.Model):
    _inherit = "product.template.attribute.line"

    default_id = fields.Many2one('product.attribute.value',
                                  domain="[('id', 'in', value_ids)]",
                                  string="Default Value")
    attribute_id = fields.Many2one('product.attribute', domain="[('woo_id', '!=', False)]", string="Attribute",
                                   ondelete='restrict', required=True,
                                   index=True)


class ProductTemplateInherited(models.Model):
    _inherit = 'product.template'
    woo_id = fields.Char(string="Woo ID", copy=False, readonly=True)
    webhook = fields.Boolean(string="Webhook", readonly=True, default=False)
    instance_id = fields.Many2one('woo.commerce', string="Instance", readonly=True)
    woo_variant_check = fields.Boolean(readonly=True)
    type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'), ('product', 'Storable')], string='Product Type', default='product', required=True,
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A consumable product is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.')
    woo_publish = fields.Boolean(string="Woo Publish", readonly=True, default=False,
                                 help='To publish or unpublish in woocommerce')
    woo_categ_ids = fields.Many2many('woocommerce.category', 'product_woo_cat', 'woo_id', string="Woocommerce Category")
    brand_ids = fields.Many2many('product.brand', string="Brand")
    sub_ids = fields.Many2many('product.subtype', string="Subtype")
    tlc_ids = fields.Many2many('product.tlc', string="TLC")
    location_id = fields.Many2one('stock.location', string="Warehouse", related='instance_id.location_id')
    veg = fields.Selection([('yes', "Yes"), ('no', "No")], string="Veg")
    list_price = fields.Float(
        'Sales Price', default=0.0,
        digits='Product Price', invisible=True,
        help="Price at which the product is sold to customers.")

    def image_upload(self, image):
        """
        Uploads image into imgur API for getting product image in the woo.
        """

        url = "https://api.imgur.com/3/image"

        payload = {'image': image}
        files = [

        ]
        headers = {
            'Authorization': 'Client-ID 3a0493870db422c'
        }

        response = requests.request("POST", url, headers=headers, data=payload, files=files)

        result = response.json()

        data = result['data']
        if 'link' in data:
            link = data['link']
            return link
        else:
            raise ValidationError(_(data['error']['message']))

    def unlink(self):
        """
        For deleting on both instances.
        """
        for recd in self:
            if recd.woo_id:
                wcapi = recd.instance_id.get_api()
                wcapi.delete("products/" + recd.woo_id + "", params={"force": True}).json()
        return super(ProductTemplateInherited, self).unlink()

    @api.model
    def create(self, vals_list):
        """
         For creating on both instances.
        """
        res = super(ProductTemplateInherited, self).create(vals_list)
        print("adasde", vals_list, res)
        if not res.woo_id:
            instance_id = self.instance_id.search([('active', '=', True)], limit=1)
            wcapi = instance_id.get_api()
            images = []
            attributes = wcapi.get("products/attributes").json()
            brand_woo_id = False
            subtype_woo_id = False
            tlc_woo_id = False
            veg_woo_id = False
            qty_woo_id = False
            for attrs in attributes:
                if attrs.get('name') == 'Brand':
                    brand_woo_id = attrs.get('id')
                if attrs.get('name') == 'Sub Type':
                    subtype_woo_id = attrs.get('id')
                if attrs.get('name') == 'veg':
                    veg_woo_id = attrs.get('id')
                if attrs.get('name') == 'TLC':
                    tlc_woo_id = attrs.get('id')
                if attrs.get('name') == 'Qty':
                    qty_woo_id = attrs.get('id')
            category_ids = self.env['woocommerce.category'].search([('woo_id', '=', False)])

            for recd in category_ids:
                if not recd.parent_id:
                    data = {
                        "name": recd.name,
                    }
                    cat_res = wcapi.post("products/categories", data).json()
                    recd.woo_id = cat_res.get('id')
                    recd.instance_id = instance_id.id

            for recd in category_ids:
                if recd.parent_id:
                    parent_id = self.env['woocommerce.category'].search([('id', '=', recd.parent_id.id)])
                    data = {
                        "name": recd.name,
                        "parent": parent_id.woo_id
                    }
                    cat_res = wcapi.post("products/categories", data).json()
                    recd.woo_id = cat_res.get('id')
                    recd.instance_id = instance_id.id

            cat_woo_ids = res.woo_categ_ids.mapped('woo_id')
            cat_list = []
            att_id = []
            for i in range(len(cat_woo_ids)):
                data = {
                    'id': cat_woo_ids[i]
                }
                cat_list.append(data)
            for att in res.attribute_line_ids:
                var_info = []
                for var in att.value_ids:
                    var_info.append(var.name)
                att_data = {
                    'id': att.attribute_id.woo_id,
                    'visible': False,
                    'variation': True,
                    'options': var_info
                }
                att_id.append(att_data)
            if res.brand_ids and brand_woo_id:
                brand_ids = res.brand_ids.browse(res.brand_ids.ids)
                brand_opt = brand_ids.mapped('brand')
                att_data = {
                    'id': brand_woo_id,
                    'visible': True,
                    'variation': False,
                    'options': brand_opt
                }
                att_id.append(att_data)
            if res.tlc_ids and tlc_woo_id:
                tlc_ids = res.tlc_ids.browse(res.tlc_ids.ids)
                tlc_opt = tlc_ids.mapped('name')
                att_data = {
                    'id': tlc_woo_id,
                    'visible': True,
                    'variation': False,
                    'options': tlc_opt
                }
                att_id.append(att_data)
            if res.sub_ids and subtype_woo_id:
                sub_ids = res.sub_ids.browse(res.sub_ids.ids)
                sub_opt = sub_ids.mapped('subtype')
                att_data = {
                    'id': subtype_woo_id,
                    'visible': True,
                    'variation': False,
                    'options': sub_opt
                }
                att_id.append(att_data)
            if res.veg and veg_woo_id:
                veg = 'Yes' if res.veg == 'Yes' else 'No'
                att_data = {
                    'id': veg_woo_id,
                    'visible': True,
                    'variation': False,
                    'options': veg
                }
                att_id.append(att_data)
            if res.image_1920:
                image = base64.decodebytes(res.image_1920)
                image_url = self.image_upload(image)
                images = [{
                    'src': image_url
                }]
            attr_id = self.env['product.attribute'].search([('name', '=', "Qty"), ('woo_id', '!=', False)], limit=1)
            _logger.info("fdgdfffd %s", attr_id)
            print("fdgdfffdsdfSEFWEFEEF", attr_id)
            attr_line = res.attribute_line_ids.filtered(lambda a: a.attribute_id == attr_id)
            print("fsdffdserwr", attr_line)
            _logger.info("fsdffdserwr %s", attr_line)
            _logger.info("fsdffdseasdseadedrwr %s", attr_line.default_id)
            _logger.info("asdsadsaddsadddddddd %s", attr_line.default_id.name)
            print("asdsadsaddasdasadddddddd", attr_line.default_id)
            print("asdsadsaddsadddddddd", attr_line.default_id.name)
            data = {
                "default_attributes": [
                    {
                        "id": qty_woo_id,
                        "name": "Qty",
                        "option": attr_line.default_id.name if attr_line.default_id else ""
                    }
                ],
                "name": res.name,
                "type": "variable",
                "status": 'private',
                "regular_price": str(res.list_price),
                "sale_price": str(res.standard_price),
                "description": res.description if res.description else "",
                "images": images,
                "categories": cat_list,
                "attributes": att_id,
            }
            print("sdcasdca", data)
            _logger.info("sdcasdcalklk %s", data)
            x = wcapi.post("products", data).json()
            print("dtrdcfctfrd", x)
            res.woo_id = x.get('id')
            print(res.product_variant_ids, "sdnjfsdfn")
            for var_id in res.product_variant_ids:
                prd_opt = var_id.product_template_attribute_value_ids.mapped('name')
                reg_price = var_id.regular_price
                data = {
                    "regular_price": str(reg_price),
                    "attributes": [
                        {
                            "id": qty_woo_id,
                            "option": prd_opt[0] if prd_opt else ""
                        }
                    ]
                }
                y = wcapi.post("products/" + str(x.get('id')) + "/variations", data).json()
                print("fcaerferferfe", y)
                _logger.info("fcaerferferfe %s", y)
                var_id.woo_var_id = y.get('id')
                res.woo_variant_check = True
            res.instance_id = instance_id.id
        return res

    def write(self, vals_list):
        """
        For updating on both instances.
        """

        print("aewfwefrfrf", vals_list)
        _logger.info("vals list product template %s", vals_list)
        _logger.info("contextttt %s", self._context.get('webhook'))
        for rec in self:
            if rec.instance_id and rec.woo_id and not self._context.get('webhook'):
                print("dsdfdsf", rec.instance_id)
                # webhook = False
                # if 'webhook' in vals_list.keys():
                #     webhook = vals_list['webhook']
                _logger.info("template  funnnn ")
                wcapi = rec.instance_id.get_api()
                attributes = wcapi.get("products/attributes").json()
                brand_woo_id = False
                subtype_woo_id = False
                tlc_woo_id = False
                veg_woo_id = False
                qty_woo_id = False
                for attrs in attributes:
                    if attrs.get('name') == 'Brand':
                        brand_woo_id = attrs.get('id')
                    if attrs.get('name') == 'Sub Type':
                        subtype_woo_id = attrs.get('id')
                    if attrs.get('name') == 'veg':
                        veg_woo_id = attrs.get('id')
                    if attrs.get('name') == 'TLC':
                        tlc_woo_id = attrs.get('id')
                    if attrs.get('name') == 'Qty':
                        qty_woo_id = attrs.get('id')

                data = {}
                flag = False
                if 'name' in vals_list.keys():
                    flag = True
                    name = vals_list['name']
                    data.update(
                        {
                            'name': name
                        }
                    )
                if 'lst_price' in vals_list.keys():
                    flag = True
                    sales_price = vals_list['lst_price']
                    data.update(
                        {
                            'sale_price': str(sales_price)
                        }
                    )
                if 'regular_price' in vals_list.keys():
                    flag = True
                    reg_price = vals_list['regular_price']
                    data.update(
                        {
                            'regular_price': str(reg_price)
                        }
                    )
                if 'description' in vals_list.keys():
                    flag = True
                    desc = vals_list['description']
                    data.update(
                        {
                            'description': desc
                        }
                    )
                if 'image_1920' in vals_list.keys():
                    flag = True
                    desc = vals_list['image_1920']
                    if desc:
                        data_bytes = desc.encode("utf-8")
                        image = base64.decodebytes(data_bytes)
                        img_url = self.image_upload(image)
                        images = [{
                            'src': img_url
                        }]
                    else:
                        images = []
                    data.update(
                        {
                            'images': images
                        }
                    )

                if 'woo_categ_ids' in vals_list.keys():

                    flag = True

                    cat_id = vals_list['woo_categ_ids'][0][2]
                    cat_ids = self.env['woocommerce.category'].browse(cat_id)

                    cat_list = []
                    for cat in cat_ids:
                        cat_data = {
                            'id': cat.woo_id
                        }
                        cat_list.append(cat_data)
                    data.update({
                        "categories": cat_list
                    })
                elif self.woo_categ_ids:
                    flag = True
                    cat_id = self.woo_categ_ids
                    print("scadsdf", cat_id)
                    cat_ids = self.env['woocommerce.category'].browse(cat_id).ids
                    cat_list = []
                    for cat in cat_ids:
                        cat_data = {
                            'id': cat.woo_id
                        }
                        cat_list.append(cat_data)
                    data.update({
                        "categories": cat_list
                    })
                attr_flag = False
                att_list = []
                default_list = []
                veg_flag = False
                if 'veg' in vals_list.keys() and veg_woo_id:

                    veg_flag = True
                    flag = True
                    attr_flag = True
                    print("aderfsareafe", vals_list['veg'])
                    veg = vals_list['veg'] if vals_list['veg'] else ""
                    attr_data = {
                        'id': veg_woo_id,
                        'visible': True,
                        'variation': False,
                        'options': veg
                    }
                    att_list.append(attr_data)
                elif self.veg and veg_woo_id:
                    veg_flag = True
                    flag = True
                    attr_flag = True
                    veg = self.veg if self.veg else ""
                    print("aderfsareafe", self.veg)
                    attr_data = {
                        'id': veg_woo_id,
                        'visible': True,
                        'variation': False,
                        'options': veg
                    }
                    att_list.append(attr_data)

                # if 'sub_ids' in vals_list.keys() and 'brand_ids' in vals_list.keys() and 'tlc_ids' in vals_list.keys() and brand_woo_id and subtype_woo_id and tlc_woo_id:
                if 'brand_ids' in vals_list.keys() and brand_woo_id:
                    flag = True
                    attr_flag = True
                    brand_ids = vals_list['brand_ids'][0][2]
                    brand_ids = rec.brand_ids.browse(brand_ids)
                    print("adffeef", brand_ids)
                    brand_opt = brand_ids.mapped('brand')
                    attr_data = {
                        'id': brand_woo_id,
                        'visible': True,
                        'variation': False,
                        'options': brand_opt
                    }
                    att_list.append(attr_data)
                elif self.brand_ids and brand_woo_id:
                    flag = True
                    attr_flag = True
                    brand_ids = self.brand_ids
                    # brand_ids = rec.brand_ids.browse(brand_ids)
                    print("adffeef", brand_ids)
                    brand_opt = brand_ids.mapped('brand')
                    attr_data = {
                        'id': brand_woo_id,
                        'visible': True,
                        'variation': False,
                        'options': brand_opt
                    }
                    att_list.append(attr_data)
                if 'sub_ids' in vals_list.keys() and subtype_woo_id:
                    sub_ids = vals_list['sub_ids'][0][2]
                    sub_ids = rec.sub_ids.browse(sub_ids)
                    sub_opt = sub_ids.mapped('subtype')
                    attr_data = {
                        'id': subtype_woo_id,
                        'visible': True,
                        'variation': False,
                        'options': sub_opt
                    }
                    att_list.append(attr_data)
                elif self.sub_ids and subtype_woo_id:
                    sub_ids = self.sub_ids
                    # sub_ids = rec.sub_ids.browse(sub_ids)
                    sub_opt = sub_ids.mapped('subtype')
                    attr_data = {
                        'id': subtype_woo_id,
                        'visible': True,
                        'variation': False,
                        'options': sub_opt
                    }
                    att_list.append(attr_data)
                if 'tlc_ids' in vals_list.keys() and tlc_woo_id:
                    tlc_ids = vals_list['tlc_ids'][0][2]
                    print("sdasff", tlc_ids)
                    tlc_ids = rec.tlc_ids.browse(tlc_ids)
                    tlc_opt = tlc_ids.mapped('name')
                    attr_data = {
                        'id': tlc_woo_id,
                        'visible': True,
                        'variation': False,
                        'options': tlc_opt
                    }
                    att_list.append(attr_data)
                elif self.tlc_ids and tlc_woo_id:
                    tlc_ids = self.tlc_ids
                    # tlc_ids = rec.tlc_ids.browse(tlc_ids)
                    tlc_opt = tlc_ids.mapped('name')
                    attr_data = {
                        'id': tlc_woo_id,
                        'visible': True,
                        'variation': False,
                        'options': tlc_opt
                    }
                    att_list.append(attr_data)
                if 'attribute_line_ids' in vals_list.keys() and qty_woo_id:
                    print("dsffffffffffffff")
                    flag = True
                    attr_flag = True
                    vals_ids = vals_list['attribute_line_ids'][0][2]
                    vals_id = vals_list['attribute_line_ids']
                    print("sadcdssfddre", vals_ids, vals_list['attribute_line_ids'])
                    if vals_ids:
                        print("saddfdsf", vals_ids.keys())
                        if 'value_ids' in vals_ids.keys():
                            print('dsdsd')
                            values_ids = vals_ids['value_ids'][0][2]
                            values_ids = self.env['product.attribute.value'].browse(values_ids)
                            print("sadcsadsafsdssfddre", values_ids)
                            names = []
                            for rec in values_ids:
                                names.append(rec.name)
                            print("afeferff", vals_ids)
                            print("afeferasdasff", names)

                            qty_attr_data = {
                                'id': qty_woo_id,
                                'visible': False,
                                'variation': True,
                                'options': names
                            }

                            print("sdaSDEDWEdffw", qty_attr_data)
                            att_list.append(qty_attr_data)
                        else:
                            if self.attribute_line_ids:
                                vals_ids = self.attribute_line_ids
                                names = []
                                for rec in vals_ids:
                                    if rec.value_ids:
                                        for vals in rec.value_ids:
                                            names.append(vals.name)
                                print("afeferff", vals_ids)
                                qty_attr_data = {
                                    'id': qty_woo_id,
                                    'visible': False,
                                    'variation': True,
                                    'options': names
                                }
                                att_list.append(qty_attr_data)
                        # print('valssssssss', vals_ids.keys())
                        vals_ids = vals_list['attribute_line_ids'][0][2]
                        if 'default_id' in vals_ids.keys():
                            default_id = vals_ids['default_id']
                            default_id = self.env['product.attribute.value'].browse(default_id)
                            print("sadcsadsafsdssfddre", default_id)
                            default_name = ''
                            for rec in default_id:
                                default_name = rec.name
                            print("afeferff", vals_ids)
                            print("afeferasdasff", default_name)

                            default_data = {
                                "id": qty_woo_id,
                                "name": "Qty",
                                "option": default_name

                            }
                            print("sdadfdddddddddddfw", default_data)
                            default_list.append(default_data)
                        else:
                            if self.attribute_line_ids:
                                vals_ids = self.attribute_line_ids
                                default_name = ''
                                for rec in vals_ids:
                                    if rec.default_id:
                                        default_name = rec.default_id.name
                                default_data = {
                                    "id": qty_woo_id,
                                    "name": "Qty",
                                    "option": default_name

                                }
                                print("sdadsafefwefrwefweffw", default_data)
                                default_list.append(default_data)

                elif self.attribute_line_ids and qty_woo_id:
                    flag = True
                    attr_flag = True
                    vals_ids = self.attribute_line_ids
                    names = []
                    for rec in vals_ids:
                        for vals in rec.value_ids:
                            names.append(vals.name)
                    print("afeferff", vals_ids)
                    attr_data = {
                        'id': qty_woo_id,
                        'visible': False,
                        'variation': True,
                        'options': names
                    }
                    att_list.append(attr_data)
                    default_name = ''
                    for rec in vals_ids:
                        if rec.default_id:

                            default_name = rec.default_id.name
                    default_data = {
                        "id": qty_woo_id,
                        "name": "Qty",
                        "option": default_name

                    }
                    print("sdaddddedEFWffw", default_data)
                    default_list.append(default_data)

                if attr_flag:
                    data.update({
                        "attributes": att_list,
                        "default_attributes": default_list
                    })
                print("sacdddddcad", data)
                if flag:
                    e = wcapi.put("products/" + self.woo_id + "", data)
                    print("sdwedwefdewad", e.text)
        res = super(ProductTemplateInherited, self).write(vals_list)
        return res


class ProductProductInherited(models.Model):
    _inherit = 'product.product'

    woo_price = fields.Float(string="woo price")
    webhook = fields.Boolean(string="Webhook", readonly=True, default=False)
    woo_var_id = fields.Char(string="Woo Variant ID", readonly=True)
    regular_price = fields.Float(string="Regular Price")
    lst_price = fields.Float(
        'Sales Price',
        store=True,
        help="The sale price is managed from the product template. Click on the 'Configure Variants' button to set the extra attribute prices.")

    def unlink(self):
        """
        For deleting on both instances.
        """
        for recd in self:
            if recd.woo_var_id:
                wcapi = recd.product_tmpl_id.instance_id.get_api()
                wcapi.delete("products/" + recd.product_tmpl_id.woo_id + "/variations/" + recd.woo_var_id + "",
                             params={"force": True}).json()
        return super(ProductProductInherited, self).unlink()

    # @api.model
    # def create(self, vals_list):
    #     """
    #         For creating on both instances.
    #     """
    #     res = super(ProductProductInherited, self).create(vals_list)
    #     product_tmpl_woo_id = self.env['product.template'].browse(res.product_tmpl_id)
    #     _logger.info("context prod.prod %s", self._context)
    #     if not res.woo_var_id and product_tmpl_woo_id:
    #         _logger.info("template createeeeeee")
    #         instance_id = self.env['woo.commerce'].search([('active', '=', True)], limit=1)
    #         wcapi = instance_id.get_api()
    #         attributes = wcapi.get("products/attributes").json()
    #         qty_woo_id = False
    #         for attrs in attributes:
    #             if attrs.get('name') == 'Qty':
    #                 qty_woo_id = attrs.get('id')
    #         prd_opt = res.product_template_attribute_value_ids.mapped('name')
    #         reg_price = res.regular_price
    #         data = {
    #             "regular_price": str(reg_price),
    #             "attributes": [
    #                 {
    #                     "id": qty_woo_id,
    #                     "option": prd_opt[0] if prd_opt else ""
    #                 }
    #             ]
    #         }
    #         print("cdafcefs", data)
    #         y = wcapi.post("products/" + str(res.product_tmpl_id.woo_id) + "/variations", data).json()
    #         print("sdacdscsd", y)
    #         res.woo_var_id = str(y.get('id'))
    #         res.product_tmpl_id.woo_variant_check = True
    #     return res

    def _compute_product_lst_price(self):
        return True

    def write(self, vals_list):
        """
        For updating on both instances.
        """
        print("acsddddc", vals_list)
        _logger.info("prod prod webhoook %s", self._context.get('webhook'))
        for rec in self:
            if rec.instance_id and rec.woo_id and not self._context.get('webhook'):
                _logger.info("product write fun..........")
                wcapi = rec.product_tmpl_id.instance_id.get_api()
                flag = False
                data = {}
                if 'lst_price' in vals_list.keys():
                    flag = True
                    sales_price = vals_list['lst_price']
                    data.update(
                        {
                            'sale_price': str(sales_price)
                        }
                    )

                if 'regular_price' in vals_list.keys():
                    flag = True
                    reg_price = vals_list['regular_price']
                    data.update(
                        {
                            'regular_price': str(reg_price)
                        }
                    )
                if 'barcode' in vals_list.keys():
                    flag = True
                    sku = vals_list['barcode']
                    data.update(
                        {
                            'sku': sku
                        }
                    )
                if flag:
                    wcapi.put("products/" + str(rec.product_tmpl_id.woo_id) + "/variations/" + str(rec.woo_var_id) + "",
                              data)
        res = super(ProductProductInherited, self).write(vals_list)
        return res


class ResPartnerInherited(models.Model):
    _inherit = 'res.partner'

    woo_id = fields.Char(string="Woo ID", readonly=True)
    woo_user_name = fields.Char(string="User Name", readonly=True)
    instance_id = fields.Many2one('woo.commerce', string="Instance", readonly=True)
    date_created = fields.Date('Date Created')

    def unlink(self):
        """
        For deleting on both instances.
        """

        for recd in self:
            if recd.woo_id:
                wcapi = recd.instance_id.get_api()
                wcapi.delete("customers/" + str(recd.woo_id),
                             params={"force": True}).json()

        return super(ResPartnerInherited, self).unlink()

    def write(self, vals_list):
        """
        For updating on both instances.
        """
        res = super(ResPartnerInherited, self).write(vals_list)
        for rec in self:
            if rec.instance_id and rec.woo_id:
                wcapi = rec.instance_id.get_api()
                data = {}
                flag = False
                contact_fn = False
                contact_ln = False
                contact_email = False
                if self.type != 'contact':
                    woo_id = self.parent_id.woo_id
                else:
                    woo_id = self.woo_id
                if self.name:
                    contact_name = self.name
                    flag = True
                    if ' ' in contact_name:
                        contact_fn = contact_name.split(' ')[0]
                        contact_ln = contact_name.split(' ')[1]
                        if ' ' in contact_ln:
                            contact_ln = contact_ln.split(' ')[1]
                        else:
                            contact_ln = contact_ln
                    else:
                        contact_fn = contact_name
                        contact_ln = ' '
                if self.email:
                    contact_email = self.email
                data.update(
                    {
                        'first_name': contact_fn,
                        'last_name': contact_ln,
                        'email': contact_email if self.email else False
                    }
                )
                _logger.info(" contct data %s", data)
                for rec in self.parent_id.child_ids:
                    if rec.type == 'invoice':
                        flag = True
                        invoice_name = rec.name if rec.name else ""
                        invoice_email = rec.email if rec.email else ""
                        invoice_street = rec.street if rec.street else ""
                        invoice_street2 = rec.street2 if rec.street2 else ""
                        invoice_city = rec.city if rec.city else ""
                        invoice_state = rec.state_id.name if rec.state_id else ""
                        invoice_country = rec.country_id.name if rec.country_id else ""
                        invoice_zip = rec.zip if rec.zip else ""
                        invoice_phone = rec.phone if rec.phone else ""
                        if ' ' in invoice_name:
                            invoice_fn = invoice_name.split(' ')[0]
                            invoice_ln = invoice_name.split(' ')[1]
                            if ' ' in invoice_ln:
                                invoice_ln = invoice_ln.split(' ')[1]
                            else:
                                invoice_ln = invoice_ln
                        else:
                            invoice_fn = invoice_name
                            invoice_ln = ' '
                        data.update(
                            {
                                'billing': {
                                    'first_name': invoice_fn,
                                    'last_name': invoice_ln,
                                    'address_1': invoice_street,
                                    'address_2': invoice_street2,
                                    'city': invoice_city,
                                    'state': invoice_state,
                                    'country': invoice_country,
                                    'postcode': invoice_zip,
                                    'email': invoice_email,
                                    'phone': invoice_phone,
                                }
                            }
                        )

                    if rec.type == 'delivery':
                        flag = True
                        delivery_name = rec.name if rec.name else ""
                        delivery_street = rec.street if rec.street else ""
                        delivery_street2 = rec.street2 if rec.street2 else ""
                        delivery_city = rec.city if rec.city else ""
                        delivery_state = rec.state_id.name if rec.state_id else ""
                        delivery_country = rec.country_id.name if rec.country_id else ""
                        delivery_zip = rec.zip if rec.zip else ""
                        if ' ' in delivery_name:
                            delivery_fn = delivery_name.split(' ')[0]
                            delivery_ln = delivery_name.split(' ')[1]
                            if ' ' in delivery_ln:
                                delivery_ln = delivery_ln.split(' ')[1]
                            else:
                                delivery_ln = delivery_ln
                        else:
                            delivery_fn = delivery_name
                            delivery_ln = ' '
                        data.update(
                            {
                                'shipping': {
                                    'first_name': delivery_fn,
                                    'last_name': delivery_ln,
                                    'address_1': delivery_street,
                                    'address_2': delivery_street2,
                                    'city': delivery_city,
                                    'state': delivery_state,
                                    'country': delivery_country,
                                    'postcode': delivery_zip,
                                }
                            }
                        )

                if flag and woo_id:
                    wcapi.put("customers/" + woo_id + "", data)

        return res


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    woo_id = fields.Char(string="Woo ID")
    woo_order_key = fields.Char(string="Order Key", readonly=True)
    instance_id = fields.Many2one('woo.commerce', string="Instance", readonly=True)
    woo_order_status = fields.Char('WooCommerce Order Status', readonly=True)
    state_check = fields.Boolean(compute='state_change')
    woo_coupon_ids = fields.One2many('woo.order.coupons', 'woo_order_id', string="Woo Coupon Details", readonly=True)
    location_id = fields.Many2one('stock.location', string="Warehouse", related='instance_id.location_id')

    def state_change(self):
        """
        For computing invoiced quantity based on the woo status.
        """
        if self.woo_order_status != 'completed':
            for order in self.order_line:
                order.qty_invoiced = 0
        self.state_check = True

    def unlink(self):
        """
        For deleting on both instances.
        """

        for recd in self:
            if recd.woo_id:
                wcapi = recd.instance_id.get_api()
                wcapi.delete("orders/" + str(recd.woo_id),
                             params={"force": True}).json()

        return super(SaleOrderInherit, self).unlink()


class WooOrderCoupons(models.Model):
    _name = 'woo.order.coupons'
    _description = "Woo Order Coupons"

    woo_coupon_id = fields.Char('Woo ID', readonly=True)
    coupon_code = fields.Char("Coupon Code", readonly=True)
    discount_amount = fields.Float("Discount Amount", readonly=True)
    tax_discount = fields.Float("Tax Discount", readonly=True)
    woo_order_id = fields.Many2one('sale.order')


class AccountTaxInherited(models.Model):
    _inherit = 'account.tax'

    woo_id = fields.Char(string="Woo ID", readonly=True)
    instance_id = fields.Many2one('woo.commerce', string="Instance", readonly=True)
    tax_class = fields.Char(string="Tax Class", readonly=True)


class ProductCategoryInherited(models.Model):
    _inherit = 'product.category'

    woo_id = fields.Char(string="Woo ID", readonly=True)
    instance_id = fields.Many2one('woo.commerce', string="Instance", readonly=True)


class ProductAttributeInherited(models.Model):
    _inherit = 'product.attribute'

    woo_id = fields.Char(string="Woo ID", readonly=True)
    # webhook = fields.Boolean("Webhook", default=False)
    instance_id = fields.Many2one('woo.commerce', string="Instance", readonly=True)
    name = fields.Char("Name")

    def unlink(self):
        """
        For deleting on both instances.
        """
        for recd in self:
            if recd.woo_id:
                wcapi = recd.instance_id.get_api()
                wcapi.delete("products/attributes/" + recd.woo_id, params={"force": True}).json()
        return super(ProductAttributeInherited, self).unlink()

    @api.model
    def create(self, vals):
        """
         For creating on both instances.
        """
        res = super(ProductAttributeInherited, self).create(vals)
        if 'woo_id' not in vals.keys() and not res.woo_id:
            _logger.info("attr create fun........")
            instance_id = self.instance_id.search([('active', '=', True)], limit=1)
            wcapi = instance_id.get_api()
            data = {
                "name": res.name,
            }
            print("fcfc", data)
            _logger.info("dweadwed %s", data)
            attr_res = wcapi.post("products/attributes", data).json()
            print("sffserferf", attr_res)
            _logger.info("dweadwSDAAWDAWQed %s", attr_res)
            res.woo_id = str(attr_res.get('id'))
            res.instance_id = instance_id.id
        return res

    # def write(self, vals):
    #     """
    #         For updating on both instances.
    #     """
    #     res = super(ProductAttributeInherited, self).write(vals)
    #     instance_id = self.instance_id.search([('active', '=', True)], limit=1)
    #     wcapi = instance_id.get_api()
    #     data = {
    #         "id": self.woo_id,
    #         "name": self.name,
    #     }
    #     attr_res = wcapi.put("products/attributes/" + str(self.woo_id), data).json()
    #     print("dfwerfew", attr_res)
    #     return res


class CouponCouponInherited(models.Model):
    _inherit = 'coupon.coupon'

    woo_id = fields.Char(string="Woo ID", readonly=True)
    instance_id = fields.Many2one('woo.commerce', string="Instance", readonly=True)
