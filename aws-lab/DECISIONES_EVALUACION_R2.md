# Decisiones de evaluación de R2

Fecha: 2026-11-21. Decisiones acordadas con el autor de la tesis.
Este documento registra el protocolo elegido; no acredita que la recolección,
los juicios ni la ejecución de las pruebas estén terminados.

## Casos y referencias

- Una prueba es un conjunto de cinco addons analizados en un salto de versión.
- El lote vigente contiene treinta pruebas: diez para 16→17, diez para 17→18 y
  diez para 18→19. Son 150 análisis de addon y salto. Los cincuenta addons
  distintos se reutilizan entre saltos; las observaciones no deben describirse
  como treinta migraciones individuales independientes.
- El autor precisa que el objetivo de la muestra son treinta migraciones MIG.
  El lote es una agenda operativa de casos; no acredita por sí mismo treinta
  MIG independientes. Se comienza por un caso y se avanza por bloques de cinco.
  Se documentan selección, ramas, dependencias, revisiones y fallos. El resumen
  informa por separado los casos y los commits MIG distintos admitidos.
- No se exige al autor aportar una lista previa de treinta commits MIG. Se
  encarga recopilar en Internet los MIG relacionados con los casos del lote.
  El número de MIG puede ser mayor o menor que treinta.
- Se admiten MIG de otros addons cuando correspondan al salto evaluado y se
  justifique su aplicación a alguno de los cinco addons mediante uso,
  dependencia o relación técnica comprobable. Pertenecer al mismo repositorio
  o compartir una palabra no basta para admitir una corrección.
- Cada referencia debe conservar repositorio, URL, SHA, salto, parche y razón
  de admisión o exclusión por caso. Se registrará la fecha y el alcance de la
  búsqueda; no se afirmará exhaustividad sin comprobarla.
- Los parches usados como solución de referencia se conservan separados del
  corpus de recuperación para evitar que las respuestas esperadas alimenten
  el análisis que se está evaluando.

## Unidad de referencia

Se cuenta una corrección técnica por incompatibilidad. Si varios hunks adaptan
el mismo campo eliminado dentro de un addon, forman una sola corrección.
Se excluyen formato, traducciones, tareas administrativas y adaptaciones
puramente mecánicas. La exclusión de una adaptación mecánica debe explicarse;
una modificación breve puede resolver una incompatibilidad real y ser evaluable.
Las referencias repetidas a una misma corrección no aumentan su denominador.

## Juicios de pertinencia y correspondencia

Un juicio es una decisión de evaluación documentada. Para cada unidad devuelta
se decide si es pertinente y qué correcciones de referencia ayuda a explicar.
Para cada corrección se decide también si existe evidencia que la cubra en la
colección completa. Estos registros permiten calcular las métricas.

Una unidad es pertinente cuando su fuente es aplicable al salto, el addon usa
o depende del elemento afectado y se puede explicar qué conviene revisar.
Puede ser pertinente aunque no corresponda a una corrección identificada en
los MIG; en ese caso contribuye a precisión, sin sumar cobertura de referencia.

Los casos dudosos reciben una decisión explícita de pertinencia o no pertinencia,
acompañada de evidencia, motivo y consideración de incertidumbre. No se deja
pendiente un juicio por ser dudoso. Se reconoce que la interpretación adoptada
puede no ser completamente acertada. Una sugerencia léxica de vínculo no equivale
por sí sola a una decisión técnica. Se registra quién realizó cada evaluación
y si recibió asistencia automática, sin atribuir una revisión que no ocurrió.
El autor encarga al asistente emitir esos juicios al final, utilizando el
dossier guardado por cada caso. La revisión se identifica como asistida por IA.

## Comparación y métricas

La comparación elegida es exclusivamente Graph frente a BM25 por unidades,
con el mismo corpus, entrada, salto y límite de resultados. La comparación
contra fuentes completas queda fuera del experimento acordado.

- C1: porcentaje de correcciones de referencia con evidencia admitida en la
  colección. Evalúa la cobertura de la colección, no un ranking de motor.
- P1: porcentaje de unidades mostradas que son pertinentes, por motor.
- C2: porcentaje de correcciones esperadas explicadas por las unidades
  pertinentes de la primera vista, por motor.
- Se conserva el denominador real y el límite de diez resultados por consulta.
  Una vista vacía tiene P1 indefinida; no es un juicio dudoso. Con referencias
  esperadas y sin resultados, la cobertura de recuperación es cero.
- Los tiempos de relaciones y BM25 se registran como información adicional,
  con sus límites de medición explícitos.

## Significado de evaluación preliminar y muestra académica

Evaluación preliminar significa una corrida cuyos resultados aún necesitan
cerrar las referencias, los juicios o la documentación del protocolo.
No implica utilizar otro lote. Muestra académica significa el conjunto de
casos sobre el que la tesis informa resultados y documenta cómo fue elegido.
El mismo lote puede cumplir ambos papeles en momentos diferentes.

## Estado al registrar estas decisiones

El catálogo local confirma treinta pruebas de cinco addons. La búsqueda web
inicial encontró el índice público de migraciones de partner-contact a 17.0,
que incluye partner_affiliate y partner_contact_age_range, presentes en el
primer caso: https://github.com/OCA/partner-contact/issues/1599.
La implementación registra todos los MIG candidatos alcanzables en los
repositorios OCA de los cinco addons para el destino, incluidas otras rutas
de addon, y permite agregar repositorios con un catálogo revisado. Conserva
parches, SHA, URL, alcance y fallos. Se ejecutará la recolección al correr en
EC2; no se afirma que los treinta casos ya tengan referencias recogidas.
El lote nuevo ejecuta exclusivamente Graph y BM25 por unidades. El dossier
`review/` se genera por caso y puede empaquetarse con `review`. Los juicios
completados se importan con `apply-review`; `evaluate` calcula las métricas.
`--require-all --require-migs 30` exige treinta casos ejecutados y al menos
treinta commits MIG distintos admitidos, sin certificar su independencia.
