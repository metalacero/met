# Quotation Management (quotation_met)

## Descripción

Este módulo agrega validación de inventario antes de confirmar una cotización y convertirla en orden de venta.

## Funcionalidades

- **Validación de inventario**: Antes de confirmar una cotización, el sistema valida que exista suficiente inventario disponible para todos los productos almacenables en la orden.

- **Mensajes de error claros**: Si no hay suficiente inventario, se muestra un mensaje de error detallado indicando:
  - El nombre del producto
  - La cantidad solicitada
  - La cantidad disponible en inventario

## Dependencias

- `sale`: Módulo de ventas
- `stock`: Módulo de inventario

## Instalación

1. Copia el módulo en la carpeta de addons de Odoo
2. Actualiza la lista de aplicaciones
3. Instala el módulo "Quotation Management"

## Uso

Cuando intentes confirmar una cotización (cambiar de estado 'draft' o 'sent' a 'sale'), el sistema automáticamente:

1. Verificará cada línea de la orden
2. Para productos almacenables, comprobará la cantidad disponible en inventario
3. Si no hay suficiente inventario, mostrará un error y evitará la confirmación
4. Si todo está correcto, procederá con la confirmación normal

## Notas

- Solo valida productos de tipo "product" (almacenables)
- Considera el almacén configurado en la orden de venta
- No afecta productos de tipo servicio o consumible

