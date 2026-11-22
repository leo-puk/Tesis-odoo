# Protocolo de evaluación de R2

## Casos y muestra de migraciones

El lote operativo contiene treinta casos, diez para cada salto entre Odoo 16,
17, 18 y 19. Cada caso analiza cinco addons y produce cinco consultas. El
catálogo reutiliza addons entre saltos, por lo que estas consultas pueden
compartir código, dependencias y correcciones.

La muestra objetivo contiene treinta SHA MIG distintos. Después de admitir
las correcciones y antes de calcular las métricas finales, `freeze-sample`
selecciona diez por salto mediante orden de SHA. La selección usa admisión
técnica, salto y SHA. Las puntuaciones de Graph y BM25 quedan fuera de esa
decisión. El archivo fija las referencias admitidas de los MIG seleccionados,
las consultas asociadas y las huellas de las revisiones. El alcance de la
muestra debe acompañar la interpretación de los resultados.

## Adquisición y referencias

R2.1 reúne documentación y guías públicas, un diff local filtrado del núcleo
y diffs acotados de repositorios OCA auxiliares. Los selecciona a partir de
dependencias, identificadores y rutas. La planificación registra URL, SHA,
alcance y fallos. Las fuentes de evaluación se conservan en un dossier separado.

Antes de adquirir las fuentes se identifican candidatos `[MIG]` y `[FIX]`
del historial destino respecto de origen, en los repositorios evaluados y
en los adicionales del catálogo. Sus parches se archivan para el juicio.
El lote excluye PR y commits individuales, los repositorios de referencia
del plan y los SHA de los candidatos conocidos del caso. Se admiten parches
de otros addons como referencia si explican
una incompatibilidad aplicable al salto y se justifica su relación con un addon
evaluado mediante uso o dependencia. Cada candidato conserva repositorio,
SHA, URL y parche. El alcance cubre los repositorios y revisiones registrados.

Se cuenta una corrección por incompatibilidad técnica. Varios hunks o commits
pueden sustentar una misma corrección. Los cambios administrativos, las
traducciones y los ajustes puramente mecánicos se excluyen con motivo. Un
parche breve puede resolver una incompatibilidad real.

## Juicios de pertinencia y correspondencia

El asistente identifica primero las correcciones a partir de los parches y
del código de los addons. Después revisa la colección para C1 y la unión de
unidades mostradas por ambos motores para P1 y C2. Se registran capa afectada,
componente, motivo e incertidumbre. Para cada vínculo de cobertura, el
asistente explica cómo la unidad muestra el cambio técnico del salto que
justifica la adaptación observada en el MIG o FIX. Una alerta genérica o
una coincidencia de identificador son pistas de revisión. Una sección de documentación puede explicar una
incompatibilidad de Python o XML. La pertinencia de una unidad se puede
acreditar por su utilidad para el addon aunque carezca de corrección asociada.

El importador valida integridad, alcance, completitud y vínculos. Los casos
dudosos conservan una decisión explícita y su incertidumbre. Las sugerencias
por identificadores orientan la revisión. Se registra la asistencia de IA y
quién emitió cada juicio.

## Comparación y métricas

Graph y BM25 consultan las mismas unidades elegibles con el mismo addon,
salto y límite. Graph utiliza el recorrido por identidades técnicas. BM25
utiliza puntuación léxica. La vista muestra hasta diez unidades por consulta.
Para la revisión operativa se reúnen hasta diez URL distintas por motor y caso.

- **C1** mide el porcentaje de correcciones admitidas que tienen evidencia
  en la colección. Una corrección sin evidencia permanece en el denominador.
- **C2** mide el porcentaje de correcciones esperadas que explican las unidades
  pertinentes de la primera vista por motor.
- **P1(q)** es 100 × unidades pertinentes mostradas / unidades mostradas
  para la consulta q. Una vista vacía deja P1 indefinida.
  [Definición de precisión en Saito y Rehmsmeier (2015)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432).
- **Cobertura por commit** distingue cobertura total, parcial o ausente según
  cuántas correcciones del MIG o FIX tienen evidencia. El indicador binario es
  positivo con cobertura total. La muestra conserva ese desglose para la
  colección y para las primeras vistas de ambos motores.

La meta principal es que la media P1 por consulta de addon de Graph supere
a BM25 en la muestra congelada. Cada consulta asociada cuenta una vez cuando
ambas vistas tienen P1 definida. El informe conserva las dos medias, su
diferencia y el número de pares. La instrumentación también conserva tiempos
por etapa y los límites de cada medición.

Los comandos y la ubicación de los artefactos están en
[Ejecución incremental y evaluación de R2](EVALUACION_FINAL.md).
