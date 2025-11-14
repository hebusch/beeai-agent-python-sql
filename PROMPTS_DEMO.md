# 🎯 Guía de Prompts para Demo del Agente AIOps

Esta guía contiene prompts probados para demostrar las capacidades del agente de análisis AIOps.

---

## 📊 NIVEL 1: Consultas Básicas SQL (Tablas Simples)

### **Alertas Básicas**

```
Muéstrame las últimas 10 alertas activas
```

```
¿Cuántas alertas tenemos por cada nivel de severidad?
```

```
Dame las alertas críticas (severidad 6) que están sin resolver
```

```
Muéstrame las 5 alertas más antiguas que siguen abiertas
```

```
¿Qué equipos tienen más alertas activas?
```

```
Muéstrame las alertas del owner 'rfadul'
```

### **Incidentes Básicos**

```
Muéstrame los últimos 15 incidentes
```

```
¿Cuántos incidentes tenemos abiertos vs resueltos?
```

```
Dame los incidentes con prioridad alta que están sin resolver
```

```
¿Qué equipos tienen más incidentes abiertos?
```

```
Muéstrame los incidentes del último mes
```

```
¿Cuántos incidentes se crearon esta semana?
```

---

## 📈 NIVEL 2: Análisis con Gráficos (Python + Visualización)

### **Análisis de Alertas**

```
Muéstrame un gráfico de la distribución de alertas por severidad
```

```
Crea un gráfico de barras con los 10 recursos que tienen más alertas
```

```
Dame un gráfico de pastel mostrando el porcentaje de alertas por estado (activas vs cerradas)
```

```
Muéstrame la evolución de alertas en los últimos 30 días (gráfico de líneas)
```

```
Crea un gráfico de barras horizontales con los equipos que tienen más alertas críticas
```

```
Dame un gráfico comparando alertas activas vs cerradas por cada nivel de severidad
```

### **Análisis de Incidentes**

```
Muéstrame un gráfico de la distribución de incidentes por prioridad
```

```
Crea un gráfico con los 10 owners que tienen más incidentes asignados
```

```
Dame un gráfico de la evolución de incidentes en el último mes
```

```
Muéstrame un gráfico de barras con los equipos que tienen más incidentes sin resolver
```

```
Crea un gráfico comparando incidentes por estado (open, in progress, resolved)
```

### **Análisis Temporal**

```
Muéstrame la tendencia de alertas de los últimos 7 días
```

```
Crea un gráfico que muestre cuántas alertas se generaron por día en la última semana
```

```
Dame un gráfico de líneas con la evolución de incidentes por semana en el último mes
```

```
Muéstrame un gráfico comparando alertas y eventos por día (últimos 10 días)
```

---

## 🚀 NIVEL 3: Análisis Avanzado (Múltiples Queries + Exportación)

### **Análisis de Recursos Críticos**

```
Dame un análisis completo de los 5 recursos con más alertas:
1. Tabla con el ranking
2. Gráfico de barras
3. Exportar los datos detallados a CSV
```

```
Analiza qué recursos tienen alertas críticas (severidad 6):
- Muéstrame una tabla con el top 10
- Crea un gráfico de barras
- Exporta todos los recursos con alertas críticas a CSV
```

### **Análisis de Equipos**

```
Dame un análisis por equipo:
1. Ranking de equipos por cantidad de alertas
2. Gráfico de barras comparativo
3. CSV con el detalle completo de alertas por equipo
```

```
Analiza la carga de trabajo por equipo:
- Tabla con alertas activas y cerradas por equipo
- Gráfico de barras apiladas
- Exporta los datos a CSV
```

### **Análisis de Severidad y Estados**

```
Crea un análisis de severidad completo:
1. Tabla con conteo por cada nivel de severidad
2. Gráfico de pastel mostrando porcentajes
3. Gráfico de barras con comparación activas vs cerradas
4. Exporta los datos a CSV
```

```
Dame un análisis de estados de alertas:
- Gráfico de barras comparando activas, cerradas y acknowledged
- Tabla con porcentajes
- CSV con el detalle de alertas por estado
```

### **Análisis de Incidentes Avanzado**

```
Analiza los incidentes sin resolver:
1. Tabla con top 10 más antiguos
2. Gráfico de barras por owner
3. Gráfico de pastel por prioridad
4. Exporta todos los datos a CSV
```

```
Dame un análisis de rendimiento de resolución de incidentes:
- Tabla con tiempo promedio de resolución por equipo
- Gráfico de barras comparativo
- CSV con todos los incidentes resueltos del último mes
```

### **Análisis Temporal Complejo**

```
Crea un análisis de evolución de alertas:
1. Gráfico de líneas: alertas por día (últimos 30 días)
2. Gráfico de barras: comparación semanal
3. Tabla con estadísticas (promedio, máximo, mínimo)
4. Exporta los datos diarios a CSV
```

```
Dame un análisis temporal de incidentes:
- Gráfico de líneas con tendencia de creación de incidentes (último mes)
- Gráfico de barras con resolución de incidentes por semana
- Tabla comparativa
- CSV con datos completos
```

### **Exportación Masiva de Datos**

```
Necesito exportar datos para un reporte:
1. CSV con todas las alertas críticas del último mes
2. CSV con todos los incidentes abiertos
3. Gráfico resumen de ambos
```

```
Genera un paquete de datos para análisis externo:
- CSV de alertas por recurso (top 50)
- CSV de incidentes por equipo
- Gráfico de dispersión mostrando recursos vs alertas
```

### **Análisis Multi-Dimensional**

```
Dame un análisis completo del estado actual del sistema:
1. Gráfico: Distribución de alertas por severidad
2. Gráfico: Top 10 recursos con más alertas
3. Gráfico: Evolución de alertas en los últimos 7 días
4. Tabla: Resumen por equipo
5. CSV: Datos completos de alertas activas
```

```
Crea un dashboard de incidentes:
1. Gráfico de pastel: Distribución por prioridad
2. Gráfico de barras: Top 10 owners con más incidentes
3. Gráfico de líneas: Tendencia de los últimos 15 días
4. Tabla: Resumen de estados
5. CSV: Exportación de todos los incidentes
```

### **Análisis de Comparación**

```
Compara el comportamiento de alertas entre equipos:
- Gráfico de barras agrupadas por equipo y severidad
- Tabla con estadísticas por equipo
- CSV con el detalle completo
```

```
Analiza la diferencia entre alertas activas y cerradas:
1. Gráfico de barras comparativo por severidad
2. Gráfico de líneas con tendencia temporal
3. Tabla con porcentajes
4. CSV con datos para cada categoría
```

---

## 🎨 NIVEL 4: Análisis con Múltiples Tipos de Gráficos

### **Combinaciones de Gráficos**

```
Crea un análisis visual completo de alertas con:
- Gráfico de barras verticales (alertas por severidad)
- Gráfico de barras horizontales (top 10 recursos)
- Gráfico de pastel (distribución por estado)
- Gráfico de líneas (evolución temporal)
```

```
Dame un análisis multi-gráfico de incidentes:
1. Gráfico de dispersión (scatter): relación entre prioridad y tiempo de resolución
2. Gráfico de barras apiladas: incidentes por equipo y estado
3. Gráfico de líneas: tendencia de creación vs resolución
4. Histograma: distribución de tiempo de vida de incidentes
```

### **Gráficos de Correlación** (sin join directo entre tablas)

```
Compara patrones entre alertas e incidentes (sin correlación directa):
1. Gráfico de barras: Top 10 recursos con más alertas
2. Gráfico de barras: Top 10 equipos con más incidentes
3. Tabla comparativa de volúmenes por equipo
```

```
Analiza la carga operativa:
- Gráfico de líneas: Evolución diaria de alertas (últimos 15 días)
- Gráfico de líneas: Evolución diaria de incidentes (últimos 15 días)
- Gráfico de barras: Comparación de volumen por equipo
- CSV con ambos datasets
```

### **Visualizaciones Especializadas**

```
Crea un heatmap de alertas:
- Por día de la semana y hora del día
- Muestra los patrones de actividad
- Exporta los datos a CSV
```

```
Dame un análisis de treemap:
- Alertas agrupadas por equipo y severidad
- Muestra proporciones visuales
- Tabla de resumen
```

### **Gráficos de Series Temporales**

```
Analiza las series temporales de alertas:
1. Gráfico de área: Volumen de alertas por día
2. Gráfico de líneas múltiples: Cada línea es un nivel de severidad
3. Gráfico de barras: Promedio semanal
4. CSV con datos completos por día y severidad
```

```
Crea un análisis de tendencias:
- Gráfico de líneas con media móvil de 7 días de alertas
- Gráfico de barras con comparación semana actual vs anterior
- Predicción visual de tendencia
- CSV con datos históricos
```

---

## 💡 TIPS PARA PROMPTS EFECTIVOS

### ✅ Buenos Prompts (Específicos y Claros)
- "Muéstrame las alertas críticas del equipo X"
- "Dame un gráfico de barras con los 10 recursos con más alertas"
- "Analiza la evolución de incidentes en los últimos 30 días"

### ❌ Prompts Vagos (Menos Efectivos)
- "Muéstrame algo de alertas"
- "Haz un gráfico"
- "Dime qué está pasando"

### 🎯 Estructura Recomendada para Prompts Complejos
```
[Objetivo] + [Tipo de visualización] + [Filtros específicos] + [Formato de salida]

Ejemplo:
"Analiza las alertas críticas (severidad 6) del equipo DevOps en 
los últimos 7 días, muéstrame un gráfico de barras y exporta los 
datos a CSV"
```

---

## 🧪 Prompts para Testing

### **Test de Manejo de Errores**
```
Muéstrame datos de la tabla que no existe XYZ123
```

```
Dame las alertas con un campo inventado llamado 'unicornio'
```

### **Test de Límites**
```
Muéstrame TODAS las alertas del sistema (sin límite)
```

```
Dame un análisis con 20 gráficos diferentes
```

### **Test de Complejidad**
```
Crea un análisis que incluya:
1. Alertas por severidad (gráfico de pastel)
2. Top 15 recursos con más alertas (gráfico de barras)
3. Evolución de alertas por día (últimos 30 días, gráfico de líneas)
4. Comparación de alertas por equipo (gráfico de barras horizontales)
5. Distribución de estados (gráfico de dona)
6. Exportar todos los datos a 3 CSVs separados
```

---

## 📋 Checklist de Demo

- [ ] **Consulta básica de alertas** (Nivel 1)
- [ ] **Consulta básica de incidentes** (Nivel 1)
- [ ] **Gráfico simple de distribución** (Nivel 2)
- [ ] **Análisis temporal con gráfico de líneas** (Nivel 2)
- [ ] **Análisis multi-gráfico** (Nivel 3)
- [ ] **Exportación de CSV** (Nivel 3)
- [ ] **Análisis completo con múltiples queries** (Nivel 4)
- [ ] **Manejo de errores** (Testing)

---

## 🚀 Recomendación de Orden para Demo

1. **Empezar Simple**: "Muéstrame las últimas 10 alertas"
2. **Añadir Filtro**: "Dame las alertas críticas"
3. **Primer Gráfico**: "Muéstrame la distribución de alertas por severidad"
4. **Análisis Temporal**: "Evolución de alertas en los últimos 7 días"
5. **Análisis Complejo**: "Top 10 recursos + gráfico + CSV"
6. **Multi-Gráfico**: "Dashboard con 4 gráficos diferentes"
7. **Wow Factor**: "Análisis completo del sistema con todos los gráficos y CSVs"

---

**Última actualización**: 2025-11-14
**Compatibilidad**: Cloud Pak for AIOps DB2 Schema (REPORTER.DB2INST1)





BUENO: 


Hazme un gráfico que ordene alertas por fecha y eventtype de los últimos 90 días para el sender Instana Webhook

que en el eje X sea fecha Y cantidad de alertas, y muestre el gráfico por eventtype

Puedes hacerlo como gráfico de barra apilado para todas las fechas?


