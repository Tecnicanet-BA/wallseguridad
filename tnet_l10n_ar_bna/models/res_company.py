# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo import exceptions, _
import requests
from lxml import etree
import datetime

import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    currency_provider = fields.Selection(selection_add=[('bna', 'Banco de la Nación Argentina')])
    l10n_ar_bna_rate_type = fields.Selection(selection=[('billete', 'Billete'), ('divisa', 'Divisa')],
                                             string='Rate',
                                             required=True,
                                             default='billete')
    l10n_ar_bna_currency_value = fields.Selection(selection=[('compra', 'Compra'),
                                                             ('venta', 'Venta'),
                                                             ('promedio', 'Promedio Compra-Venta')],
                                                  string='Value',
                                                  required=True,
                                                  default='venta')

    def _parse_bna_data(self, available_currencies):
        ''' Parses the data returned in text from BNA Website.'''
        def get_rates_from_table(currency_type, rows):
            for line in rows:
                rows = line.findall("./td")
                currency_read = rows[0].text.replace(' *', '')
                compra = float(rows[1].text.replace(',', '.'))
                venta = float(rows[2].text.replace(',', '.'))
                if currency_read not in values:
                    values[currency_read] = {'fecha': rate_date}

                values[currency_read]['%s_compra' % currency_type] = compra
                values[currency_read]['%s_venta' % currency_type] = venta
                
        bna_url = 'https://www.bna.com.ar'

        try:
            response = requests.get(bna_url, headers={
				'User-Agent': 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'
			})
            data = response.text
        except IOError:
            _logger.error('Error: Web Service BNA url does not exist or it is non accesible !')
            raise exceptions.AccessError(_('Error: Web Service [%s] does not exist or it is non accesible !') % bna_url)

        available_currency_names = available_currencies.mapped('name')
        today = fields.Date.context_today(self)

        _logger.debug("BNA currencies rate update service: connecting...")

        if not data:
            _logger.error('No data could be retrieved from BNA! Please check connection!')
            raise exceptions.AccessError(_('Error retrieving info from BNA. No data retrieved from %s') % bna_url)

        values = {}
        page = etree.HTML(data)

        divisas = page.find(".//div[@id='divisas']")
        if len(divisas) == 0:
            _logger.error('No "divisas" found! Bad site structure! Please check connection!')
            raise exceptions.AccessError(_('No "divisas" found! Bad site structure! Please check connection!'))

        fechaCot = divisas.find(".//th[@class='fechaCot']")
        dateStrParsed = fechaCot.text.split('/')
        rate_date = datetime.date(int(dateStrParsed[2]), int(dateStrParsed[1]), int(dateStrParsed[0]))

        #if rate_date == today:
            # Solo se leen cotizaciones del dia anterior o ultimo dia habil
            # Despues de las 15hs, aparecen las cotizaciones de cierre de hoy
            # que deben ser leidas a primera hora mañana
            #return

        get_rates_from_table('divisa', divisas.iterfind(".//tbody/tr"))

        billetes = page.find(".//div[@id='billetes']")
        if len(billetes) == 0:
            _logger.error('No "billetes" found! Bad site structure! Please check connection!')
            raise exceptions.AccessError(_('No "billetes" found! Bad site structure! Please check connection!'))

        fechaCot = billetes.find(".//th[@class='fechaCot']")
        dateStrParsed = fechaCot.text.split('/')
        rate_date = datetime.date(int(dateStrParsed[2]), int(dateStrParsed[1]), int(dateStrParsed[0]))

        get_rates_from_table('billete', billetes.iterfind(".//tbody/tr"))

        return values or False

    def _generate_currency_rates(self, parsed_data):
        """ Apply options for on bna rates """
        for company in self:
            if company.currency_provider == 'bna':
                bna_currencies_model = self.env['account.bna.currencies']

                if not company.currency_id.id == self.env.ref('base.ARS').id:
                    continue
                if not company.currency_id.rate == 1:
                    continue

                rate_type = company.l10n_ar_bna_rate_type
                currency_value = company.l10n_ar_bna_currency_value
                new_parsed_data = {}

                for currency_name, data in parsed_data.items():
                    bna_currency = bna_currencies_model.search([('name', '=', currency_name)], limit=1)
                    if not bna_currency:
                        _logger.info('%s not found in BNA Currencies!' % currency_name)
                        continue

                    # Skip if not active
                    if not bna_currency.currency_id.active:
                        _logger.info('Currency %s not active in the system!' % currency_name)
                        continue

                    if not bna_currency.with_company(company).property_read_rate:
                        _logger.info('Currency %s marked not to read in company %s!' % (currency_name, company.name))
                        continue

                    if currency_value == 'venta':
                        rate_value = data['billete_venta'] if rate_type == 'billete' else data['divisa_venta']
                    elif currency_value == 'compra':
                        rate_value = data['billete_compra'] if rate_type == 'billete' else data['divisa_compra']
                    else:
                        if rate_type == 'billete':
                            rate_value = (data['billete_venta'] + data['billete_compra']) / 2
                        else:
                            rate_value = (data['divisa_venta'] + data['divisa_compra']) / 2

                    if bna_currency.bna_units > 0:
                        new_parsed_data[bna_currency.currency_id.name] = (1 / (rate_value / bna_currency.bna_units), data['fecha'])

                new_parsed_data['ARS'] = (1.0, data['fecha'])
                super(ResCompany, company)._generate_currency_rates(new_parsed_data)
            else:
                super(ResCompany, company)._generate_currency_rates(parsed_data)
                
