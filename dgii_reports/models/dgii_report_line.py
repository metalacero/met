# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DgiiReportLine(models.Model):
    _name = 'dgii.report.line'
    _description = 'DGII Report Line'
    _order = 'fecha_comprobante desc, id desc'

    report_id = fields.Many2one('dgii.report', string='Reporte', required=True, ondelete='cascade')
    report_type = fields.Selection(related='report_id.report_type', store=True, readonly=True)
    
    # Información del cliente/proveedor
    rnc = fields.Char(string='RNC', size=11)
    tipo_id = fields.Char(string='Tipo Id', size=2)
    
    # Información del comprobante
    numero_comprobante_fiscal = fields.Char(string='Número Comprobante Fiscal', size=19)
    ncf_modificado = fields.Char(string='NCF o Documento Modificado', size=19)
    tipo_ingreso = fields.Char(string='Tipo de Ingreso', size=2)
    tipo_bien_servicio = fields.Char(string='Tipo de Bien o Servicio', size=100)
    tipo_bien_servicio_codigo = fields.Char(string='Tipo de bien o servicio comprados', size=2, compute='_compute_tipo_bien_servicio_codigo', store=False)
    
    @api.depends('tipo_ingreso', 'report_type')
    def _compute_tipo_bien_servicio_codigo(self):
        for record in self:
            if record.report_type == '606':
                record.tipo_bien_servicio_codigo = record.tipo_ingreso
            else:
                record.tipo_bien_servicio_codigo = ''
    fecha_comprobante = fields.Char(string='Fecha Comprobante', size=8)  # YYYYMMDD
    fecha_comprobante_ym = fields.Char(string='Fecha Comprobante YM', size=6)  # YYYYMM
    fecha_comprobante_dd = fields.Char(string='Fecha Comprobante DD', size=2)  # DD
    fecha_pago = fields.Char(string='Fecha de Pago', size=8)  # YYYYMMDD
    fecha_pago_ym = fields.Char(string='Fecha de Pago YM', size=6)  # YYYYMM
    fecha_pago_dd = fields.Char(string='Fecha de Pago DD', size=2)  # DD
    fecha_retencion = fields.Char(string='Fecha Retención', size=8)
    
    # Montos
    monto_facturado = fields.Float(string='Monto Facturado', digits=(16, 2), default=0.0)
    monto_comprobante = fields.Float(string='Monto Comprobante', digits=(16, 2), default=0.0)
    monto_servicios = fields.Float(string='Monto en Servicios', digits=(16, 2), default=0.0)
    monto_productos = fields.Float(string='Monto en Productos', digits=(16, 2), default=0.0)
    
    # ITBIS
    itbis_facturado = fields.Float(string='ITBIS Facturado', digits=(16, 2), default=0.0)
    itbis_retenido = fields.Float(string='ITBIS Retenido', digits=(16, 2), default=0.0)
    itbis_retenido_terceros = fields.Float(string='ITBIS Retenido por Terceros', digits=(16, 2), default=0.0)
    itbis_percibido = fields.Float(string='ITBIS Percibido', digits=(16, 2), default=0.0)
    
    # Retención de Renta
    tipo_retencion_renta = fields.Char(string='Tipo de Retención en Renta', size=2)
    tipo_retencion_isr = fields.Char(string='Tipo de Retención en ISR', size=2)
    monto_retencion_renta = fields.Float(string='Monto Retención Renta', digits=(16, 2), default=0.0)
    isr_percibido = fields.Float(string='ISR Percibido', digits=(16, 2), default=0.0)
    
    # Otros impuestos
    impuesto_selectivo_consumo = fields.Float(string='Impuesto Selectivo al Consumo', digits=(16, 2), default=0.0)
    otros_impuestos_tasas = fields.Float(string='Otros Impuestos/Tasas', digits=(16, 2), default=0.0)
    propina_legal = fields.Float(string='Propina Legal', digits=(16, 2), default=0.0)
    
    # Formas de pago
    efectivo = fields.Float(string='Efectivo', digits=(16, 2), default=0.0)
    cheques_transferencia_deposito = fields.Float(string='Cheques/Transferencia/Depósito', digits=(16, 2), default=0.0)
    tarjeta_debito = fields.Float(string='Tarjeta Débito', digits=(16, 2), default=0.0)
    tarjeta_credito = fields.Float(string='Tarjeta Crédito', digits=(16, 2), default=0.0)
    transferencia = fields.Float(string='Transferencia', digits=(16, 2), default=0.0)
    debito_credito = fields.Float(string='Débito/Crédito', digits=(16, 2), default=0.0)
    venta_credito = fields.Float(string='Venta a Crédito', digits=(16, 2), default=0.0)
    bonos_certificados_regalo = fields.Float(string='Bonos o Certificados de Regalo', digits=(16, 2), default=0.0)
    permuta = fields.Float(string='Permuta', digits=(16, 2), default=0.0)
    otras_formas_ventas = fields.Float(string='Otras Formas de Ventas', digits=(16, 2), default=0.0)
    
    # ITBIS adicionales (para reporte 606)
    itbis_sujeto_proporcionalidad = fields.Float(string='ITBIS Sujeto a Proporcionalidad', digits=(16, 2), default=0.0)
    itbis_llevado_costo_gasto = fields.Float(string='ITBIS Llevado a Costo o Gasto', digits=(16, 2), default=0.0)
    itbis_por_adelantar = fields.Float(string='ITBIS por Adelantar', digits=(16, 2), default=0.0)
    itbis_pagado_compras = fields.Float(string='ITBIS Pagado en Compras', digits=(16, 2), default=0.0)
    itbis_pagado_importaciones = fields.Float(string='ITBIS Pagado en Importaciones', digits=(16, 2), default=0.0)
    itbis_pagado_servicios = fields.Float(string='ITBIS Pagado en Servicios', digits=(16, 2), default=0.0)
    itbis_pagado_bienes = fields.Float(string='ITBIS Pagado en Bienes', digits=(16, 2), default=0.0)
    itbis_pagado_activos_fijos = fields.Float(string='ITBIS Pagado en Activos Fijos', digits=(16, 2), default=0.0)
    itbis_pagado_otros = fields.Float(string='ITBIS Pagado en Otros', digits=(16, 2), default=0.0)
    
    # Otros campos
    formas_ventas = fields.Float(string='Formas de Ventas', digits=(16, 2), default=0.0)
    estado = fields.Char(string='Estado', size=10, default='OK')
    
    # Referencia a la factura original
    move_id = fields.Many2one('account.move', string='Factura', readonly=True)

