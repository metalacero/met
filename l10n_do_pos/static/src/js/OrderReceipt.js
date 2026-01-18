odoo.define('l10n_do_pos.OrderReceipt', function (require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');

    const L10nDoPosOrderReceipt = OrderReceipt => class extends OrderReceipt {
        isSimple(line) {

            if (this.env.pos.config.l10n_do_fiscal_journal) {
                return false;
            }

            return super.isSimple(line);
        }

        mounted() {
            super.mounted();
            this._hideSaleOrderReferences();
        }

        updated() {
            super.updated();
            this._hideSaleOrderReferences();
        }

        _hideSaleOrderReferences() {
            var self = this;
            // Usar setTimeout para asegurar que el DOM esté completamente renderizado
            setTimeout(function () {
                if (!self.el) return;

                // Ocultar específicamente el elemento div.pos-receipt-left-padding que contiene "De S00118"
                const leftPaddingDivs = self.el.querySelectorAll('.pos-receipt-left-padding');
                leftPaddingDivs.forEach(function (div) {
                    const text = div.textContent || div.innerText || '';
                    if (text.trim().match(/^De\s+\w+/)) {
                        div.style.display = 'none';
                        div.style.visibility = 'hidden';
                        div.style.height = '0';
                        div.style.overflow = 'hidden';
                        div.style.margin = '0';
                        div.style.padding = '0';
                    }
                });

                // También buscar dentro de orderlines cualquier elemento que contenga "De "
                const orderlines = self.el.querySelectorAll('.orderlines > div');
                orderlines.forEach(function (lineDiv) {
                    // Buscar todos los elementos dentro de la línea
                    const allElements = lineDiv.querySelectorAll('*');
                    allElements.forEach(function (element) {
                        const text = element.textContent || element.innerText || '';
                        // Si el texto contiene "De " seguido de texto (como "De S00118")
                        if (text.trim().match(/^De\s+\w+/)) {
                            element.style.display = 'none';
                            element.style.visibility = 'hidden';
                            element.style.height = '0';
                            element.style.overflow = 'hidden';
                            element.style.margin = '0';
                            element.style.padding = '0';
                        }
                    });

                    // Buscar nodos de texto directamente
                    const walker = document.createTreeWalker(
                        lineDiv,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    let node;
                    while (node = walker.nextNode()) {
                        if (node.textContent && node.textContent.trim().match(/^De\s+\w+/)) {
                            if (node.parentElement) {
                                node.parentElement.style.display = 'none';
                            }
                        }
                    }
                });
            }, 200);

            // También usar MutationObserver para detectar cambios dinámicos
            if (!this._observer) {
                this._observer = new MutationObserver(function (mutations) {
                    self._hideSaleOrderReferences();
                });
                if (this.el) {
                    this._observer.observe(this.el, {
                        childList: true,
                        subtree: true,
                        characterData: true
                    });
                }
            }
        }
    }

    Registries.Component.extend(OrderReceipt, L10nDoPosOrderReceipt);

});
