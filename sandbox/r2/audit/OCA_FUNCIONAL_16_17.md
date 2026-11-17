# Prueba funcional OCA 16→17

Resultado: aprobada. Ejecución del 16 de noviembre de 2026. La suite completa posterior pasó 71 pruebas, incluidas las 21 originales del componente final, la prueba OCA y tres comprobaciones de extracción por tokens. Registro: oca-functional-16-17-tests.txt.

## Entrada y simulación

Se utilizó sale_advance_payment 16.0.1.0.0, de OCA/sale-workflow, tal como está en examples/original_module. Su código, manifiesto y hashes quedaron intactos. Ya era un caso de desarrollo excluido de evaluación final; esta prueba no incorpora un caso nuevo a la muestra académica.

La respuesta HTTP del compare oficial se reemplazó por un unified diff calculado entre dos snapshots locales reales de Odoo 16 y 17: odoo/fields.py e ir_ui_view.py. La procedencia histórica de esas imágenes y hashes de ambos archivos se conserva en report.json. No se afirma que este fixture sea una respuesta obtenida del endpoint compare de GitHub: se simula el transporte y se documenta su procedencia local.

Las dos anotaciones de revisión son entradas mock explícitas del test. No son verificación automática ni juicios independientes. La comprobación de recuperación distingue los candidatos sin revisar de los dos cambios seleccionados mediante esas anotaciones.

## Resultados observados

- La captura oficial simulada se aceptó. Una URL OCA de control, usada solo como sentinel de exclusión y no como PR real de migración, se rechazó antes de cualquier petición.
- Se construyeron 158 hunks candidatos desde el diff. No equivalen a 158 incompatibilidades.
- La consulta inicial por grafo sobre el módulo recuperó 19 candidatos y mostró diez. No se evaluó la pertinencia de los diecinueve.
- Tras cargar la revisión mock, grafo y BM25 devolvieron exactamente los dos cambios esperados, con procedencia y condiciones: property:states y xml-attribute:attrs.
- En models/payment.py, línea 12, el módulo utiliza states en Many2one. El código destino del núcleo incluye una advertencia de que esa propiedad ya no está soportada. La prueba no convierte esa advertencia en un fallo fatal.
- En views/sale_view.xml, línea 14, utiliza attrs. El validador destino incluye un rechazo de attrs/states con ValidationError.
- Un módulo de control sin esas condiciones devolvió cero hallazgos revisados. Consultar el salto 17→18 también devolvió cero para esa colección.
- La consulta siguió recuperando los dos cambios después de borrar las unidades temporales mediante la API final.
- El módulo OCA solo se analizó como entrada: no se indexaron soluciones OCA. Los nueve archivos de adquisición final permanecen idénticos al baseline.

## Limitación encontrada y corrección

El análisis previo de los hunks reales mostró que el extractor dependiente de clases AST completas no producía anclas para los dos cambios esperados. Se corrigió fuera de adquisición, en conversion/anchors.py y conversion/units.py.

El complemento usa tokens locales para propiedades de la API de campos en sus rutas conocidas y atributos presentes en argumentos literales de xpath. No inventa clases, dueños o relaciones ni reconstruye archivos. La procedencia de esas anclas se registra explícitamente. Hay pruebas con atributos ajenos al ejemplo y controles de comentarios, cadenas de texto y expresiones dinámicas.

## Artefactos y reproducción

- ../examples/run_oca_functional_test.py: ejecución reproducible con --output NUEVA_CARPETA.
- ../tests/test_oca_functionality.py: regresión automatizada del caso real con transporte simulado.
- ../tests/test_partial_anchors.py: controles de la corrección del extractor.
- ../examples/output/oca-functional-16-17/REPORT.md: resumen de la ejecución conservada.
- ../examples/output/oca-functional-16-17/report.json: datos, condiciones, hashes y comprobaciones.
- ../examples/output/oca-functional-16-17/query-graph.json y query-bm25.json: salidas completas.
- ../examples/output/oca-functional-16-17/query-candidates.json: consulta previa a la revisión mock.
- ../examples/output/oca-functional-16-17/mock-response.diff: diff real local servido por el mock.
- oca-functional-16-17-state.json: integridad y hashes del código de esta comprobación, posteriores a la entrega de integración anterior.

Esta es una prueba de software de recuperación y sus conexiones. No se arrancó Odoo, no se ejecutaron las pruebas del addon, no se modificó o migró su código y no se acreditó equivalencia funcional. No constituye medición académica de precisión o cobertura ni acredita detección de todos los cambios necesarios para migrar el módulo.
