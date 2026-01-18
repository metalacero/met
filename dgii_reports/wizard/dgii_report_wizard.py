# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class DgiiReportWizard(models.TransientModel):
    _name = 'dgii.report.wizard'
    _description = 'Wizard para generar reportes DGII'

    report_type = fields.Selection([
        ('606', 'Reporte 606 - Compras'),
        ('607', 'Reporte 607 - Ventas'),
    ], string='Tipo de Reporte', required=True)
    
    company_id = fields.Many2one('res.company', string='Compañía', 
                                  default=lambda self: self.env.company, required=True)
    
    month = fields.Selection([
        ('1', 'Enero'),
        ('2', 'Febrero'),
        ('3', 'Marzo'),
        ('4', 'Abril'),
        ('5', 'Mayo'),
        ('6', 'Junio'),
        ('7', 'Julio'),
        ('8', 'Agosto'),
        ('9', 'Septiembre'),
        ('10', 'Octubre'),
        ('11', 'Noviembre'),
        ('12', 'Diciembre'),
    ], string='Mes', required=True, default=lambda self: str(datetime.now().month))
    
    year = fields.Char(string='Año', required=True, default=lambda self: str(datetime.now().year), size=4)
    
    exclude_error = fields.Boolean(string='Exclude error', default=False)
    
    currency_rate = fields.Float(string='Currency Rate', digits=(16, 4), default=0.0)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = datetime.now()
        if 'month' not in res:
            res['month'] = str(today.month)
        if 'year' not in res:
            res['year'] = str(today.year)
        # Asegurar que year siempre sea string
        if 'year' in res and res['year']:
            res['year'] = str(res['year'])
        return res

    def action_generate(self):
        """Genera el reporte basado en los parámetros del wizard"""
        # Calcular fechas desde/hasta basado en mes y año
        from calendar import monthrange
        year_int = int(self.year) if isinstance(self.year, str) else self.year
        last_day = monthrange(year_int, int(self.month))[1]
        date_from = fields.Date.to_date(f'{year_int}-{int(self.month):02d}-01')
        date_to = fields.Date.to_date(f'{year_int}-{int(self.month):02d}-{last_day}')
        
        # Crear nombre del reporte
        month_name = dict(self._fields['month'].selection)[self.month]
        year_str = str(self.year) if not isinstance(self.year, str) else self.year
        report_name = f"{self.report_type} - {month_name} {year_str}"
        
        # Crear el reporte
        report = self.env['dgii.report'].create({
            'name': report_name,
            'report_type': self.report_type,
            'date_from': date_from,
            'date_to': date_to,
            'company_id': self.company_id.id,
        })
        
        # Generar las líneas del reporte automáticamente
        report.action_generate()
        
        # Retornar la vista del reporte generado
        return {
            'type': 'ir.actions.act_window',
            'name': report_name,
            'res_model': 'dgii.report',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'current',
        }

