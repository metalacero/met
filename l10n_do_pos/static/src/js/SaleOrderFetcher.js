odoo.define('l10n_do_pos.SaleOrderFetcher', function (require) {
    'use strict';

    const SaleOrderFetcher = require('pos_sale.SaleOrderFetcher');

    // Override to only show confirmed sale orders (state = 'sale'),
    // excluding quotations and cancelled orders.
    SaleOrderFetcher._getOrderIdsForCurrentPage = async function (limit, offset) {
        let domain = [
            ['currency_id', '=', this.comp.env.pos.currency.id],
            ['state', '=', 'sale'],
        ].concat(this.searchDomain || []);

        const saleOrders = await this.rpc({
            model: 'sale.order',
            method: 'search_read',
            args: [domain, this.orderFields, offset, limit],
            context: this.comp.env.session.user_context,
        });

        return saleOrders;
    };
});
