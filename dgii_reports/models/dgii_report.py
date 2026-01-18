# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class DgiiReport(models.Model):
    _name = 'dgii.report'
    _description = 'DGII Report (606 & 607)'
    _order = 'date_to desc, id desc'

    name = fields.Char(string='Nombre', required=True, default='Nuevo Reporte')
    report_type = fields.Selection([
        ('606', 'Reporte 606 - Compras'),
        ('607', 'Reporte 607 - Ventas'),
    ], string='Tipo de Reporte', required=True)
    date_from = fields.Date(string='Fecha Desde', required=True)
    date_to = fields.Date(string='Fecha Hasta', required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('generated', 'Generado'),
        ('sent', 'Enviado'),
    ], string='Estado', default='draft', readonly=False)
    company_id = fields.Many2one('res.company', string='Compañía', 
                                 default=lambda self: self.env.company, required=True)
    
    line_ids = fields.One2many('dgii.report.line', 'report_id', string='Líneas del Reporte')
    line_count = fields.Integer(string='Número de Líneas', compute='_compute_line_count')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for report in self:
            report.line_count = len(report.line_ids)
    
    @api.model
    def load_views(self, views, options=None):
        """Sobrescribe load_views para cambiar la vista tree de line_ids según el tipo de reporte"""
        res = super().load_views(views, options or {})
        
        # Obtener el tipo de reporte del contexto o del registro actual
        report_type = self.env.context.get('default_report_type')
        
        # Si hay un ID en el contexto, intentar obtener el tipo de reporte del registro
        if not report_type:
            active_id = (self.env.context.get('active_id') or 
                        self.env.context.get('res_id') or
                        self.env.context.get('id'))
            if active_id:
                try:
                    record = self.browse(active_id)
                    if record.exists() and record.report_type:
                        report_type = record.report_type
                except:
                    pass
        
        # También intentar obtener desde options
        if not report_type and options:
            res_id = options.get('res_id') or options.get('active_id')
            if res_id:
                try:
                    record = self.browse(res_id)
                    if record.exists() and record.report_type:
                        report_type = record.report_type
                except:
                    pass
        
        # Si encontramos el tipo de reporte y hay una vista form, modificar la vista tree
        if report_type and 'form' in res.get('views', {}):
            try:
                form_view = res['views']['form']
                arch = form_view.get('arch', '')
                if arch and '<field name="line_ids"' in arch:
                    # Buscar la vista específica según el tipo de reporte
                    if report_type == '606':
                        tree_view = self.env.ref('dgii_reports.view_dgii_report_line_tree_606', raise_if_not_found=False)
                    elif report_type == '607':
                        tree_view = self.env.ref('dgii_reports.view_dgii_report_line_tree_607', raise_if_not_found=False)
                    else:
                        tree_view = None
                    
                    if tree_view and tree_view.arch:
                        import lxml.etree as ET
                        arch_tree = ET.fromstring(arch)
                        line_ids_field = arch_tree.xpath("//field[@name='line_ids']")
                        if line_ids_field:
                            # Obtener la vista tree específica
                            tree_arch = ET.fromstring(tree_view.arch)
                            tree_content = tree_arch.find('tree')
                            if tree_content is not None:
                                # Limpiar el contenido actual del campo (incluyendo cualquier tree existente)
                                for child in list(line_ids_field[0]):
                                    line_ids_field[0].remove(child)
                                # Crear un nuevo elemento tree
                                new_tree = ET.Element('tree')
                                if 'string' in tree_content.attrib:
                                    new_tree.set('string', tree_content.attrib['string'])
                                if 'default_order' in tree_content.attrib:
                                    new_tree.set('default_order', tree_content.attrib['default_order'])
                                # Agregar todos los campos del tree específico
                                for child in tree_content:
                                    new_tree.append(child)
                                # Agregar el nuevo tree al campo line_ids
                                line_ids_field[0].append(new_tree)
                                form_view['arch'] = ET.tostring(arch_tree, encoding='unicode')
                                
                                # También actualizar el contexto para que las líneas sepan el tipo de reporte
                                if 'context' not in form_view:
                                    form_view['context'] = {}
                                if isinstance(form_view['context'], str):
                                    # Si es string, convertirlo a dict
                                    import ast
                                    try:
                                        form_view['context'] = ast.literal_eval(form_view['context'])
                                    except:
                                        form_view['context'] = {}
                                form_view['context']['default_report_type'] = report_type
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning("Error al modificar vista tree en load_views para reporte %s: %s", report_type, str(e))
        
        return res
    
    def _get_view(self, view_id=None, view_type='form', **options):
        """Sobrescribe para cambiar la vista tree de line_ids según el tipo de reporte"""
        res = super()._get_view(view_id=view_id, view_type=view_type, **options)
        
        if view_type == 'form':
            # Obtener el tipo de reporte del contexto o del registro actual
            report_type = self.env.context.get('default_report_type')
            
            # Si hay un ID en el contexto, intentar obtener el tipo de reporte del registro
            if not report_type:
                # Intentar obtener el ID desde diferentes lugares del contexto
                active_id = (self.env.context.get('active_id') or 
                            self.env.context.get('res_id') or
                            self.env.context.get('id'))
                if active_id:
                    try:
                        record = self.browse(active_id)
                        if record.exists() and record.report_type:
                            report_type = record.report_type
                    except:
                        pass
            
            # Si aún no tenemos el tipo y estamos en un recordset, obtenerlo directamente
            if not report_type and self:
                try:
                    if len(self) == 1 and self.report_type:
                        report_type = self.report_type
                    elif len(self) > 1:
                        # Si hay múltiples registros, tomar el primero
                        report_type = self[0].report_type
                except:
                    pass
            
            # Si aún no tenemos el tipo, intentar obtenerlo desde options si está disponible
            if not report_type and options.get('res_id'):
                try:
                    record = self.browse(options['res_id'])
                    if record.exists() and record.report_type:
                        report_type = record.report_type
                except:
                    pass
            
            # Buscar la vista específica según el tipo de reporte
            tree_view = None
            if report_type == '606':
                tree_view = self.env.ref('dgii_reports.view_dgii_report_line_tree_606', raise_if_not_found=False)
            elif report_type == '607':
                tree_view = self.env.ref('dgii_reports.view_dgii_report_line_tree_607', raise_if_not_found=False)
            
            # Si encontramos una vista específica, reemplazar la vista tree en el campo line_ids
            if tree_view and tree_view.arch and report_type:
                import lxml.etree as ET
                try:
                    arch = ET.fromstring(res['arch'])
                    line_ids_field = arch.xpath("//field[@name='line_ids']")
                    if line_ids_field:
                        # Obtener la vista tree específica (solo el contenido del tree, no el tag tree)
                        tree_arch = ET.fromstring(tree_view.arch)
                        tree_content = tree_arch.find('tree')
                        if tree_content is not None:
                            # Limpiar el contenido actual del campo (incluyendo cualquier tree existente)
                            for child in list(line_ids_field[0]):
                                line_ids_field[0].remove(child)
                            # Crear un nuevo elemento tree y agregar todos los hijos
                            new_tree = ET.Element('tree')
                            # Copiar atributos del tree original si existen
                            if 'string' in tree_content.attrib:
                                new_tree.set('string', tree_content.attrib['string'])
                            if 'default_order' in tree_content.attrib:
                                new_tree.set('default_order', tree_content.attrib['default_order'])
                            # Agregar todos los campos del tree específico
                            for child in tree_content:
                                new_tree.append(child)
                            # Agregar el nuevo tree al campo line_ids
                            line_ids_field[0].append(new_tree)
                            res['arch'] = ET.tostring(arch, encoding='unicode')
                except Exception as e:
                    # Si hay un error, continuar sin modificar la vista
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning("Error al modificar vista tree para reporte %s: %s", report_type, str(e))
        
        return res

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Establecer fechas por defecto (mes actual)
        today = fields.Date.today()
        res['date_from'] = today.replace(day=1)
        res['date_to'] = today
        return res

    def action_generate(self):
        """Genera las líneas del reporte basado en las facturas"""
        self.ensure_one()
        
        # Eliminar líneas existentes
        self.line_ids.unlink()
        
        if self.report_type == '607':
            self._generate_report_607()
        elif self.report_type == '606':
            self._generate_report_606()
        
        self.write({'state': 'generated'})
        
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'dgii.report',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _generate_report_607(self):
        """Genera las líneas del reporte 607 (Ventas)
        
        Parámetros que debe cumplir una factura para estar en el reporte 607:
        1. Tipo: out_invoice (factura de venta) o out_refund (nota de crédito)
        2. Estado: posted (publicada/validada)
        3. Fecha: Dentro del rango del período (date_from a date_to)
        4. Compañía: Debe ser de la compañía seleccionada
        5. Factura Fiscal: Debe ser una factura fiscal (is_l10n_do_fiscal_invoice = True)
        6. Tipo Fiscal: Debe tener un fiscal_type_id asignado
        7. NCF: Debe tener un número de comprobante fiscal (NCF) válido
        """
        # Buscar facturas de venta en el período que cumplan los criterios
        domain = [
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
            ('is_l10n_do_fiscal_invoice', '=', True),  # Debe ser factura fiscal
            ('fiscal_type_id', '!=', False),  # Debe tener tipo fiscal asignado
        ]
        
        invoices = self.env['account.move'].search(domain)
        
        line_vals = []
        for invoice in invoices:
            # Obtener NCF (Número de Comprobante Fiscal)
            # El campo 'ref' es el que almacena el NCF en facturas fiscales
            ncf = invoice.ref or ''
            
            # Si no tiene NCF válido, saltar esta factura
            if not ncf or len(ncf) < 10:
                continue
            
            # Obtener RNC del cliente
            rnc = invoice.partner_id.vat or ''
            rnc = rnc.replace('-', '').replace(' ', '') if rnc else ''
            
            # Tipo de ID según el tipo de documento del cliente
            # 1=RNC, 2=Cédula, 3=Pasaporte, 4=Otro
            tipo_id = '1'  # Por defecto RNC
            if invoice.partner_id.country_id and invoice.partner_id.country_id.code != 'DO':
                tipo_id = '3'  # Pasaporte para extranjeros
            
            # Tipo de ingreso según el campo income_type de la factura
            # Si no tiene income_type, usar 01 por defecto
            tipo_ingreso = getattr(invoice, 'income_type', None) or '01'
            
            # Si es nota de crédito, el tipo de ingreso puede ser diferente
            if invoice.move_type == 'out_refund':
                tipo_ingreso = '02'  # Nota de Crédito
            
            # Fechas en formato YYYYMMDD
            fecha_comprobante = invoice.date.strftime('%Y%m%d') if invoice.date else ''
            
            # Montos
            monto_facturado = invoice.amount_total if invoice.move_type == 'out_invoice' else -invoice.amount_total
            
            # ITBIS facturado (buscar en las líneas de impuestos)
            itbis_facturado = 0.0
            for line in invoice.line_ids:
                if line.tax_line_id and 'itbis' in line.tax_line_id.name.lower():
                    itbis_facturado += abs(line.balance)
            
            # Formas de pago (simplificado, se puede mejorar)
            efectivo = 0.0
            cheques_transferencia = 0.0
            tarjeta_debito = 0.0
            
            # Si hay pagos asociados, distribuir el monto
            if invoice.payment_state == 'paid':
                # Simplificado: distribuir según configuración o lógica
                efectivo = monto_facturado * 0.5  # Ejemplo
                cheques_transferencia = monto_facturado * 0.5
            
            # NCF modificado (para notas de crédito o facturas modificadas)
            ncf_modificado = getattr(invoice, 'origin_out', None) or ''
            
            line_vals.append({
                'report_id': self.id,
                'rnc': rnc[:11],
                'tipo_id': tipo_id,
                'numero_comprobante_fiscal': ncf[:19],
                'ncf_modificado': ncf_modificado[:19] if ncf_modificado else '',
                'tipo_ingreso': tipo_ingreso,
                'fecha_comprobante': fecha_comprobante,
                'fecha_retencion': '',
                'monto_facturado': monto_facturado,
                'monto_comprobante': monto_facturado,
                'itbis_facturado': itbis_facturado,
                'itbis_retenido_terceros': 0.0,
                'itbis_percibido': 0.0,
                'tipo_retencion_renta': '',
                'monto_retencion_renta': 0.0,
                'isr_percibido': 0.0,
                'impuesto_selectivo_consumo': 0.0,
                'otros_impuestos_tasas': 0.0,
                'propina_legal': 0.0,
                'efectivo': efectivo,
                'cheques_transferencia_deposito': cheques_transferencia,
                'tarjeta_debito': tarjeta_debito,
                'tarjeta_credito': 0.0,
                'transferencia': 0.0,
                'debito_credito': 0.0,
                'formas_ventas': monto_facturado,
                'estado': 'OK',
                'move_id': invoice.id,
            })
        
        if line_vals:
            self.env['dgii.report.line'].create(line_vals)
    
    def _generate_report_606(self):
        """Genera las líneas del reporte 606 (Compras)
        
        Parámetros que debe cumplir una factura para estar en el reporte 606:
        1. Tipo: in_invoice (factura de compra) o in_refund (nota de crédito de proveedor)
        2. Estado: posted (publicada/validada)
        3. Fecha: Dentro del rango del período (date_from a date_to)
        4. Compañía: Debe ser de la compañía seleccionada
        5. Factura Fiscal: Debe ser una factura fiscal (is_l10n_do_fiscal_invoice = True)
        6. Tipo Fiscal: Debe tener un fiscal_type_id asignado
        7. NCF: Debe tener un número de comprobante fiscal (NCF) válido
        """
        # Buscar facturas de compra en el período que cumplan los criterios
        domain = [
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
            ('is_l10n_do_fiscal_invoice', '=', True),  # Debe ser factura fiscal
            ('fiscal_type_id', '!=', False),  # Debe tener tipo fiscal asignado
        ]
        
        invoices = self.env['account.move'].search(domain)
        
        line_vals = []
        for invoice in invoices:
            # Obtener NCF (Número de Comprobante Fiscal)
            ncf = invoice.ref or ''
            
            # Si no tiene NCF válido, saltar esta factura
            if not ncf or len(ncf) < 10:
                continue
            
            # Obtener RNC del proveedor
            rnc = invoice.partner_id.vat or ''
            rnc = rnc.replace('-', '').replace(' ', '') if rnc else ''
            
            # Tipo de ID según el tipo de documento del proveedor
            # 1=RNC, 2=Cédula, 3=Pasaporte, 4=Otro
            tipo_id = '1'  # Por defecto RNC
            if invoice.partner_id.country_id and invoice.partner_id.country_id.code != 'DO':
                tipo_id = '3'  # Pasaporte para extranjeros
            
            # Tipo de gasto según el campo expense_type de la factura
            # Si no tiene expense_type, usar 01 por defecto
            tipo_ingreso = getattr(invoice, 'expense_type', None) or '01'
            
            # Descripción del tipo de bien o servicio según expense_type
            expense_type_dict = {
                '01': 'Gastos de personal',
                '02': 'Gastos por trabajo, suministros y servicios',
                '03': 'Arrendamientos',
                '04': 'Gastos de Activos Fijos',
                '05': 'Gastos de Representación',
                '06': 'Otras Deducciones Admitidas',
                '07': 'Gastos Financieros',
                '08': 'Gastos Extraordinarios',
                '09': 'Compras y Gastos que forman parte del Costo de Venta',
                '10': 'Adquisiciones de Activos',
                '11': 'Gastos de Seguro',
            }
            tipo_bien_servicio = expense_type_dict.get(tipo_ingreso, '')
            
            # Si es nota de crédito, el tipo puede ser diferente
            if invoice.move_type == 'in_refund':
                tipo_ingreso = '02'  # Nota de Crédito
            
            # Fechas en formato YYYYMMDD y desglosadas
            fecha_comprobante = invoice.date.strftime('%Y%m%d') if invoice.date else ''
            fecha_comprobante_ym = invoice.date.strftime('%Y%m') if invoice.date else ''
            fecha_comprobante_dd = invoice.date.strftime('%d') if invoice.date else ''
            
            # Fecha de pago (buscar en los pagos asociados)
            fecha_pago = ''
            fecha_pago_ym = ''
            fecha_pago_dd = ''
            if invoice.payment_state == 'paid' and invoice.payment_ids:
                # Tomar la fecha del último pago
                last_payment = invoice.payment_ids.sorted('date', reverse=True)[0]
                fecha_pago = last_payment.date.strftime('%Y%m%d') if last_payment.date else ''
                fecha_pago_ym = last_payment.date.strftime('%Y%m') if last_payment.date else ''
                fecha_pago_dd = last_payment.date.strftime('%d') if last_payment.date else ''
            
            # Montos: separar servicios y productos
            monto_servicios = 0.0
            monto_productos = 0.0
            
            for line in invoice.invoice_line_ids:
                if line.product_id:
                    if line.product_id.type == 'service':
                        monto_servicios += line.price_subtotal
                    else:
                        monto_productos += line.price_subtotal
                else:
                    # Si no tiene producto, considerar como servicios por defecto
                    monto_servicios += line.price_subtotal
            
            monto_comprobante = invoice.amount_total if invoice.move_type == 'in_invoice' else -invoice.amount_total
            
            # ITBIS facturado y retenido (buscar en las líneas de impuestos)
            itbis_facturado = 0.0
            itbis_retenido = 0.0
            
            for line in invoice.line_ids:
                if line.tax_line_id:
                    tax_name = line.tax_line_id.name.lower()
                    tax_amount = abs(line.balance)
                    
                    if 'itbis' in tax_name:
                        if 'retenido' in tax_name or 'retencion' in tax_name:
                            itbis_retenido += tax_amount
                        else:
                            itbis_facturado += tax_amount
            
            # ITBIS pagado por categorías (distribuir según tipo de producto)
            itbis_pagado_compras = 0.0
            itbis_pagado_importaciones = 0.0
            itbis_pagado_servicios = 0.0
            itbis_pagado_bienes = 0.0
            itbis_pagado_activos_fijos = 0.0
            itbis_pagado_otros = 0.0
            
            # Distribuir ITBIS según tipo de producto en las líneas de factura
            for line in invoice.invoice_line_ids:
                if line.tax_ids:
                    for tax in line.tax_ids:
                        if 'itbis' in tax.name.lower():
                            # Calcular ITBIS de esta línea
                            tax_amount = abs(line.balance) if line.tax_line_id else line.price_subtotal * (tax.amount / 100)
                            
                            if line.product_id:
                                if line.product_id.type == 'service':
                                    itbis_pagado_servicios += tax_amount
                                elif line.product_id.type == 'product':
                                    # Verificar si es activo fijo (simplificado)
                                    if line.product_id.categ_id and 'activo' in line.product_id.categ_id.name.lower():
                                        itbis_pagado_activos_fijos += tax_amount
                                    else:
                                        itbis_pagado_bienes += tax_amount
                                else:
                                    itbis_pagado_otros += tax_amount
                            else:
                                itbis_pagado_compras += tax_amount
            
            # ITBIS por adelantar (si la factura está pagada)
            itbis_por_adelantar = 0.0
            if invoice.payment_state == 'paid':
                itbis_por_adelantar = itbis_facturado
            
            # Retención de renta/ISR (buscar en las líneas de impuestos)
            tipo_retencion_renta = ''
            tipo_retencion_isr = ''
            monto_retencion_renta = 0.0
            
            for line in invoice.line_ids:
                if line.tax_line_id:
                    tax_name = line.tax_line_id.name.lower()
                    tax_amount = abs(line.balance)
                    
                    if 'retencion' in tax_name or 'isr' in tax_name or 'renta' in tax_name:
                        monto_retencion_renta += tax_amount
                        if 'isr' in tax_name:
                            tipo_retencion_isr = '01'  # Por defecto
                        else:
                            tipo_retencion_renta = '01'  # Por defecto
            
            # ITBIS retenido por terceros
            itbis_retenido_terceros = 0.0
            
            # Impuesto selectivo al consumo
            impuesto_selectivo_consumo = 0.0
            for line in invoice.line_ids:
                if line.tax_line_id:
                    tax_name = line.tax_line_id.name.lower()
                    if 'selectivo' in tax_name or 'consumo' in tax_name:
                        impuesto_selectivo_consumo += abs(line.balance)
            
            # NCF modificado (para notas de crédito o facturas modificadas)
            ncf_modificado = getattr(invoice, 'origin_out', None) or ''
            
            line_vals.append({
                'report_id': self.id,
                'rnc': rnc[:11] if rnc else '',
                'tipo_id': tipo_id,
                'numero_comprobante_fiscal': ncf[:19],
                'ncf_modificado': ncf_modificado[:19] if ncf_modificado else '',
                'tipo_ingreso': tipo_ingreso,
                'tipo_bien_servicio': tipo_bien_servicio,
                'fecha_comprobante': fecha_comprobante,
                'fecha_comprobante_ym': fecha_comprobante_ym,
                'fecha_comprobante_dd': fecha_comprobante_dd,
                'fecha_pago': fecha_pago,
                'fecha_pago_ym': fecha_pago_ym,
                'fecha_pago_dd': fecha_pago_dd,
                'fecha_retencion': '',
                'monto_servicios': monto_servicios,
                'monto_productos': monto_productos,
                'monto_facturado': monto_comprobante,  # Total monto facturado
                'monto_comprobante': monto_comprobante,
                'itbis_facturado': itbis_facturado,
                'itbis_retenido': itbis_retenido,
                'itbis_retenido_terceros': itbis_retenido_terceros,
                'itbis_percibido': 0.0,  # No aplica para compras
                'tipo_retencion_renta': tipo_retencion_renta,
                'tipo_retencion_isr': tipo_retencion_isr,
                'monto_retencion_renta': monto_retencion_renta,
                'isr_percibido': 0.0,  # No aplica para compras
                'impuesto_selectivo_consumo': impuesto_selectivo_consumo,
                'otros_impuestos_tasas': 0.0,
                'propina_legal': 0.0,  # Pro leg
                'efectivo': 0.0,  # No aplica para compras
                'cheques_transferencia_deposito': 0.0,  # No aplica para compras
                'tarjeta_debito': 0.0,  # No aplica para compras
                'tarjeta_credito': 0.0,
                'transferencia': 0.0,
                'debito_credito': 0.0,
                'itbis_sujeto_proporcionalidad': 0.0,
                'itbis_llevado_costo_gasto': 0.0,
                'itbis_por_adelantar': itbis_por_adelantar,
                'itbis_pagado_compras': itbis_pagado_compras,
                'itbis_pagado_importaciones': itbis_pagado_importaciones,
                'itbis_pagado_servicios': itbis_pagado_servicios,
                'itbis_pagado_bienes': itbis_pagado_bienes,
                'itbis_pagado_activos_fijos': itbis_pagado_activos_fijos,
                'itbis_pagado_otros': itbis_pagado_otros,
                'formas_ventas': 0.0,  # No aplica para compras
                'estado': 'OK',
                'move_id': invoice.id,
            })
        
        if line_vals:
            self.env['dgii.report.line'].create(line_vals)

    def action_send(self):
        """Envía el reporte a DGII"""
        self.ensure_one()
        
        # Validar que el reporte tenga líneas generadas
        if not self.line_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'El reporte no tiene líneas generadas. Por favor, genere el reporte primero.',
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        # Cambiar el estado a enviado
        self.write({'state': 'sent'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Reporte Enviado',
                'message': f'El reporte {self.name} ha sido marcado como enviado.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_export_xlsx(self):
        """Exporta el reporte a formato Excel"""
        self.ensure_one()
        
        if not self.line_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'El reporte no tiene líneas para exportar.',
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        try:
            import xlsxwriter
            import io
            import base64
            from datetime import datetime
            
            # Crear un objeto en memoria para el archivo Excel
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Reporte ' + self.report_type)
            
            # Formato para encabezados
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#366092',
                'font_color': 'white',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            
            # Formato para números
            number_format = workbook.add_format({'num_format': '#,##0.00'})
            
            # Encabezados según el tipo de reporte
            if self.report_type == '607':
                headers = [
                    'RNC/Cédula o Pasaporte', 'Tipo Identificación', 'Número Comprobante Fiscal',
                    'Número Comprobante Fiscal Modificado', 'Tipo de Ingreso', 'Fecha Comprobante',
                    'Fecha de Retención', 'Monto Facturado', 'ITBIS Facturado', 'ITBIS Retenido por Terceros',
                    'ITBIS Percibido', 'Retención Renta por Terceros', 'ISR Percibido',
                    'Impuesto Selectivo al Consumo', 'Otros Impuestos/Tasas',
                    'Monto Propina Legal', 'Efectivo', 'Cheque/ Transferencia/ Depósito',
                    'Tarjeta Débito/Crédito', 'Venta a Crédito', 'Bonos o Certificados de Regalo',
                    'Permuta', 'Otras Formas de Ventas'
                ]
            else:  # 606
                headers = [
                    'RNC o Cédula', 'Tipo Id', 'Tipo Bienes y Servicios Comprados', 'NCF',
                    'NCF ó Documento Modificado', 'Fecha Comprobante', 'Fecha Pago',
                    'Monto Facturado en Servicios', 'Monto Facturado en Bienes', 'Total Monto Facturado',
                    'ITBIS Facturado', 'ITBIS Retenido', 'ITBIS sujeto a Proporcionalidad (Art. 349)',
                    'ITBIS llevado al Costo', 'ITBIS por Adelantar', 'ITBIS percib en compra',
                    'Tipo de Retención en ISR', 'Monto Retención Renta', 'ISR Percibido en compras',
                    'Impuesto Selectivo al Consumo', 'Otros Impuesto/Tasas', 'Monto Propina Legal', 'Forma de Pago'
                ]
            
            # Escribir encabezados
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Escribir datos
            row = 1
            for line in self.line_ids:
                if self.report_type == '607':
                    data = [
                        line.rnc or '',
                        line.tipo_id or '',
                        line.numero_comprobante_fiscal or '',
                        line.ncf_modificado or '',
                        line.tipo_ingreso or '',
                        line.fecha_comprobante or '',
                        line.fecha_retencion or '',
                        line.monto_facturado,
                        line.itbis_facturado,
                        line.itbis_retenido_terceros,
                        line.itbis_percibido,
                        line.monto_retencion_renta,
                        line.isr_percibido,
                        line.impuesto_selectivo_consumo,
                        line.otros_impuestos_tasas,
                        line.propina_legal,
                        line.efectivo,
                        line.cheques_transferencia_deposito,
                        (line.tarjeta_debito or 0.0) + (line.tarjeta_credito or 0.0),
                        line.venta_credito,
                        line.bonos_certificados_regalo,
                        line.permuta,
                        line.otras_formas_ventas or line.formas_ventas or 0.0,
                    ]
                else:  # 606
                    # Determinar forma de pago (simplificado: usar efectivo si existe, sino cheques/transferencia)
                    forma_pago = ''
                    if line.efectivo and line.efectivo > 0:
                        forma_pago = 'Efectivo'
                    elif line.cheques_transferencia_deposito and line.cheques_transferencia_deposito > 0:
                        forma_pago = 'Cheques/Transferencia'
                    elif line.tarjeta_debito and line.tarjeta_debito > 0:
                        forma_pago = 'Tarjeta Débito'
                    elif line.tarjeta_credito and line.tarjeta_credito > 0:
                        forma_pago = 'Tarjeta Crédito'
                    
                    # Formatear Tipo Bienes y Servicios Comprados como "09- Compras y Gastos que forman parte del Costo de Venta"
                    codigo_tipo = line.tipo_ingreso or ''
                    descripcion_tipo = line.tipo_bien_servicio or ''
                    tipo_bien_servicio_formato = ''
                    if codigo_tipo:
                        if descripcion_tipo:
                            tipo_bien_servicio_formato = f"{codigo_tipo}- {descripcion_tipo}"
                        else:
                            tipo_bien_servicio_formato = codigo_tipo
                    
                    data = [
                        line.rnc or '',
                        line.tipo_id or '',
                        tipo_bien_servicio_formato,
                        line.numero_comprobante_fiscal or '',
                        line.ncf_modificado or '',
                        line.fecha_comprobante or '',
                        line.fecha_pago or '',
                        line.monto_servicios,
                        line.monto_productos,
                        line.monto_comprobante,
                        line.itbis_facturado,
                        line.itbis_retenido,
                        line.itbis_sujeto_proporcionalidad,
                        line.itbis_llevado_costo_gasto,
                        line.itbis_por_adelantar,
                        line.itbis_pagado_compras,
                        line.tipo_retencion_isr or '',
                        line.monto_retencion_renta,
                        line.isr_percibido,
                        line.impuesto_selectivo_consumo,
                        line.otros_impuestos_tasas,
                        line.propina_legal,
                        forma_pago,
                    ]
                
                for col, value in enumerate(data):
                    if isinstance(value, (int, float)):
                        worksheet.write(row, col, value, number_format)
                    else:
                        worksheet.write(row, col, value)
                row += 1
            
            # Ajustar ancho de columnas
            worksheet.set_column(0, len(headers) - 1, 15)
            
            workbook.close()
            output.seek(0)
            
            # Crear el archivo adjunto
            filename = f'Reporte_{self.report_type}_{self.name.replace(" ", "_")}.xlsx'
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(output.read()),
                'res_model': self._name,
                'res_id': self.id,
            })
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
            
        except ImportError:
            # Si xlsxwriter no está disponible, usar CSV como alternativa
            return self._export_to_csv()
    
    def _export_to_csv(self):
        """Exporta el reporte a formato CSV (alternativa si no hay xlsxwriter)"""
        import csv
        import io
        import base64
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Encabezados
        if self.report_type == '607':
            headers = [
                'RNC/Cédula o Pasaporte', 'Tipo Identificación', 'Número Comprobante Fiscal',
                'Número Comprobante Fiscal Modificado', 'Tipo de Ingreso', 'Fecha Comprobante',
                'Fecha de Retención', 'Monto Facturado', 'ITBIS Facturado', 'ITBIS Retenido por Terceros',
                'ITBIS Percibido', 'Retención Renta por Terceros', 'ISR Percibido',
                'Impuesto Selectivo al Consumo', 'Otros Impuestos/Tasas'
            ]
        else:  # 606
            headers = [
                'RNC o Cédula', 'Tipo Id', 'Tipo Bienes y Servicios Comprados', 'NCF',
                'NCF ó Documento Modificado', 'Fecha Comprobante', 'Fecha Pago',
                'Monto Facturado en Servicios', 'Monto Facturado en Bienes', 'Total Monto Facturado',
                'ITBIS Facturado', 'ITBIS Retenido', 'ITBIS sujeto a Proporcionalidad (Art. 349)',
                'ITBIS llevado al Costo', 'ITBIS por Adelantar', 'ITBIS percib en compra',
                'Tipo de Retención en ISR', 'Monto Retención Renta', 'ISR Percibido en compras',
                'Impuesto Selectivo al Consumo', 'Otros Impuesto/Tasas', 'Monto Propina Legal', 'Forma de Pago'
            ]
        
        writer.writerow(headers)
        
        # Datos
        for line in self.line_ids:
            if self.report_type == '607':
                row = [
                    line.rnc or '',
                    line.tipo_id or '',
                    line.numero_comprobante_fiscal or '',
                    line.ncf_modificado or '',
                    line.tipo_ingreso or '',
                    line.fecha_comprobante or '',
                    line.fecha_retencion or '',
                    line.monto_facturado,
                    line.itbis_facturado,
                    line.itbis_retenido_terceros,
                    line.itbis_percibido,
                    line.monto_retencion_renta,
                    line.isr_percibido,
                    line.impuesto_selectivo_consumo,
                    line.otros_impuestos_tasas,
                ]
            else:  # 606
                # Determinar forma de pago
                forma_pago = ''
                if line.efectivo and line.efectivo > 0:
                    forma_pago = 'Efectivo'
                elif line.cheques_transferencia_deposito and line.cheques_transferencia_deposito > 0:
                    forma_pago = 'Cheques/Transferencia'
                elif line.tarjeta_debito and line.tarjeta_debito > 0:
                    forma_pago = 'Tarjeta Débito'
                elif line.tarjeta_credito and line.tarjeta_credito > 0:
                    forma_pago = 'Tarjeta Crédito'
                
                row = [
                    line.rnc or '',
                    line.tipo_id or '',
                    line.tipo_ingreso or '',
                    line.numero_comprobante_fiscal or '',
                    line.ncf_modificado or '',
                    line.fecha_comprobante or '',
                    line.fecha_pago or '',
                    line.monto_servicios,
                    line.monto_productos,
                    line.monto_comprobante,
                    line.itbis_facturado,
                    line.itbis_retenido,
                    line.itbis_sujeto_proporcionalidad,
                    line.itbis_llevado_costo_gasto,
                    line.itbis_por_adelantar,
                    line.itbis_pagado_compras,
                    line.tipo_retencion_isr or '',
                    line.monto_retencion_renta,
                    line.isr_percibido,
                    line.impuesto_selectivo_consumo,
                    line.otros_impuestos_tasas,
                    line.propina_legal,
                    forma_pago,
                ]
            writer.writerow(row)
        
        # Crear archivo adjunto
        filename = f'Reporte_{self.report_type}_{self.name.replace(" ", "_")}.csv'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue().encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
    
    def action_export_txt(self):
        """Exporta el reporte a formato TXT según formato DGII"""
        self.ensure_one()
        
        if not self.line_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'El reporte no tiene líneas para exportar.',
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        import io
        import base64
        
        output = io.StringIO()
        
        # Escribir cada línea según formato DGII (formato fijo de columnas)
        for line in self.line_ids:
            if self.report_type == '607':
                # Formato para reporte 607 (ajustar según especificación DGII)
                txt_line = (
                    f"{str(line.rnc or ''):<11}"  # RNC (11 caracteres)
                    f"{str(line.tipo_id or ''):<2}"  # Tipo ID (2 caracteres)
                    f"{str(line.numero_comprobante_fiscal or ''):<19}"  # NCF (19 caracteres)
                    f"{str(line.ncf_modificado or ''):<19}"  # NCF Modificado (19 caracteres)
                    f"{str(line.tipo_ingreso or ''):<2}"  # Tipo Ingreso (2 caracteres)
                    f"{str(line.fecha_comprobante or ''):<8}"  # Fecha Comprobante (8 caracteres)
                    f"{str(line.fecha_retencion or ''):<8}"  # Fecha Retención (8 caracteres)
                    f"{line.monto_facturado:>15.2f}"  # Monto Facturado (15 caracteres, 2 decimales)
                    f"{line.itbis_facturado:>15.2f}"  # ITBIS Facturado
                    f"{line.itbis_retenido_terceros:>15.2f}"  # ITBIS Retenido
                    f"{line.itbis_percibido:>15.2f}"  # ITBIS Percibido
                    f"{line.monto_retencion_renta:>15.2f}"  # Monto Retención Renta
                    f"{line.isr_percibido:>15.2f}"  # ISR Percibido
                    f"{line.impuesto_selectivo_consumo:>15.2f}"  # Impuesto Selectivo
                    f"{line.otros_impuestos_tasas:>15.2f}"  # Otros Impuestos
                    f"{line.propina_legal:>15.2f}"  # Propina Legal
                    f"{line.efectivo:>15.2f}"  # Efectivo
                    f"{line.cheques_transferencia_deposito:>15.2f}"  # Cheques/Transferencia
                    f"{line.tarjeta_debito:>15.2f}"  # Tarjeta Débito
                    f"\n"
                )
            else:  # 606
                txt_line = (
                    f"{str(line.rnc or ''):<11}"
                    f"{str(line.tipo_id or ''):<2}"
                    f"{str(line.numero_comprobante_fiscal or ''):<19}"
                    f"{str(line.ncf_modificado or ''):<19}"
                    f"{str(line.tipo_ingreso or ''):<2}"
                    f"{str(line.fecha_comprobante or ''):<8}"
                    f"{line.monto_comprobante:>15.2f}"
                    f"{line.itbis_facturado:>15.2f}"
                    f"{line.itbis_retenido_terceros:>15.2f}"
                    f"{line.itbis_percibido:>15.2f}"
                    f"{str(line.tipo_retencion_renta or ''):<2}"
                    f"{line.monto_retencion_renta:>15.2f}"
                    f"{line.itbis_pagado_compras:>15.2f}"
                    f"{line.itbis_pagado_importaciones:>15.2f}"
                    f"{line.itbis_pagado_servicios:>15.2f}"
                    f"{line.itbis_pagado_bienes:>15.2f}"
                    f"{line.itbis_pagado_activos_fijos:>15.2f}"
                    f"{line.itbis_pagado_otros:>15.2f}"
                    f"\n"
                )
            output.write(txt_line)
        
        # Crear archivo adjunto
        filename = f'Reporte_{self.report_type}_{self.name.replace(" ", "_")}.txt'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue().encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

