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
    
   