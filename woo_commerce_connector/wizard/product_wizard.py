# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields, _
from woocommerce import API
import requests
import base64
import logging
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class WooWizard(models.TransientModel):
    _name = 'woo.wizard'
    _description = "Woo Operation Wizard"

    name = fields.Char(string="Instance Name", readonly=True)
    consumer_key = fields.Char(string="Consumer Key", readonly=True)
    consumer_secret = fields.Char(string="Consumer Secret", readonly=True)
    store_url = fields.Char(string="Store URL", readonly=True)
    product_check = fields.Boolean(string="Products")
    customer_check = fields.Boolean(string="Customers")
    order_check = fields.Boolean(string="Orders")
    currency = fields.Char("Currency", readonly=True)
    journal = fields.Selection([('bank', 'Bank'), ('cash', 'Cash')])
    location_id = fields.Many2one("stock.location", string="Location")

    def get_api(self):
        """
        It returns the API object for operations
        """

        wcapi = API(
            url="" + self.store_url + "/index.php/",  # Your store URL
            consumer_key=self.consumer_key,  # Your consumer key
            consumer_secret=self.consumer_secret,  # Your consumer secret
            wp_api=True,  # Enable the WP REST API integration
            version="wc/v3",  # WooCommerce WP REST API version
            timeout=500,
        )
        return wcapi

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
        else:
            raise ValidationError(_(data['error']['message']))
        return link

    def get_woo_import(self):
        """
        function for importing data from woocommerce
        database

        """
        currency_name = self.env.company.currency_id.name
        currency_cal = requests.get('https://api.exchangerate-api.com/v4/latest/' + currency_name + '').json()
        currency_rates = currency_cal['rates']

        if self.product_check:
            active_id = self._context.get('active_id')
            wcapi = self.get_api()
            res = wcapi.get("products/categories", params={"per_page": 100}).json()
            category_ids = self.env['woocommerce.category'].search([])
            woo_ids = category_ids.mapped('woo_id')
            for recd in res:
                if str(recd.get('id')) not in woo_ids:
                    vals_cat = {
                        'name': recd.get('name'),
                        'woo_id': recd.get('id'),
                        'instance_id': active_id
                    }
                    self.env['woocommerce.category'].create(vals_cat)
            for recd in res:
                if recd.get('parent') != 0:
                    category_id = self.env['woocommerce.category'].search([('woo_id', '=', recd.get('id'))])
                    parent_id = self.env['woocommerce.category'].search([('woo_id', '=', recd.get('parent'))])
                    category_id.write({
                        'parent_id': parent_id.id,
                    })
            wcapi_attr = self.get_api()

            res = wcapi_attr.get("products/attributes", params={"per_page": 100}).json()
            print("sdasdfewf", res)
            attribute_ids = self.env['product.attribute'].search([])
            woo_ids = attribute_ids.mapped('woo_id')
            for recd in res:
                if str(recd.get('id')) not in woo_ids:
                    vals_attr = {
                        'name': recd.get('name'),
                        'woo_id': recd.get('id'),
                        'instance_id': active_id,
                        'display_type': 'select',
                    }
                    self.env['product.attribute'].create(vals_attr)
            wcapi = self.get_api()
            res = wcapi.get("products", params={"per_page": 100}).json()
            product_ids = self.env['product.template'].search([])
            woo_ids = product_ids.mapped('woo_id')

            if 'extra_charge' not in woo_ids:
                self.env['product.template'].create({
                    'name': 'Extra Charges',
                    'type': 'service',
                    'taxes_id': False,
                    'woo_id': 'extra_charge',
                    'instance_id': active_id
                })

            brand_obj = self.env['product.brand']
            subtype_obj = self.env['product.subtype']
            tlc_obj = self.env['product.tlc']
            woo_publish = False
            for recd in res:
                if recd.get('status') == 'publish':
                    woo_publish = True
                elif recd.get('status') == 'private':
                    woo_publish = False
                attr_info = []
                brand_id = False
                sub_id = False
                tlc_id = False
                subtype_list = []
                brand_list = []
                tlc_list = []
                veg_value = False
                for attr in recd.get('attributes'):
                    if attr.get('name') == 'Brand':
                        brand_ids = brand_obj.search([])
                        brand_woo_ids = brand_ids.mapped('brand')
                        for option in attr.get('options'):
                            if option not in brand_woo_ids:
                                brand_id = brand_obj.create({
                                    'brand': option,
                                    'woo_id': str(attr.get('id')),
                                    'instance_id': active_id,
                                })
                            else:
                                brand_id = brand_ids.filtered(lambda b: b.brand == option)
                            brand_list.append(brand_id.id)
                    if attr.get('name') == 'Sub Type':
                        sub_type_ids = subtype_obj.search([])
                        sub_type_woo_ids = sub_type_ids.mapped('subtype')
                        for option in attr.get('options'):
                            if option not in sub_type_woo_ids:
                                sub_id = subtype_obj.create({
                                    'subtype': option,
                                    'slug': option.lower(),
                                    'woo_id': str(attr.get('id')),
                                    'instance_id': active_id,
                                })
                            else:
                                sub_id = sub_type_ids.filtered(lambda s: s.subtype == option)
                            subtype_list.append(sub_id.id)
                    if attr.get('name') == 'TLC':
                        tlc_ids = tlc_obj.search([])
                        tlc_woo_ids = tlc_ids.mapped('name')
                        for option in attr.get('options'):
                            if option not in tlc_woo_ids:
                                tlc_id = tlc_obj.create({
                                    'name': option,
                                    'woo_id': str(attr.get('id')),
                                    'instance_id': active_id,
                                })
                            else:
                                tlc_id = tlc_ids.filtered(lambda t: t.name == option)
                            tlc_list.append(tlc_id.id)

                    var_info = []
                    attr_id = self.env['product.attribute'].search(
                        [('woo_id', '=', attr.get('id')), ('instance_id', '=', active_id)])

                    qty_info = []
                    if attr.get('name') == 'Qty':
                        if attr.get('variation'):
                            for var in attr.get('options'):
                                qty_info.append(var)
                                if var not in attr_id.value_ids.mapped('name'):
                                    vals_line = (0, 0, {
                                        'name': var
                                    })
                                    var_info.append(vals_line)
                            if var_info:
                                attr_id.write({
                                    'value_ids': var_info
                                })

                            if attr_id.value_ids:
                                vals_line = (0, 0, {
                                    'attribute_id': attr_id.id,
                                    'value_ids': attr_id.value_ids.filtered(lambda r: r.name in qty_info)
                                })
                                attr_info.append(vals_line)

                    if attr.get('name') == 'veg':
                        if attr.get('options')[0] == 'Yes':
                            veg_value = 'yes'
                        else:
                            veg_value = 'no'

                caty_list = []
                if str(recd.get('id')) not in woo_ids:
                    for caty in recd.get('categories'):
                        categ_id = caty.get('id')
                        caty_list.append(categ_id)
                    category_ids = self.env['woocommerce.category'].search([('woo_id', 'in', caty_list)])
                    list_price = round(float(recd.get('price')) * currency_rates[self.currency], 4) if recd.get(
                        'price') else 0

                    if recd.get('images') and attr_info:
                        output_img = base64.b64encode(requests.get(recd['images'][0].get('src')).content)
                        print("")
                        vals = {
                            'name': recd.get('name'),
                            'list_price': list_price,
                            'type': "product",
                            'woo_publish': woo_publish,
                            'image_1920': output_img,
                            'woo_id': recd.get('id'),
                            'instance_id': active_id,
                            'woo_categ_ids': category_ids.ids,
                            'brand_ids': brand_list,
                            'sub_ids': subtype_list,
                            'tlc_ids': tlc_list,
                            'veg': veg_value,
                            'attribute_line_ids': attr_info if attr_info else False,
                        }

                        prd_id = self.env['product.template'].create(vals)

                        for var_id in prd_id.product_variant_ids:
                            prd_opt = var_id.product_template_attribute_value_ids.mapped('name')
                            wcapi = self.get_api()
                            result = wcapi.get("products/" + str(recd.get('id')) + "/variations").json()

                            for dit in result:
                                reg_price = round(float(dit.get('regular_price')) * currency_rates[self.currency], 4)if dit.get('regular_price') else 0
                                woo_price = round(float(dit.get('price')) * currency_rates[self.currency], 4)
                                options = [i['option'] for i in dit.get('attributes')]

                                if set(prd_opt) == set(options):

                                    prd_id.write({
                                        'woo_variant_check': True
                                    })
                                    if dit.get('image'):
                                        output_img = base64.b64encode(requests.get(dit['image'].get('src')).content)
                                    var_id.write({
                                        'woo_var_id': dit.get('id'),
                                        'lst_price': woo_price,
                                        'barcode': dit.get('sku') if dit.get('sku') else None,
                                        'regular_price': reg_price,
                                        'image_1920': output_img
                                    })
                    elif recd.get('images') and not attr_info:
                        output_img = base64.b64encode(requests.get(recd['images'][0].get('src')).content)
                        vals = {
                            'name': recd.get('name'),
                            'list_price': list_price,
                            'type': "product",
                            'woo_publish': woo_publish,
                            'image_1920': output_img,
                            'woo_id': recd.get('id'),
                            'instance_id': active_id,
                            'woo_categ_ids': category_ids.ids,
                            'brand_ids': brand_list,
                            'sub_ids': subtype_list,
                            'tlc_ids': tlc_list,
                            'veg': veg_value,
                        }

                        prd_id = self.env['product.template'].create(vals)

                    elif not recd.get('images') and attr_info:

                        vals = {
                            'name': recd.get('name'),
                            'list_price': list_price,
                            'type': "product",
                            'woo_publish': woo_publish,
                            'woo_id': recd.get('id'),
                            'instance_id': active_id,
                            'woo_categ_ids': category_ids.ids,
                            'brand_ids': brand_list,
                            'sub_ids': subtype_list,
                            'tlc_ids': tlc_list,
                            'veg': veg_value,
                            'attribute_line_ids': attr_info if attr_info else False,
                        }

                        prd_id = self.env['product.template'].create(vals)

                        for var_id in prd_id.product_variant_ids:
                            prd_opt = var_id.product_template_attribute_value_ids.mapped('name')
                            wcapi = self.get_api()
                            result = wcapi.get("products/" + str(recd.get('id')) + "/variations").json()
                            for dit in result:
                                reg_price = round(float(dit.get('regular_price')) * currency_rates[self.currency], 4)if dit.get('regular_price') else 0
                                woo_price = round(float(dit.get('price')) * currency_rates[self.currency], 4) if dit.get('price') else 0
                                options = [i['option'] for i in dit.get('attributes')]

                                if set(prd_opt) == set(options):
                                    prd_id.write({
                                        'woo_variant_check': True
                                    })
                                    if dit.get('image'):
                                        output_img = base64.b64encode(requests.get(dit['image'].get('src')).content)
                                        var_id.write({
                                            'woo_var_id': dit.get('id'),
                                            'lst_price': woo_price,
                                            'barcode': dit.get('sku') if dit.get('sku') else None,
                                            'regular_price': reg_price,
                                            'image_1920': output_img
                                        })
                                    else:
                                        var_id.write({
                                            'woo_var_id': dit.get('id'),
                                            'lst_price': woo_price,
                                            'barcode': dit.get('sku') if dit.get('sku') else None,
                                            'regular_price': reg_price,
                                        })

                    else:

                        list_price = round(float(recd.get('price')) * currency_rates[self.currency], 4) if recd.get(
                            'price') else 0

                        vals = {
                            'name': recd.get('name'),
                            'list_price': list_price,
                            'type': "product",
                            'woo_publish': woo_publish,
                            'woo_id': recd.get('id'),
                            'brand_ids': brand_list,
                            'sub_ids': subtype_list,
                            'instance_id': active_id,
                            'woo_categ_ids': category_ids.ids,
                            'veg': veg_value,
                            'tlc_ids': tlc_list,
                        }
                        prd_id = self.env['product.template'].create(vals)

        if self.customer_check:
            wcapi = self.get_api()
            res = wcapi.get("customers", params={"per_page": 100}).json()
            customer_ids = self.env['res.partner'].search([])
            woo_ids = customer_ids.mapped('woo_id')
            active_id = self._context.get('active_id')
            for recd in res:
                if str(recd.get('id')) not in woo_ids:
                    if recd['billing'].get('country') and recd['billing'].get('state') and \
                            recd['shipping'].get('country') and recd['shipping'].get('state'):
                        country_id = self.env['res.country'].search([('code', '=', recd['billing'].get('country'))])
                        state_id = self.env['res.country.state'].search([('code', '=', recd['billing'].get('state')),
                                                                         ('country_id', '=', country_id.id)])
                        vals = {
                            'company_type': "person",
                            'name': recd.get('first_name') + " " + recd.get('last_name'),
                            'street': recd['billing'].get('address_1'),
                            'city': recd['billing'].get('city'),
                            'state_id': state_id.id,
                            'zip': recd['billing'].get('postcode'),
                            'country_id': country_id.id,
                            'phone': recd['billing'].get('phone'),
                            'email': recd.get('email'),
                            'woo_id': recd.get('id'),
                            'woo_user_name': recd.get('username'),
                            'instance_id': active_id
                        }
                        contact = self.env['res.partner'].create(vals)

                    else:
                        vals = {
                            'company_type': "person",
                            'name': recd.get('first_name') + " " + recd.get('last_name'),
                            'email': recd.get('email'),
                            'woo_id': recd.get('id'),
                            'woo_user_name': recd.get('username'),
                            'instance_id': active_id
                        }
                        contact = self.env['res.partner'].create(vals)

        if self.order_check:
            active_id = self._context.get('active_id')
            wcapi = self.get_api()
            res = wcapi.get("taxes", params={"per_page": 100}).json()
            tax_ids = self.env['account.tax'].search([])
            woo_ids = tax_ids.mapped('woo_id')
            for recd in res:
                if str(recd.get('id')) not in woo_ids:
                    vals_tax = {
                        'name': recd.get('name'),
                        'amount': recd.get('rate'),
                        'woo_id': recd.get('id'),
                        'instance_id': active_id,
                        'tax_class': recd.get('class'),
                        'description': recd.get('rate').split('.')[0] + ".00%"
                    }

                    self.env['account.tax'].create(vals_tax)
            wcapi = self.get_api()
            res = wcapi.get("orders", params={"per_page": 100}).json()

            sale_order_ids = self.env['sale.order'].search([('state', '!=', 'cancel')])
            woo_ids = sale_order_ids.mapped('woo_id')
            service_id = self.env['product.product'].search([('woo_id', '=', 'extra_charge')])
            for recd in res:
                if str(recd.get('id')) not in woo_ids and recd.get('status') != 'cancelled':
                    partner_id = self.env['res.partner'].search([('woo_id', '=', recd.get('customer_id'))])
                    if not partner_id:
                        if recd['billing'].get('country') and recd['billing'].get('state'):
                            country_id = self.env['res.country'].search([('code', '=', recd['billing'].get('country'))])
                            state_id = self.env['res.country.state'].search(
                                [('code', '=', recd['billing'].get('state')),
                                 ('country_id', '=', country_id.id)])
                            vals = {
                                'company_type': "person",
                                'name': recd['billing'].get('first_name') + " " + recd['billing'].get('last_name'),
                                'street': recd['billing'].get('address_1'),
                                'city': recd['billing'].get('city'),
                                'state_id': state_id.id,
                                'zip': recd['billing'].get('postcode'),
                                'country_id': country_id.id,
                                'phone': recd['billing'].get('phone'),
                                'email': recd['billing'].get('email'),
                                'woo_id': recd.get('customer_id'),
                                'instance_id': active_id
                            }
                            contact = self.env['res.partner'].create(vals)

                        else:
                            vals = {
                                'company_type': "person",
                                'name': recd['billing'].get('first_name') + " " + recd['billing'].get('last_name'),
                                'email': recd['billing'].get('email'),
                                'woo_id': recd.get('customer_id'),
                                'instance_id': active_id
                            }
                            contact = self.env['res.partner'].create(vals)

                        partner_id = contact
                    order_info = []
                    coupon_info = []
                    for coupon in recd.get('coupon_lines'):
                        discount_amount = round(int(coupon.get('discount')) * currency_rates[self.currency], 4)
                        tax_discount = round(int(coupon.get('discount_tax')) * currency_rates[self.currency], 4)
                        coupon_vals = (0, 0, {
                            'woo_coupon_id': coupon.get('id'),
                            'coupon_code': coupon.get('code'),
                            'discount_amount': discount_amount,
                            'tax_discount': tax_discount
                        })
                        coupon_info.append(coupon_vals)
                    for line in recd.get('line_items'):
                        if line.get('variation_id'):
                            product_id = self.env['product.product'].search([('woo_id', '=', line.get('product_id')),
                                                                             ('woo_var_id', '=',
                                                                              line.get('variation_id'))])
                        else:
                            product_id = self.env['product.product'].search([('woo_id', '=', line.get('product_id'))])
                        if not product_id:
                            product_id = self.env['product.product'].create({'woo_id': line.get('product_id')})
                        price_unit = round(float(line.get('price')) * currency_rates[self.currency], 4)
                        vals_line = (0, 0, {
                            'product_id': product_id.id,
                            'name': product_id.description if product_id.description else product_id.name,
                            'product_uom_qty': line.get('quantity'),
                            'price_unit': price_unit,
                        })
                        order_info.append(vals_line)
                    if recd.get('shipping_lines'):
                        for line in recd.get('shipping_lines'):
                            price_unit = round(float(line.get('total')) * currency_rates[self.currency], 4)
                            if float(line.get('total')) > 0:
                                vals_line = (0, 0, {
                                    'product_id': service_id.id,
                                    'name': "Shipping : " + line.get('method_title'),
                                    'price_unit': price_unit,
                                })
                                order_info.append(vals_line)
                    if recd.get('fee_lines'):
                        for line in recd.get('fee_lines'):
                            price_unit = round(float(line.get('total')) * currency_rates[self.currency], 4)
                            if float(line.get('total')) > 0:
                                vals_line = (0, 0, {
                                    'product_id': service_id.id,
                                    'name': line.get('name'),
                                    'price_unit': price_unit,
                                })
                                order_info.append(vals_line)

                    vals = {
                        'partner_id': partner_id.id,
                        'order_line': order_info,
                        'woo_id': recd.get('id'),
                        'woo_order_key': recd.get('order_key'),
                        'instance_id': active_id,
                        'woo_order_status': recd.get('status'),
                        'woo_coupon_ids': coupon_info,
                        'state': 'sale'
                    }
                    sale_id = self.env['sale.order'].create(vals)

                    if sale_id:
                        for picking in sale_id.picking_ids:
                            picking.action_assign()

            coupon_res = wcapi.get("coupons").json()
            coupon_ids = self.env['coupon.coupon'].search([('woo_id', '!=', False)])
            woo_ids = coupon_ids.mapped('woo_id')
            for coupon in coupon_res:
                if int(coupon.get('id')) not in woo_ids:
                    vals = {
                        "woo_id": coupon.get('id'),
                        "code": coupon.get('code'),
                        "instance_id": active_id,
                        "expiration_date": coupon.get('date_expires'),
                    }
                    coupon_id = self.env['coupon.coupon'].create(vals)

    def get_woo_export(self):
        """
        function for Exporting data to woocommerce
        database

        """
        currency_name = self.env.company.currency_id.name
        currency_cal = requests.get('https://api.exchangerate-api.com/v4/latest/' + currency_name + '').json()
        currency_rates = currency_cal['rates']
        if self.product_check:
            active_id = self._context.get('active_id')
            wcapi = self.get_api()
            category_ids = self.env['woocommerce.category'].search([('woo_id', '=', False)])

            for recd in category_ids:
                if not recd.parent_id:
                    data = {
                        "name": recd.name,
                    }
                    cat_res = wcapi.post("products/categories", data).json()

                    recd.woo_id = cat_res.get('id')
                    recd.instance_id = active_id

            for recd in category_ids:
                if recd.parent_id:
                    parent_id = self.env['woocommerce.category'].search([('id', '=', recd.parent_id.id)])
                    data = {
                        "name": recd.name,
                        "parent": parent_id.woo_id
                    }
                    cat_res = wcapi.post("products/categories", data).json()

                    recd.woo_id = cat_res.get('id')
                    recd.instance_id = active_id
            wcapi = self.get_api()
            attribute_ids = self.env['product.attribute'].search([('woo_id', '=', False)])
            for recd in attribute_ids:
                data = {
                    "name": recd.name,
                    "slug": recd.name,
                    "type": "select",
                    "order_by": "menu_order",
                    "has_archives": True
                }
                att_res = wcapi.post("products/attributes", data).json()
                recd.woo_id = att_res.get('id')
                recd.instance_id = active_id

            products = self.env['product.template'].search([('woo_id', '=', False), ('type', '=', 'product')])
            attributes = wcapi.get("products/attributes").json()
            brand_woo_id = False
            subtype_woo_id = False
            tlc_woo_id = False
            for attrs in attributes:
                if attrs.get('name') == 'Brand':
                    brand_woo_id = attrs.get('id')
                if attrs.get('name') == 'Sub Type':
                    subtype_woo_id = attrs.get('id')
                if attrs.get('name') == 'TLC':
                    tlc_woo_id = attrs.get('id')

            sl_no = 0
            for recd in products:
                att_id = []
                sl_no += 1
                image_url = False
                product = self.env['product.product'].search([('product_tmpl_id', '=', recd.id)])
                stock_check = False
                stock_qty = 0
                if len(recd.product_variant_ids) == 1 and product.stock_quant_ids:
                    location_id = product.stock_quant_ids.filtered(lambda s: s.location_id == self.location_id)
                    if location_id:
                        stock_check = True
                        stock_qty = location_id.available_quantity
                if recd.image_1920:
                    image = base64.decodebytes(recd.image_1920)
                    image_url = self.image_upload(image)

                for att in recd.attribute_line_ids:
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
                if recd.brand_ids and brand_woo_id:
                    brand_data = {
                        'id': brand_woo_id,
                        'visible': False,
                        'variation': False,
                        'options': recd.brand_ids.mapped('brand')
                    }
                    att_id.append(brand_data)
                if recd.sub_ids and subtype_woo_id:
                    subtype_data = {
                        'id': subtype_woo_id,
                        'visible': False,
                        'variation': False,
                        'options': recd.sub_ids.mapped('subtype')
                    }
                    att_id.append(subtype_data)
                if recd.tlc_ids and tlc_woo_id:
                    tlc_data = {
                        'id': tlc_woo_id,
                        'visible': False,
                        'variation': False,
                        'options': recd.tlc_ids.mapped('name')
                    }
                    att_id.append(tlc_data)

                cat_woo_ids = recd.woo_categ_ids.mapped('woo_id')
                cat_list = []
                for i in range(len(cat_woo_ids)):
                    data = {
                        'id': cat_woo_ids[i]
                    }
                    cat_list.append(data)
                if att_id and recd.image_1920:
                    wcapi = self.get_api()
                    regular_price = round(currency_rates[self.currency] * recd.list_price, 4) if recd.list_price else 0
                    data = {
                        "name": recd.name,
                        "type": "variable",
                        "regular_price": str(regular_price),
                        "description": "",
                        "manage_stock": stock_check,
                        "stock_quantity": stock_qty,
                        "short_description": "",
                        "categories": cat_list,
                        "attributes": att_id,
                        "images": [
                            {
                                "src": image_url
                            },
                        ],
                    }

                    res = wcapi.post("products", data).json()

                    _logger.info("Variant With Image %s", res)
                    recd.woo_id = res.get('id')
                    recd.instance_id = active_id
                    recd.woo_variant_check = True
                    wcapi = self.get_api()

                    for var in recd.product_variant_ids:
                        opt_info = []
                        for qty in var.product_template_attribute_value_ids:
                            for att_qty in att_id:
                                for i in range(len(att_qty['options'])):
                                    if att_qty['options'][i] == qty.name:
                                        att_vals = {
                                            "id": int(att_qty['id']),
                                            "option": qty.name
                                        }
                                        opt_info.append(att_vals)
                        if var.image_1920:
                            image = base64.decodebytes(var.image_1920)
                            image_url = self.image_upload(image)

                        else:
                            image = False
                        today = date.today()

                        stock_qty = 0
                        stock_check = False
                        if var.qty_available:
                            stock_check = True
                            stock_qty = var.qty_available
                        regular_price = round(currency_rates[self.currency] * var.lst_price, 4)
                        data = {
                            "regular_price": str(regular_price),
                            "attributes": opt_info,
                            "image": {
                                "src": image_url
                            },
                            "manage_stock": stock_check,
                            "stock_quantity": stock_qty

                        }

                        var_res = wcapi.post("products/" + str(res.get('id')) + "/variations", data).json()
                        var.woo_var_id = var_res.get('id')
                if att_id and not recd.image_1920:
                    wcapi = self.get_api()
                    regular_price = round(currency_rates[self.currency] * recd.list_price, 4) if recd.list_price else 0
                    data = {
                        "name": recd.name,
                        "type": "variable",
                        "regular_price": str(regular_price),
                        "description": "",
                        "short_description": "",
                        "manage_stock": stock_check,
                        "stock_quantity": stock_qty,
                        "categories": cat_list,
                        "attributes": att_id,

                    }

                    res = wcapi.post("products", data).json()
                    _logger.info("Variant With out Image %s", res)
                    recd.woo_id = res.get('id')
                    recd.instance_id = active_id
                    recd.woo_variant_check = True
                    wcapi = self.get_api()

                    for var in recd.product_variant_ids:
                        opt_info = []
                        stock_qty = 0
                        stock_check = False
                        if var.qty_available:
                            stock_check = True
                            stock_qty = var.qty_available
                        for qty in var.product_template_attribute_value_ids:
                            for att_qty in att_id:
                                for i in range(len(att_qty['options'])):
                                    if att_qty['options'][i] == qty.name:
                                        att_vals = {
                                            "id": int(att_qty['id']),
                                            "option": qty.name
                                        }
                                        opt_info.append(att_vals)
                        regular_price = round(currency_rates[self.currency] * var.lst_price, 4)
                        data = {
                            "regular_price": str(regular_price),
                            "attributes": opt_info,
                            "manage_stock": stock_check,
                            "stock_quantity": stock_qty,
                        }

                        var_res = wcapi.post("products/" + str(res.get('id')) + "/variations", data).json()

                        var.woo_var_id = var_res.get('id')
                if not att_id and recd.image_1920:
                    wcapi = self.get_api()
                    regular_price = round(currency_rates[self.currency] * recd.list_price, 4) if recd.list_price else 0
                    data = {
                        "name": recd.name,
                        "type": "simple",
                        "regular_price": str(regular_price),
                        "description": "",
                        "short_description": "",
                        "manage_stock": stock_check,
                        "stock_quantity": stock_qty,
                        "categories": cat_list,
                        "images": [
                            {
                                "src": image_url
                            },
                        ],
                    }

                    res = wcapi.post("products", data).json()
                    _logger.info(" no Variant With Image %s", res)
                    recd.woo_id = res.get('id')
                    recd.instance_id = active_id
                if not recd.image_1920 and not att_id:
                    wcapi = self.get_api()
                    regular_price = round(currency_rates[self.currency] * recd.list_price, 4) if recd.list_price else 0
                    data = {
                        "name": recd.name,
                        "type": "simple",
                        "regular_price": str(regular_price),
                        "description": "",
                        "short_description": "",
                        "manage_stock": stock_check,
                        "stock_quantity": stock_qty,
                        "categories": cat_list,
                    }

                    res = wcapi.post("products", data).json()
                    _logger.info("no Variant With no Image %s", res)
                    recd.woo_id = res.get('id')
                    recd.instance_id = active_id
        if self.customer_check:
            active_id = self._context.get('active_id')
            wcapi = self.get_api()
            customer_ids = self.env['res.partner'].search([('woo_id', '=', False), ('is_company', '=', False),
                                                           ('email', '!=', False)])
            for recd in customer_ids:
                name = recd.name.split(' ')
                username = recd.email.split('@')
                data = {
                    "email": recd.email,
                    "first_name": name[0],
                    "last_name": name[1] if len(name) > 1 else "",
                    "username": username[0],
                    "billing": {
                        "first_name": name[0],
                        "last_name": name[1] if len(name) > 1 else "",
                        "company": "",
                        "address_1": recd.street if recd.street else "",
                        "address_2": "",
                        "city": recd.city if recd.city else "",
                        "state": recd.state_id.code if recd.state_id else "",
                        "postcode": recd.zip if recd.zip else "",
                        "country": recd.country_id.code if recd.country_id else "",
                        "email": recd.email if recd.email else "",
                        "phone": recd.phone if recd.phone else ""
                    },
                    "shipping": {
                        "first_name": name[0],
                        "last_name": name[1] if len(name) > 1 else "",
                        "company": "",
                        "address_1": recd.street if recd.street else "",
                        "address_2": "",
                        "city": recd.city if recd.city else "",
                        "state": recd.state_id.code if recd.state_id else "",
                        "postcode": recd.zip if recd.zip else "",
                        "country": recd.country_id.code if recd.country_id else ""
                    }
                }
                res = wcapi.post('customers', data).json()
                recd.woo_id = res.get('id')
                recd.instance_id = active_id
