# -*- coding: utf-8 -*-

import requests
from woocommerce import API
from odoo import models, fields, _, api
from odoo.exceptions import UserError
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class WooCommerceInstance(models.Model):
    _name = 'woo.commerce'
    _description = "WooCommerce Instances"

    name = fields.Char(string="Instance Name", required=True)
    color = fields.Integer('Color')
    consumer_key = fields.Char(string="Consumer Key", required=True)
    consumer_secret = fields.Char(string="Consumer Secret", required=True)
    store_url = fields.Char(string="Store URL", required=True)
    currency = fields.Char("Currency", readonly=True)
    webhook_product = fields.Char(string='Product Url')
    webhook_customer = fields.Char(string='Customer Url')
    webhook_order = fields.Char(string='Order Url')
    webhook_coupon = fields.Char(string='Coupon Url')
    active = fields.Boolean(string="Active")
    location_id = fields.Many2one('stock.location', string="Location")

    def get_api(self):
        """
        Returns API object.
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

    def get_wizard(self):
        """
        function used for returning wizard view
        for operations

        """
        set_wcapi = API(
            url="" + self.store_url + "/index.php/wp-json/wc/v3/system_status?",  # Your store URL
            consumer_key=self.consumer_key,  # Your consumer key
            consumer_secret=self.consumer_secret,  # Your consumer secret
            wp_api=True,  # Enable the WP REST API integration
            version="wc/v3",  # WooCommerce WP REST API version
            timeout=500

        )
        set_res = set_wcapi.get("").json()
        currency = set_res['settings'].get('currency')
        self.currency = currency
        return {
            'name': _('Instance Operations'),
            'view_mode': 'form',
            'res_model': 'woo.wizard',
            'domain': [],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_name': self.name,
                        'default_consumer_key': self.consumer_key,
                        'default_consumer_secret': self.consumer_secret,
                        'default_store_url': self.store_url,
                        'default_currency': self.currency,
                        'default_location_id': self.location_id.id
                        }
        }

    def get_instance(self):
        """
        function is used for returning
        current form view of instance.

        """
        return {
            'name': _('Instance'),
            'view_mode': 'form',
            'res_model': 'woo.commerce',
            'res_id': self.id,
            'domain': [],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'current',

        }

    @api.model
    def create(self, vals_list):
        """
        It checks all the connection validations.
        """
        set_wcapi = API(
            url="" + vals_list['store_url'] + "/index.php/wp-json/wc/v3/system_status?",  # Your store URL
            consumer_key=vals_list['consumer_key'],  # Your consumer key
            consumer_secret=vals_list['consumer_secret'],  # Your consumer secret
            wp_api=True,  # Enable the WP REST API integration
            version="wc/v3",  # WooCommerce WP REST API version
            timeout=500

        )
        validate = URLValidator()

        try:

            validate(set_wcapi.url)


        except ValidationError as exception:

            raise UserError(_("URL Doesn't Exist."))

        try:

            response = requests.get(set_wcapi.url)


        except requests.ConnectionError as exception:

            raise UserError(_("URL Doesn't Exist."))
        if set_wcapi.get("").status_code != 200:
            raise UserError(_("URL Doesn't Exist."))
        set_res = set_wcapi.get("").json()
        if set_res['settings']:
            currency = set_res['settings'].get('currency')
            vals_list['currency'] = currency
        return super(WooCommerceInstance, self).create(vals_list)
