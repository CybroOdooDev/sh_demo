# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo import SUPERUSER_ID
import dateutil.parser
import odoo
import pytz
import logging

_logger = logging.getLogger(__name__)


class WebHookOrders(http.Controller):
    @http.route('/orders', type='json', auth='none', method=['GET', 'POST'],
                csrf=False)
    def get_create_order_webhook_url__(self, *args, **kwargs):
        ''' creating order from woocommerce to odoo'''

        try:
            customer_name = request.jsonrequest['shipping'].get('first_name') + ' ' + request.jsonrequest[
                'shipping'].get('last_name')
            partner_id = request.env['res.partner'].with_user(SUPERUSER_ID).search([('name', '=', customer_name)],
                                                                                   limit=1)
            if not partner_id:
                partner_id = request.env['res.partner'].with_user(SUPERUSER_ID).create({'name': customer_name})
            _logger.info("partner id ..... %s", partner_id)
            so = request.env['sale.order'].with_user(SUPERUSER_ID).create({
                "partner_id": partner_id.id,
                "date_order": odoo.fields.Datetime.to_string(
                    dateutil.parser.parse(request.jsonrequest['date_created']).astimezone(pytz.utc)),
                "l10n_in_gst_treatment": "consumer",
                "woo_id": request.jsonrequest['id'],
            })

            line_items = request.jsonrequest.get('line_items')
            _logger.info("line itemsssssss %s", line_items)
            if request.jsonrequest.get('line_items'):
                for line in line_items:
                    line_total = line.get('quantity') * line.get('price')
                    _logger.info("woo_product_idddddd %s", line.get('product_id'))
                    product_id = request.env['product.product'].with_user(SUPERUSER_ID).search(
                        [('woo_var_id', '=', line.get('variation_id'))])
                    _logger.info("product_id %s", product_id)
                    if product_id:
                        so.write({
                            'order_line': [
                                (0, 0, {
                                    'name': product_id.name,
                                    'product_id': product_id.id,
                                    'product_uom_qty': line.get('quantity'),
                                    'price_unit': line.get('price'),
                                    'price_subtotal': line_total,
                                })
                            ]
                        })
            if request.jsonrequest.get('status') == 'processing':
                so.action_confirm()

            return {"Message": "Success"}
        except Exception as e:
            return {"Message": "Something went wrong"}

    @http.route('/update_orders', type='json', auth='none', method=['PUT'],
                csrf=False)
    def get_update_order_webhook_url__(self, *args, **kwargs):
        ''' updating order from woocommerce to odoo'''

        record = request.env['sale.order'].with_user(SUPERUSER_ID).search(
            [('woo_id', '=', int(request.jsonrequest['id']))])

        customer_name = request.jsonrequest['shipping'].get('first_name') + ' ' + request.jsonrequest[
            'shipping'].get('last_name')
        partner_id = request.env['res.partner'].with_user(SUPERUSER_ID).search([('name', '=', customer_name)],
                                                                               limit=1)
        if not partner_id:
            partner_id = request.env['res.partner'].with_user(SUPERUSER_ID).create({'name': customer_name})

        try:
            record.with_user(SUPERUSER_ID).write({'partner_id': partner_id})
            line_items = request.jsonrequest.get('line_items')
            product_ids = record.order_line.mapped('product_id')
            if line_items:
                for line in line_items:
                    product_id = request.env['product.product'].with_user(SUPERUSER_ID).search(
                        [('woo_var_id', '=', line.get('variation_id'))])
                    if product_id.id not in product_ids.ids:
                        sale_order_line = request.env['sale.order.line'].with_user(SUPERUSER_ID).create({
                            'name': product_id.name,
                            'product_id': product_id.id,
                            'product_uom_qty': line.get('quantity'),
                            'price_unit': line.get('price'),
                            'order_id': record.id
                        })
                    else:
                        order_line_id = record.order_line.filtered(lambda l: l.product_id.id == product_id.id)
                        order_line_id.with_user(SUPERUSER_ID).write({
                            'name': product_id.name,
                            'product_id': product_id.id,
                            'product_uom_qty': line.get('quantity'),
                            'price_unit': line.get('price'),
                            'order_id': record.id
                        })
            if request.jsonrequest.get('status') == 'processing' and record.state == 'draft':
                record.action_confirm()

            return {"Message": "Success"}
        except Exception as e:
            return {"Message": "Something went wrong"}

    @http.route('/delete_orders', type='json', auth='none', method=['DELETE'],
                csrf=False)
    def get_delete_order_webhook_url__(self, *args, **kwargs):
        ''' deleting order from woocommerce'''

        try:
            record = request.env['sale.order'].with_user(SUPERUSER_ID).search(
                [('woo_id', '=', int(request.jsonrequest['id']))])
            record.action_cancel()
            return {"Message": "Success"}
        except Exception as e:
            return {"Message": "Something went wrong"}
