# Matriz de trazabilidad R2

Autoridad: Word de tesis, Tabla 3, Tabla 4, 1.3.1, 1.3.3.1 y 1.3.4, leído el 14 de noviembre de 2026. SHA256 inicial del Word: 317B8F1E37EE0D8A63181451C7205D43B06C4412B8A48A8A5414FD4831898D57. No se autoriza modificarlo. El backlog no sustituye esos requisitos.

Revisión Git inicial del repositorio `repo odo`: 9ee4dbd9f2279c3f45620d6691131a39c4db608a. Había modificaciones del usuario en sandbox/.gitignore y control/odoolab/cli.py y archivos no seguidos en control, research y r2. No se revierten ni se incorporan a un commit ajeno. R2 estaba íntegramente no seguido: la revisión Git de base no identifica por sí sola su contenido; se registra además un manifiesto de hashes antes/después.

Tipos: I = brecha frente al requisito; L = limitación compatible declarada; E = mejora de ingeniería; A = evaluación académica pendiente; D = discrepancia que requiere decisión académica. Estado inicial significa inspeccionado antes de editar código para este encargo. El cierre requiere la evidencia indicada, no una declaración de README.

| ID | Requisito / ubicación tesis | Componente y método/herramienta | Implementación inicial | Tipo y brecha | Corrección prevista | Evidencia de aceptación | Estado inicial |
|---|---|---|---|---|---|---|---|
| M01 | Artefacto y evaluación, 1.3.1 | Paquete y auditoría, ciencia del diseño | Prototipo 0.1 con 11 pruebas | A: pruebas no son evaluación académica | Conservar pruebas y separar evidencia empírica | Matriz, pruebas, protocolo e informe | Parcial |
| M02 | Python 3.12 y NetworkX, Tabla 4 | Entorno aislado y bfs_layers | NetworkX en pruebas históricas; entrega local usa fallback | I: entrega sin NetworkX efectivo | Entorno 3.12 aislado, lock y NetworkX real; fallback solo compatibilidad | Versiones efectivas y pruebas actuales en ambos modos | Pendiente |
| M03 | Git/API GitHub, Tabla 4 y 1.3.4 | Recolección | Git local implementado; REST ausente | I: metadatos de selección no recolectados | Cliente REST paginado y archivos auditables de PR/revisiones/fechas | Pruebas HTTP y captura pública real si accesible | Pendiente |
| M04 | Fuentes 16–19 y revisiones, 1.3.3.1 | Recolección y procedencia | Solo dos archivos de imágenes 16/17 | I/A: corpus limitado, no completo | Capturas oficiales/OCA consumibles, bytes y texto con hashes separados | Inventario, originales, extracción y alcance por salto | Parcial |
| M05 | Independencia, 1.3.3.1 y 1.3.4 | Política | Excluye por split declarado y padres | I: etiqueta no justifica asignación | Registro de asignación, exclusiones por caso/módulo, corte y criterios con evidencias | Rechazo previo a leer fuente reservada y registro auditable | Parcial |
| M06 | Muestreo 30, 10/salto, 1.3.4 | Selección | No existe | A: criterios humanos y marco no disponibles | Flujo estratificado reproducible con reemplazos y faltantes | Registro de selección sin inventar revisores/criterios | Pendiente |
| M07 | Análisis de contenido, 1.3.3.1 | Modelo/codificación | Bloque candidato + anotación sencilla | I: verified no comprueba vigencia ni condiciones generales explícitas | Manual, validación de revisión, historial, fuentes/comparaciones/evidencias separadas | Casos negativos y positivos del modelo | Parcial |
| M08 | Cambios distintos y evidencia, 1.3.3.1 | Modelo | Varios bloques agrupables, un cambio/bloque | I: falta varios cambios por evidencia | Revisiones con IDs semánticos y referencias a evidencia M:N | Dos cambios sobre un bloque y uno sobre varios | Parcial |
| M09 | Elementos Python, 1.3.3.1; ast es reutilización de Tabla 4/R4 | Extracción | self.x siempre origina método | E/I: identidad incorrecta daña cruce | Declaración/referencia separadas, campo/método conocidos o unresolved | Atributo que no se convierte en método | Pendiente |
| M10 | XML/QWeb/datos/seguridad, 1.3.3.1 | lxml/XPath/csv | XML-ID local sin módulo; QWeb t-call sin arista | I: colisiones y relaciones incompletas | Cualificar IDs, t-call/herencia y grupos/modelos de seguridad | Dos módulos con ID local igual y relaciones verificadas | Pendiente |
| M11 | Profundidad/camino, 1.3.3.1 | Grafo/NetworkX | Todas las ocurrencias son semillas; solo primera evidencia de arista | E/I: definición de raíces y evidencia incompletas | Semillas explícitas; conservar todas las evidencias por arista | BFS multiorigen mínimo, ciclos y trazabilidad completa | Parcial |
| M12 | Vigencia y versiones, 1.3.3.1 | Grafo/filtro | Relaciones de origen; saltos múltiples advertidos | L: no simula transformaciones | Conservar límite, verificar versiones de cada arista y revisión | Tres saltos consecutivos y negativas de versión | Parcial |
| M13 | Orden relevante fijado, 1.3.3.1 | Ranking | Reglas deterministas sin calibración | A: falta congelación y casos independientes | Configuración firmada, corpus de construcción y bloqueo de evaluación no congelada | Fingerprint de parámetros/código/colección/consultas | Pendiente |
| M14 | BM25 misma colección, 1.3.3.1 | FTS5 | Indexa JSON entero | E/I: metadatos alteran coincidencias no justificadas | Lista blanca de campos de contenido; filtros/estado/límite iguales | Texto indexado inspeccionable y paridad de parámetros | Pendiente |
| M15 | Primera vista/resumen, 1.3.3.1 | Presentación | Máximo diez, contadores, JSON/texto | L/E: no distingue candidatos/verificados en resumen | Separar estados; evidencias agrupadas consultables; elemento/condiciones explícitos | Pruebas de contadores y presentación | Parcial |
| M16 | V1, 1.3.3.1 | Validación | Claves/camino básico, sin versiones completas | I: validación estructural limitada | Validación de rangos/versiones/relaciones/contadores; revisión lingüística y semántica humana separada | Salidas corruptas rechazadas y límites documentados | Parcial |
| M17 | C1, Tabla 3 y 1.3.3.1 | Evaluador | IDs existentes y juicio de cobertura | I: no comprueba estado/salto/elemento | Validar cobertura aplicable y verificada, no solo ID | Correspondencias inválidas rechazadas, desglose por módulo/salto | Pendiente |
| M18 | P1/C2, 1.3.3.1 | Evaluador | Fórmulas/vacíos y unión por módulo | I: no expone estado/límite, no registra válidos fuera del MIG | Parámetros compartidos, juicio aplicable y hallazgos extra separados | Casos definidos, vacíos/N/A y unión sin duplicados | Parcial |
| M19 | T1, 1.3.3.1 | Medición | Solo tiempo interno, motores en orden fijo | I/E: presentación y efectos de orden | Medidas internas y hasta serialización/validación, contrabalanceo | Mediciones individuales y entorno/cache | Pendiente |
| M20 | pandas/sklearn/statsmodels, Tabla 4 | Análisis | No utilizados | I/D: no conformidad literal, no justificar con llamadas decorativas | pandas en tablas/exportaciones; sklearn solo fórmula exacta; statsmodels pendiente si R2 no requiere inferencia | Uso efectivo y nota académica, sin McNemar/Wilson forzados | Pendiente |
| M21 | Evaluación independiente, 1.3.3.1/1.3.4 | Protocolo | Solo fixture y demo revisada por desarrollador | A: no hay juicios reales ni 30 casos | Flujo bloquea faltantes; piloto y casos inspeccionados fuera de evaluación | Registro de bloqueos y preparación reproducible | Pendiente |
| M22 | Reproducción | Ingeniería | Dependencias con rangos y config local | E: instalación no congelada | Lock, entorno limpio y comandos auditables | Reconstrucción, Git temporal real, FTS5 y versiones | Pendiente |

Las referencias a Tabla 4 no implican que ast/lxml estuvieran allí asignados originalmente a R2; su reutilización se declara como decisión de implementación. No se exige IA interna, GUI ni migración funcional en R2. El piloto histórico no se reinterpreta como migración autónoma ni sus tiempos como T1.

## Estado de entrega tras la corrección

Esta tabla no sustituye los requisitos anteriores. Distingue aceptación de una corrección técnica y lo que aún requiere datos o decisiones. Evidencia real del corpus no significa pertinencia académica ya juzgada.

| ID | Estado final y evidencia | Pendiente que no se da por cerrado |
|---|---|---|
| M01 | Prototipo corregido, código y hashes, pruebas y reconstrucción | Evaluación académica completa |
| M02 | Verificado: environment.json, environment-reproduced.json, pruebas con NetworkX real; fallback separado | Ninguno para el requisito técnico de entorno |
| M03 | Cliente implementado y ejecutado: github-pilot-metadata y github-window-* | Marco completo de población y revisión de candidatas |
| M04 | Captura e inventario verificables, normalización v2, nueve unidades parciales; source-coverage.csv | Cobertura suficiente, licencias no verificadas y codificación del corpus |
| M05 | Registro de asignación, exclusión antes de lectura y derivados probados; once módulos históricos excluidos | Auditoría completa de casos anteriores y copias ocultas |
| M06 | sample reproducible; 52 entradas reales de una ventana, selection-status.json | Treinta elegibles, diez por salto, seis criterios y corte confirmado |
| M07 | Manual y validación de verified, fechas/condiciones/vigencia e historial probados | Revisión real del conjunto de candidatos |
| M08 | Comparisons/evidence/change_evidence, pruebas M:N y agrupación | Identidad semántica de casos ambiguos requiere codificador |
| M09 | Distinción campo/método/unresolved y resolución entre declaraciones probadas | Inferencia completa de tipos/MRO no se promete |
| M10 | XML-ID cualificado, QWeb, herencia y seguridad probados | Arquitectura combinada y referencias dinámicas no se validan estáticamente |
| M11 | BFS real, mínimo, ciclos y múltiples evidencias de arista probados; demostración actual | Auditoría semántica exhaustiva del grafo |
| M12 | Pruebas de tres saltos y rechazo de versiones incompatibles | Saltos múltiples no simulan código intermedio |
| M13 | Parámetros explícitos y freeze con rechazo de faltantes | Calibración de construcción y congelación académica final |
| M14 | Lista blanca BM25, configuración compartida y prueba que excluye metadatos | Comparación empírica de pertinencia |
| M15 | Presentación, contadores por estado, fuentes/evidencias y máximo diez probados | Interpretación de candidatos y títulos revisados del corpus completo |
| M16 | V1 automático ampliado con alcance explícito; salida actual validada | Inglés libre, autenticidad y semántica necesitan revisión humana |
| M17 | Validación C1 de IDs/estado/salto/elementos/condiciones y casos negativos | Matriz de cobertura independiente real |
| M18 | Fórmulas/vacíos/parámetros/unión/extras implementados; sklearn en pruebas | Juicios P1/C2 reales y agregación ratificada |
| M19 | Medidas internas/serialización/CLI, contrabalanceo y registros individuales | Procedimiento de caché y límite operacional ratificados |
| M20 | pandas y sklearn utilizados de forma pertinente y efectiva | statsmodels: discrepancia académica documentada; no se fuerza inferencia |
| M21 | Protocolo, selección, templates y bloqueos concretos | Sin responsables/juicios reales no se ejecuta evaluación oficial |
| M22 | Lock, segundo entorno limpio, instalación y reconstrucción con igual revisión | No se exige un entorno Docker ni se confunde con reproducibilidad científica completa |

Los informes de pruebas son evidencia de software. No acreditan C1 ≥ 90 %, P1/C2 reales, superioridad frente a BM25 ni equivalencia funcional. El estado anterior de 0.1 se conserva como antecedente en docs/README-v010-historical.md y el backlog histórico, sin atribuirle estas correcciones.
