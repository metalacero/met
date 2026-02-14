from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Campo relacionado del producto para controlar si el precio es modificable
    price_modifiable = fields.Boolean(
        related='product_id.price_modifiable',
        string='Precio Modificable',
        readonly=True,
        store=False
    )

    @api.model
    def _get_product_domain(self):
        """Filtrar productos restringidos en las líneas de venta"""
        domain = []
        user = self.env.user
        
        # if user is not admin, filter restricted products
        if not user.has_group('base.group_system'):
            domain = [
                '|',
                ('is_restricted_user', '=', False),
                '|',
                ('restricted_user_id', '=', False),
                ('restricted_user_id', '=', user.id)
            ]
        
        return domain
    
    def read(self, fields=None, load='_classic_read'):
        """
        Override read para ocultar información sobre move_ids cuando se llama desde el POS
        Esto previene que el POS divida las líneas basándose en movimientos de stock
        """
        # Verificar si se está llamando desde el POS
        is_pos_context = False
        try:
            pos_session = self.env['pos.session'].sudo().search([
                ('user_id', '=', self.env.uid),
                ('state', '=', 'opened')
            ], limit=1)
            is_pos_context = bool(pos_session)
        except Exception:
            pass
        
        # Llamar al método base
        result = super(SaleOrderLine, self).read(fields=fields, load=load)
        
        # Asegurar que result sea válido
        if result is None:
            result = [] if fields else {}
        
        # Si se llama desde el POS, ocultar o limpiar move_ids para evitar división de líneas
        if is_pos_context:
            if isinstance(result, list):
                for record in result:
                    if isinstance(record, dict) and 'move_ids' in record:
                        # Limpiar move_ids para evitar que el POS divida las líneas
                        record['move_ids'] = []
                        _logger.debug('move_ids limpiado para línea %s cuando se lee desde POS', record.get('id'))
            elif isinstance(result, dict) and 'move_ids' in result:
                result['move_ids'] = []
                _logger.debug('move_ids limpiado para línea %s cuando se lee desde POS', result.get('id'))
        
        return result

    def read_converted(self):
        """
        # Override to allow the POS to display the correct quantities
        # when fetching orders that have already been delivered (pickings in 'done').
        #
        # When the picking is in 'done', qty_delivered = product_uom_qty,
        # so qty_to_invoice = 0. But the POS needs to display the original
        # quantity (product_uom_qty) so it can invoice the correct amount.
        #
        # También consolida líneas divididas: cuando el método base divide una línea
        # de venta en múltiples líneas del POS (por ejemplo, por entregas parciales),
        # las consolida en una sola línea con la cantidad total.
        """
        _logger.info('read_converted called for %s sale lines', len(self))
        
        # Log de las líneas de venta originales
        # Verificar si hay múltiples líneas del mismo producto
        lines_by_product = {}
        for sale_line in self:
            if sale_line.product_id:
                product_id = sale_line.product_id.id
                if product_id not in lines_by_product:
                    lines_by_product[product_id] = []
                lines_by_product[product_id].append(sale_line.id)
            
            _logger.info(
                'Línea de venta original: ID=%s, Producto=%s, Cantidad=%s, Precio=%s',
                sale_line.id,
                sale_line.product_id.display_name if sale_line.product_id else 'N/A',
                sale_line.product_uom_qty,
                sale_line.price_unit
            )
        
        # Log si hay productos duplicados
        for product_id, line_ids in lines_by_product.items():
            if len(line_ids) > 1:
                _logger.warning(
                    'Múltiples líneas del mismo producto %s detectadas: %s líneas (IDs: %s)',
                    product_id, len(line_ids), line_ids
                )
        
        # Call the base method
        results = super(SaleOrderLine, self).read_converted()
        
        # Asegurar que results sea siempre una lista
        if results is None:
            results = []
        elif not isinstance(results, list):
            results = [results] if results else []
        
        _logger.info('read_converted base returned %s results (esperábamos %s líneas)', len(results), len(self))
        
        # Log detallado de todos los resultados del método base
        for idx, result in enumerate(results):
            # Extraer información del ID (puede ser lista, tupla o entero)
            result_id = result.get('id')
            id_str = str(result_id)
            if isinstance(result_id, (list, tuple)) and len(result_id) > 1:
                id_str = f"{result_id[0]} (con {len(result_id)-1} elementos adicionales)"
            
            _logger.info(
                'Resultado %s del método base: id=%s, product_id=%s, price_unit=%s, qty_to_invoice=%s, product_uom_qty=%s, qty_delivered=%s, qty_invoiced=%s',
                idx, id_str, result.get('product_id'), result.get('price_unit'),
                result.get('qty_to_invoice', 0), result.get('product_uom_qty', 0),
                result.get('qty_delivered', 0), result.get('qty_invoiced', 0)
            )
            
            # Log de TODOS los campos del resultado para identificar qué puede causar división
            _logger.info('  - Todos los campos del resultado: %s', list(result.keys()))
            
            # Log de TODOS los valores del resultado para debugging completo
            _logger.info('  - Valores completos del resultado: %s', result)
            
            # Log de campos específicos que puedan causar división
            for field in ['move_ids', 'lot_id', 'lot_ids', 'package_id', 'package_ids', 
                          'serial_number', 'serial_numbers', 'tracking_number', 'move_line_ids',
                          'stock_move_ids', 'picking_ids', 'move_line_count', 'stock_move_count',
                          'move_line_ids_without_package', 'move_line_nosuggest_ids', 'move_line_ids_without_package']:
                if field in result:
                    _logger.info('  - %s: %s', field, result.get(field))
        
        # Si el número de resultados es mayor que el número de líneas de venta,
        # significa que algunas líneas fueron divididas
        if len(results) > len(self):
            _logger.warning(
                'El método base dividió las líneas: %s resultados para %s líneas de venta',
                len(results), len(self)
            )
        
        # ESTRATEGIA MEJORADA: Agrupar TODAS las líneas SOLO por producto (sin considerar precio)
        # Esto asegura que todas las líneas del mismo producto se consoliden en una sola línea
        # independientemente de si vienen de diferentes líneas de venta o tienen diferentes precios
        
        # Agrupar TODOS los resultados SOLO por producto_id (más agresivo)
        # IMPORTANTE: Agrupar por producto_id solamente, sin considerar precio
        results_by_product_id = {}
        
        for idx, result in enumerate(results):
            product_id = result.get('product_id')
            
            # Extraer el ID del producto (puede ser una lista o un entero)
            if isinstance(product_id, list) and len(product_id) > 0:
                product_id = product_id[0]
            elif isinstance(product_id, tuple) and len(product_id) > 0:
                product_id = product_id[0]
            
            # Si no hay product_id, intentar obtenerlo del ID de la línea de venta
            if product_id is None:
                result_id = result.get('id')
                if isinstance(result_id, (list, tuple)) and len(result_id) > 0:
                    result_id = result_id[0]
                elif isinstance(result_id, (int, float)):
                    result_id = int(result_id)
                else:
                    result_id = None
                
                # Si tenemos un ID de línea, buscar el producto desde la línea de venta
                if result_id and result_id in self.ids:
                    sale_line = self.browse(result_id)
                    if sale_line.exists() and sale_line.product_id:
                        product_id = sale_line.product_id.id
                        _logger.info('Producto obtenido desde línea de venta %s: %s', result_id, product_id)
            
            # Si aún no hay product_id, usar None como clave
            if product_id is None:
                product_id = None
            
            # Agrupar SOLO por producto_id, sin considerar precio ni ID de línea
            if product_id not in results_by_product_id:
                results_by_product_id[product_id] = []
            results_by_product_id[product_id].append(result)
            
            _logger.info(
                'Agrupado resultado %s: producto_id=%s, price_unit=%s, qty=%s, id=%s',
                idx, product_id, result.get('price_unit', 0), result.get('qty_to_invoice', 0), result.get('id')
            )
        
        # Crear un mapa de líneas de venta por producto_id para referencia
        # IMPORTANTE: Si hay múltiples líneas del mismo producto, sumar sus cantidades
        # y usar solo la primera línea como base
        sale_lines_by_product_id = {}
        sale_lines_qty_by_product_id = {}
        for sale_line in self:
            product_id = sale_line.product_id.id if sale_line.product_id else None
            # Solo guardar la primera línea de venta para cada producto
            # Esto asegura que todas las líneas del mismo producto usen el mismo ID
            if product_id not in sale_lines_by_product_id:
                sale_lines_by_product_id[product_id] = sale_line
                sale_lines_qty_by_product_id[product_id] = sale_line.product_uom_qty
            else:
                # Si ya existe, sumar la cantidad
                sale_lines_qty_by_product_id[product_id] += sale_line.product_uom_qty
                _logger.info(
                    'Sumando cantidad de línea %s al producto %s: cantidad total=%s',
                    sale_line.id, product_id, sale_lines_qty_by_product_id[product_id]
                )
        
        # Inicializar lista de resultados consolidados
        # Asegurar que siempre sea una lista válida
        consolidated_results = []
        if not isinstance(consolidated_results, list):
            consolidated_results = []
        
        # Procesar cada grupo de resultados agrupados por producto
        for product_id, grouped_results in results_by_product_id.items():
            # Asegurar que grouped_results sea una lista válida
            if not isinstance(grouped_results, list):
                _logger.warning('grouped_results no es una lista para producto %s: %s', product_id, type(grouped_results))
                continue
            if len(grouped_results) == 0:
                _logger.warning('grouped_results vacío para producto %s', product_id)
                continue
            
            # Buscar la primera línea de venta que coincida con este producto
            matching_sale_line = None
            if product_id in sale_lines_by_product_id:
                matching_sale_line = sale_lines_by_product_id[product_id]
            else:
                # Si no hay coincidencia, intentar usar el ID del primer resultado
                first_result = grouped_results[0]
                if not isinstance(first_result, dict):
                    _logger.warning('Primer resultado no es un diccionario para producto %s', product_id)
                    continue
                result_id = first_result.get('id')
                sale_line_id = None
                
                if isinstance(result_id, list) and len(result_id) > 0:
                    sale_line_id = result_id[0]
                elif isinstance(result_id, tuple) and len(result_id) > 0:
                    sale_line_id = result_id[0]
                elif isinstance(result_id, (int, float)):
                    sale_line_id = int(result_id)
                
                if sale_line_id and sale_line_id in self.ids:
                    matching_sale_line = self.browse(sale_line_id)
            
            # SIEMPRE consolidar si hay más de un resultado para el mismo producto
            # Incluso si solo hay uno, asegurarse de que el ID sea consistente
            if matching_sale_line and matching_sale_line.exists():
                # Si hay múltiples líneas de venta del mismo producto, usar la cantidad total
                total_qty_from_sale_lines = sale_lines_qty_by_product_id.get(product_id, matching_sale_line.product_uom_qty)
                
                if len(grouped_results) == 1:
                    # Solo hay un resultado, pero puede haber múltiples líneas de venta
                    result = grouped_results[0]
                    result = self._process_single_result(matching_sale_line, result)
                    # Si hay múltiples líneas de venta del mismo producto, usar la cantidad total
                    if total_qty_from_sale_lines != matching_sale_line.product_uom_qty:
                        _logger.info(
                            'Ajustando cantidad de %s a %s para consolidar múltiples líneas de venta del producto %s',
                            result.get('product_uom_qty', 0), total_qty_from_sale_lines, product_id
                        )
                        result['product_uom_qty'] = total_qty_from_sale_lines
                        result['qty_to_invoice'] = total_qty_from_sale_lines
                    # Asegurar que el ID sea el de la línea de venta para consistencia
                    result['id'] = matching_sale_line.id
                    consolidated_results.append(result)
                else:
                    # Hay múltiples líneas para el mismo producto - consolidarlas TODAS
                    _logger.info(
                        'Consolidando %s líneas para producto %s (ID línea de venta: %s, Producto: %s)',
                        len(grouped_results), product_id, matching_sale_line.id,
                        matching_sale_line.product_id.display_name if matching_sale_line.product_id else 'N/A'
                    )
                    # Log detallado de las líneas a consolidar
                    for i, r in enumerate(grouped_results):
                        result_id = r.get('id')
                        if isinstance(result_id, (list, tuple)) and len(result_id) > 0:
                            result_id = result_id[0]
                        _logger.info(
                            '  Línea %s: qty_to_invoice=%s, product_uom_qty=%s, qty_delivered=%s, price_unit=%s, id=%s',
                            i+1, r.get('qty_to_invoice', 0), r.get('product_uom_qty', 0), 
                            r.get('qty_delivered', 0), r.get('price_unit', 0), result_id
                        )
                    consolidated_result = self._consolidate_split_lines(matching_sale_line, grouped_results)
                    # Asegurar que el ID sea siempre el de la línea de venta para evitar duplicados
                    consolidated_result['id'] = matching_sale_line.id
                    consolidated_results.append(consolidated_result)
            else:
                # Si no podemos encontrar una línea de venta, intentar consolidar de todas formas
                if len(grouped_results) > 1:
                    _logger.warning(
                        'No se encontró línea de venta para producto %s, pero hay %s resultados. Intentando consolidar...',
                        product_id, len(grouped_results)
                    )
                    # Usar el primer resultado como base y consolidar
                    consolidated_result = self._consolidate_split_lines_by_results(grouped_results)
                    consolidated_results.append(consolidated_result)
                else:
                    # Solo hay un resultado y no hay línea de venta, mantenerlo tal cual
                    _logger.warning(
                        'No se encontró línea de venta para producto %s, manteniendo resultado sin agrupar',
                        product_id
                    )
                    # Asegurar que grouped_results sea una lista válida antes de extender
                    if isinstance(grouped_results, list):
                        consolidated_results.extend(grouped_results)
                    else:
                        _logger.warning('grouped_results no es una lista: %s', type(grouped_results))
                        if grouped_results:
                            consolidated_results.append(grouped_results)
        
        # Asegurar que todos los resultados sean diccionarios válidos y no None
        final_results = []
        for result in consolidated_results:
            if result is not None and isinstance(result, dict):
                # Asegurar que todos los campos requeridos existan
                if 'id' not in result or result.get('id') is None:
                    _logger.warning('Resultado sin ID válido, omitiendo: %s', result)
                    continue
                final_results.append(result)
            else:
                _logger.warning('Resultado inválido omitido: %s (tipo: %s)', result, type(result))
        
        _logger.info(
            'read_converted final: %s resultados consolidados válidos (de %s originales)', 
            len(final_results), len(results)
        )
        
        # Log detallado de cada resultado final para debugging
        for idx, final_result in enumerate(final_results):
            _logger.info(
                'Resultado final %s: id=%s, product_id=%s, quantity=%s, product_uom_qty=%s, qty_to_invoice=%s, price_unit=%s, move_ids=%s',
                idx + 1,
                final_result.get('id'),
                final_result.get('product_id'),
                final_result.get('quantity'),
                final_result.get('product_uom_qty'),
                final_result.get('qty_to_invoice'),
                final_result.get('price_unit'),
                final_result.get('move_ids', 'NO PRESENTE')
            )
            # Log completo del resultado para debugging
            _logger.info('  - Resultado completo JSON: %s', final_result)
        
        # Asegurar que siempre devolvamos una lista, nunca None
        return final_results if final_results else []
    
    def _consolidate_split_lines_by_results(self, grouped_results):
        """
        Consolida múltiples resultados cuando no hay una línea de venta disponible
        """
        consolidated = grouped_results[0].copy()
        
        # Sumar las cantidades
        total_qty_to_invoice = sum(r.get('qty_to_invoice', 0) for r in grouped_results)
        total_product_uom_qty = sum(r.get('product_uom_qty', 0) for r in grouped_results)
        
        # Calcular precio promedio ponderado
        prices = [r.get('price_unit', 0) for r in grouped_results]
        unique_prices = set(round(float(p), 2) for p in prices if p)
        
        if len(unique_prices) == 1:
            consolidated['price_unit'] = prices[0]
        elif len(unique_prices) > 1:
            total_amount = sum(r.get('qty_to_invoice', 0) * r.get('price_unit', 0) for r in grouped_results)
            if total_qty_to_invoice > 0:
                consolidated['price_unit'] = total_amount / total_qty_to_invoice
            else:
                consolidated['price_unit'] = prices[0]
        
        consolidated['qty_to_invoice'] = total_qty_to_invoice
        consolidated['product_uom_qty'] = total_product_uom_qty
        
        # Limpiar campos que pueden causar división
        fields_to_clean = [
            'lot_id', 'lot_ids', 'package_id', 'package_ids', 
            'serial_number', 'serial_numbers', 'tracking_number',
            'move_ids', 'move_line_ids', 'stock_move_ids', 'picking_ids',
            'stock_quant_ids', 'reserved_availability', 'free_qty'
        ]
        for field in fields_to_clean:
            if field in consolidated:
                consolidated.pop(field, None)
        
        # Usar el ID del primer resultado
        result_id = consolidated.get('id')
        if isinstance(result_id, (list, tuple)) and len(result_id) > 0:
            consolidated['id'] = result_id[0]
        elif not isinstance(result_id, (int, float)):
            consolidated['id'] = grouped_results[0].get('id')
        
        return consolidated
    
    def _process_single_result(self, sale_line, result):
        """Procesa un resultado único para una línea de venta"""
        
        # IMPORTANTE: Limpiar TODOS los campos relacionados con movimientos/stock ANTES de cualquier procesamiento
        # El POS puede usar estos campos para dividir líneas, incluso si no hay pickings en 'done'
        fields_to_remove = [
            'move_ids', 'move_line_ids', 'stock_move_ids', 'picking_ids',
            'lot_id', 'lot_ids', 'package_id', 'package_ids',
            'serial_number', 'serial_numbers', 'tracking_number',
            'stock_quant_ids', 'reserved_availability', 'free_qty',
            'move_line_count', 'stock_move_count', 'picking_count',
            'procurement_ids', 'orderpoint_ids', 'route_id', 'route_ids',
            'warehouse_id', 'location_id', 'location_dest_id',
            'move_line_ids_without_package', 'move_line_nosuggest_ids',
            'move_line_ids_without_package', 'move_line_ids_without_package',
            'move_line_ids_without_package', 'move_line_ids_without_package'
        ]
        for field in fields_to_remove:
            if field in result:
                _logger.debug('Limpiando campo %s del resultado para evitar división en POS', field)
                result.pop(field, None)
        
        # Asegurar que el ID sea siempre el de la línea de venta desde el inicio
        result['id'] = sale_line.id
        
        # Log de información sobre movimientos de stock
        if sale_line.move_ids:
            moves_count = len(sale_line.move_ids)
            _logger.info(
                'Línea de venta %s (ID: %s) tiene %s movimientos de stock',
                sale_line.display_name, sale_line.id, moves_count
            )
            
            pickings = sale_line.move_ids.mapped('picking_id')
            done_pickings = pickings.filtered(lambda p: p.state == 'done')
            
            if done_pickings:
                # When the picking is in 'done', qty_to_invoice may be 0
                # but we need to show the original quantity so the POS can charge
                current_qty_to_invoice = result.get('qty_to_invoice', 0)
                current_product_uom_qty = result.get('product_uom_qty', 0)
                
                _logger.info(
                    'Línea de venta %s (ID: %s) tiene picking en "done". '
                    'Valores actuales: qty_to_invoice=%s, product_uom_qty=%s, '
                    'qty_delivered=%s, qty_invoiced=%s, product_uom_qty (campo)=%s',
                    sale_line.display_name, sale_line.id, current_qty_to_invoice, current_product_uom_qty,
                    sale_line.qty_delivered, sale_line.qty_invoiced, sale_line.product_uom_qty
                )
                
                # When the picking is in 'done', ALWAYS use product_uom_qty as the available quantity
                # to charge, regardless of qty_to_invoice, because the POS should only charge
                # and the inventory has already been processed
                if sale_line.product_uom_qty > 0:
                    # Use product_uom_qty as the available quantity to charge
                    original_qty = sale_line.product_uom_qty
                    
                    # Convert the quantity if necessary using the pos_sale method
                    # The _convert_qty method is in the pos_sale module and is @api.model
                    if sale_line.product_id.uom_id != sale_line.product_uom:
                        # Use the _convert_qty method of the model (inherited from pos_sale)
                        if hasattr(self, '_convert_qty'):
                            original_qty = self._convert_qty(sale_line, original_qty, 's2p')
                        else:
                            # If not available, convert manually
                            original_qty = sale_line.product_uom._compute_quantity(
                                original_qty, sale_line.product_id.uom_id, False
                            )
                    
                    # ALWAYS update qty_to_invoice and product_uom_qty when there are pickings in 'done'
                    # to ensure the POS displays the correct quantity
                    # IMPORTANT: Also adjust qty_delivered to 0 for the JavaScript calculation to work:
                    # quantity = product_uom_qty - Math.max(qty_delivered, qty_invoiced)
                    # If qty_delivered = product_uom_qty, then quantity = 0
                    # So we put qty_delivered = 0 when the picking is in 'done'
                    result['qty_to_invoice'] = original_qty
                    result['product_uom_qty'] = original_qty
                    result['qty_delivered'] = 0  # Adjust to 0 for the JavaScript calculation to work
                    result['qty_invoiced'] = 0  # También asegurar que qty_invoiced sea 0
                    
                    # Los campos ya fueron limpiados al inicio del método
                    
                    _logger.info(
                        'Picking in "done" detected. Adjusting qty_to_invoice from %s to %s, product_uom_qty to %s, qty_delivered to 0, qty_invoiced to 0 to allow POS charging.',
                        current_qty_to_invoice, original_qty, original_qty
                    )
        
        # IMPORTANTE: Asegurar que el ID sea siempre un entero simple, no una tupla o lista
        # El POS puede interpretar IDs complejos como múltiples líneas
        # SIEMPRE usar el ID de la línea de venta para garantizar consistencia
        result['id'] = sale_line.id
        _logger.debug('  - ID establecido a %s (línea de venta) para evitar división en POS', sale_line.id)
        
        # IMPORTANTE: Asegurar que la cantidad disponible para el POS sea la cantidad total
        # El POS calcula: quantity = product_uom_qty - Math.max(qty_delivered, qty_invoiced)
        # Ya hemos puesto qty_delivered=0 y qty_invoiced=0, así que quantity debería ser product_uom_qty
        # Pero por si acaso, también podemos asegurar que product_uom_qty tenga el valor correcto
        if result.get('product_uom_qty', 0) != sale_line.product_uom_qty:
            _logger.info(
                '  - Ajustando product_uom_qty de %s a %s para asegurar cantidad correcta',
                result.get('product_uom_qty', 0), sale_line.product_uom_qty
            )
            result['product_uom_qty'] = sale_line.product_uom_qty
        
        # Asegurar que qty_to_invoice también tenga el valor correcto
        if result.get('qty_to_invoice', 0) != sale_line.product_uom_qty:
            _logger.info(
                '  - Ajustando qty_to_invoice de %s a %s para asegurar cantidad correcta',
                result.get('qty_to_invoice', 0), sale_line.product_uom_qty
            )
            result['qty_to_invoice'] = sale_line.product_uom_qty
        
        # CRÍTICO: Asegurar que qty_delivered y qty_invoiced sean siempre 0
        # El POS calcula: quantity = product_uom_qty - Math.max(qty_delivered, qty_invoiced)
        # Si estos valores no son 0, el POS puede dividir la línea
        result['qty_delivered'] = 0
        result['qty_invoiced'] = 0
        
        # Asegurar que price_total se calcule correctamente con la cantidad total
        if 'price_total' in result:
            # Recalcular price_total basándose en la cantidad total
            price_subtotal = result.get('product_uom_qty', 0) * result.get('price_unit', 0)
            # Aplicar descuento si existe
            discount = result.get('discount', 0)
            if discount:
                price_subtotal = price_subtotal * (1 - discount / 100)
            # Aplicar impuestos si existen
            tax_id = result.get('tax_id', [])
            if tax_id and isinstance(tax_id, list) and len(tax_id) > 0:
                # Simplificar: usar el precio subtotal * 1.18 (asumiendo ITBIS del 18%)
                # O mejor, mantener el price_total original pero asegurar que sea consistente
                pass
            result['price_total'] = result.get('price_total', price_subtotal)
        
        # Limpiar cualquier campo adicional que pueda causar problemas
        # Asegurar que no haya campos que indiquen múltiples líneas o entregas parciales
        additional_fields_to_remove = [
            'invoice_lines', 'invoice_status', 'invoice_count',
            'picking_ids', 'delivery_count', 'procurement_group_id'
        ]
        for field in additional_fields_to_remove:
            if field in result:
                result.pop(field, None)
        
        # CRÍTICO: Agregar un campo especial para indicar al POS que NO divida esta línea
        # El POS puede estar dividiendo basándose en algún campo que no podemos controlar
        # Agregamos un campo que indique explícitamente que esta es una línea consolidada
        result['_pos_consolidated'] = True
        result['_pos_do_not_split'] = True
        
        # Asegurar que el campo 'quantity' (si existe) también tenga el valor correcto
        # El POS puede estar usando este campo en lugar de product_uom_qty
        if 'quantity' not in result:
            result['quantity'] = result.get('product_uom_qty', sale_line.product_uom_qty)
        else:
            result['quantity'] = result.get('product_uom_qty', sale_line.product_uom_qty)
        
        _logger.info(
            '  - Resultado final procesado: id=%s, qty_to_invoice=%s, product_uom_qty=%s, qty_delivered=%s, qty_invoiced=%s, price_total=%s, quantity=%s',
            result.get('id'), result.get('qty_to_invoice', 0), result.get('product_uom_qty', 0),
            result.get('qty_delivered', 0), result.get('qty_invoiced', 0), result.get('price_total', 0),
            result.get('quantity', 0)
        )
        
        # Log de TODOS los campos del resultado para identificar qué puede causar división
        _logger.info('  - TODOS los campos del resultado final: %s', list(result.keys()))
        
        # Verificar campos específicos que pueden causar división
        problematic_fields = ['move_ids', 'move_line_ids', 'lot_id', 'package_id', 'serial_number']
        for field in problematic_fields:
            if field in result:
                _logger.warning('  - ⚠️ Campo problemático encontrado: %s = %s', field, result.get(field))
        
        return result
    
    def _consolidate_split_lines(self, sale_line, grouped_results):
        """
        Consolida múltiples líneas del POS que provienen del mismo producto
        en una sola línea con la cantidad total
        """
        # Usar el primer resultado como base
        consolidated = grouped_results[0].copy()
        
        # Sumar las cantidades de todas las líneas divididas
        total_qty_to_invoice = sum(r.get('qty_to_invoice', 0) for r in grouped_results)
        total_product_uom_qty = sum(r.get('product_uom_qty', 0) for r in grouped_results)
        total_qty_delivered = sum(r.get('qty_delivered', 0) for r in grouped_results)
        total_qty_invoiced = sum(r.get('qty_invoiced', 0) for r in grouped_results)
        
        # Calcular precio promedio ponderado si hay diferentes precios
        # Si todos tienen el mismo precio, usar ese precio
        prices = [r.get('price_unit', 0) for r in grouped_results]
        unique_prices = set(round(float(p), 2) for p in prices if p)
        
        if len(unique_prices) == 1:
            # Todos tienen el mismo precio, usar ese precio
            consolidated['price_unit'] = prices[0]
        elif len(unique_prices) > 1:
            # Hay diferentes precios, calcular promedio ponderado por cantidad
            total_amount = sum(r.get('qty_to_invoice', 0) * r.get('price_unit', 0) for r in grouped_results)
            if total_qty_to_invoice > 0:
                consolidated['price_unit'] = total_amount / total_qty_to_invoice
            else:
                consolidated['price_unit'] = prices[0]  # Fallback al primer precio
            _logger.info(
                'Múltiples precios detectados para producto %s, usando precio promedio ponderado: %s',
                sale_line.product_id.display_name if sale_line.product_id else 'N/A',
                consolidated['price_unit']
            )
        
        # Limpiar TODOS los campos relacionados con movimientos/stock/números de serie/lotes
        # que pueden causar problemas cuando se consolidan múltiples líneas o cuando el POS los procesa
        fields_to_clean = [
            'lot_id', 'lot_ids', 'package_id', 'package_ids', 
            'serial_number', 'serial_numbers', 'tracking_number',
            'move_ids', 'move_line_ids', 'stock_move_ids', 'picking_ids',
            'stock_quant_ids', 'reserved_availability', 'free_qty'
        ]
        for field in fields_to_clean:
            if field in consolidated:
                # Limpiar estos campos para evitar que el POS los use para dividir líneas
                consolidated.pop(field, None)
                _logger.info('Campo %s eliminado de línea consolidada para evitar división en POS', field)
        
        # Asegurar que el ID sea el de la línea de venta original
        # El ID puede estar en formato lista o tupla, asegurarse de que sea el ID correcto
        if isinstance(consolidated.get('id'), (list, tuple)):
            consolidated['id'] = sale_line.id
        else:
            consolidated['id'] = sale_line.id
        
        # Si hay pickings en 'done', usar la cantidad original de la línea de venta
        if sale_line.move_ids:
            pickings = sale_line.move_ids.mapped('picking_id')
            done_pickings = pickings.filtered(lambda p: p.state == 'done')
            
            if done_pickings and sale_line.product_uom_qty > 0:
                # Cuando el picking está en 'done', usar la cantidad original
                original_qty = sale_line.product_uom_qty
                
                # Convertir la cantidad si es necesario
                if sale_line.product_id.uom_id != sale_line.product_uom:
                    if hasattr(self, '_convert_qty'):
                        original_qty = self._convert_qty(sale_line, original_qty, 's2p')
                    else:
                        original_qty = sale_line.product_uom._compute_quantity(
                            original_qty, sale_line.product_id.uom_id, False
                        )
                
                consolidated['qty_to_invoice'] = original_qty
                consolidated['product_uom_qty'] = original_qty
                consolidated['qty_delivered'] = 0
                _logger.info(
                    'Usando cantidad original de línea de venta (picking en "done"): %s',
                    original_qty
                )
            else:
                # Si no hay pickings en 'done', usar las cantidades consolidadas
                consolidated['qty_to_invoice'] = total_qty_to_invoice
                consolidated['product_uom_qty'] = total_product_uom_qty
                consolidated['qty_delivered'] = total_qty_delivered
                consolidated['qty_invoiced'] = total_qty_invoiced
                _logger.info(
                    'Usando cantidades consolidadas: qty_to_invoice=%s, product_uom_qty=%s',
                    total_qty_to_invoice, total_product_uom_qty
                )
        else:
            # Si no hay movimientos, usar las cantidades consolidadas
            consolidated['qty_to_invoice'] = total_qty_to_invoice
            consolidated['product_uom_qty'] = total_product_uom_qty
            consolidated['qty_delivered'] = total_qty_delivered
            consolidated['qty_invoiced'] = total_qty_invoiced
            _logger.info(
                'Sin movimientos, usando cantidades consolidadas: qty_to_invoice=%s, product_uom_qty=%s',
                total_qty_to_invoice, total_product_uom_qty
            )
        
        _logger.info(
            'Líneas consolidadas para línea de venta %s (ID: %s): '
            'qty_to_invoice=%s, product_uom_qty=%s, qty_delivered=%s (de %s líneas)',
            sale_line.display_name, sale_line.id,
            consolidated.get('qty_to_invoice', 0),
            consolidated.get('product_uom_qty', 0),
            consolidated.get('qty_delivered', 0),
            len(grouped_results)
        )
        
        return consolidated
