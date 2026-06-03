# Manual de usuario — Dashboard

## Acceso

1. API en ejecución (`http://localhost:8000`)
2. Frontend en ejecución (`http://localhost:3000`)
3. ETL completado al menos una vez

---

## Interfaz general

El dashboard se divide en:

- **Sidebar (izquierda):** filtros, ingestión de datos y acciones de reprocesamiento
- **Área principal:** pestañas de análisis
- **Cabecera:** resumen del filtro activo

---

## Filtros

### Tiendas

Checkboxes para tiendas **102, 103, 107 y 110**. Los KPIs y gráficos solo incluyen las tiendas marcadas.

Debe haber al menos una tienda activa; de lo contrario el área principal muestra un aviso.

### Rango de fechas

Por defecto: 2013-01-01 a 2013-06-30 (periodo del dataset).

Los cambios de filtro se aplican automáticamente tras un breve retardo (debounce).

**Restablecer filtros** vuelve a todas las tiendas y al rango completo.

---

## Pestañas

### Resumen ejecutivo

| Elemento | Descripción |
|----------|-------------|
| Unidades vendidas | Suma de cantidades en el periodo filtrado |
| Transacciones | Número de tickets |
| Clientes únicos | Compradores distintos |
| Top 10 categorías | Mayor volumen (el dataset no incluye SKU individual) |
| Top 10 clientes | Mayor número de transacciones |
| Días de la semana | Transacciones agregadas por Lunes–Domingo |
| Participación top categorías | Distribución relativa |

### Visualizaciones

- Serie temporal de transacciones
- Boxplot del tamaño de canasta por cliente (top clientes)
- Heatmaps de actividad por día/mes y correlaciones entre métricas de cliente

### Segmentación

- Gráfico de dispersión (PCA) de clientes agrupados con K-Means (k = 4)
- Perfiles de cada cluster: frecuencia, volumen, diversidad de categorías

Los modelos se generan durante el ETL. Si la pestaña está vacía, usar **Regenerar datos**.

### Recomendaciones

**Por cliente:** ingresar ID de cliente → categorías complementarias según historial y filtros activos.

**Por categoría:** ingresar ID 1–50 → categorías que suelen comprarse en la misma canasta.

---

## Incorporar nuevos datos

Los datos nuevos se agregan **por tienda**, no se crean tiendas adicionales.

### Procedimiento

1. En el sidebar, pulsar **+** junto a la tienda deseada
2. Seleccionar archivo `.csv` con líneas en formato `fecha|tienda|cliente|ítems`
3. Revisar el resultado de la validación en el modal
4. Confirmar con **Agregar al CSV**
5. Pulsar **Procesar nuevos datos** para actualizar Parquet y modelos ML
6. Recargar o esperar la actualización del dashboard

### Reglas del CSV de carga

- Extensión `.csv`, codificación UTF-8
- Sin fila de encabezado
- Todas las líneas deben corresponder a **la misma tienda** seleccionada
- Formato por línea: `AAAA-MM-DD|tienda|id_cliente|n1 n2 n3 ...`
- Tienda 102: ítems = categorías 1–50
- Tiendas 103, 107, 110: ítems = SKU (se mapean a categoría en el ETL)

Las líneas válidas se **añaden al final** del archivo `{tienda}_Tran.csv` existente.

### Restablecer datos originales

1. Restaurar los cuatro CSV del curso en `DataSet/DataSet/Transactions/`
2. Eliminar la carpeta `data/processed/`
3. Ejecutar el ETL (`python -m src.etl.load_transactions` o **Regenerar datos**)

---

## Acciones del sidebar

| Botón | Función |
|-------|---------|
| **+** (por tienda) | Abrir modal de carga de transacciones |
| **Procesar nuevos datos** | ETL + reentrenamiento ML tras una carga |
| **Regenerar datos (Spark)** | Reprocesar todo el dataset desde los CSV |

---

## Pie del sidebar — Dataset (global)

Muestra totales **sin filtrar** (todas las tiendas y fechas del ETL). Los KPIs principales respetan los filtros seleccionados.
