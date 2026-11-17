# Verificación de R2 0.1.0

Documento histórico. La verificación actual de 0.2 está en audit/INFORME_CUMPLIMIENTO.md, audit/tests-networkx.txt, audit/tests-clean-environment.txt y audit/tests-compatibility.txt. No se atribuyen a 0.2 las cifras anteriores.

Actualizada el 14 de noviembre de 2026. Se distinguen pruebas de software, demostración de desarrollo y evaluación académica pendiente.

## Entornos

Las nueve pruebas iniciales pasaron en Python 3.12.15, NetworkX 3.7 y lxml 6.1.3 dentro del entorno virtual /tmp/r2-venv del contenedor de control. Dos intentos posteriores de construir la colección mediante Docker no se ejecutaron: la revisión automática de permisos agotó su plazo. No se atribuye ese timeout a un fallo del programa.

Se continuó con el Python 3.12.14 local del runtime disponible, con lxml y sin NetworkX. Se implementó una alternativa BFS explícita y se comprobó también el cierre de conexiones SQLite en Windows. Las pruebas finales corresponden al código actual y a ese entorno local. El método de grafo utilizado queda registrado en la salida.

## Pruebas finales

Comando: python -m unittest discover -s tests -v.

Resultado final: 11 pruebas correctas, 0 fallos y 0 errores, en Windows con Python 3.12.14 y BFS alternativo. El lanzador r2.ps1 ejecutó además la consulta real y validate-output devolvió conformant=true. La salida comprobada se conserva en examples/output/final-query.json.

Casos: estabilidad de colección, trazabilidad, versiones, BM25 sin recorrido, BFS multiorigen/ciclos/límites, exclusión MIG/FIX y descendientes, política incompatible, no ejecución del módulo, referencias dinámicas, XML/DTD/sintaxis, construcción inmutable, filtro verificado, máximo diez y resumen completo, fórmulas con juicios sintéticos, vacíos y N/A, extremo correcto del camino revisado y agrupación semántica de dos bloques conservando ambas evidencias.

## Demostración real

Inventario examples/manifest.json: dos archivos del núcleo Odoo de las imágenes locales 16 y 17, fijados por procedencia y SHA256. Entrada: examples/original_module, copia de consulta del módulo sale_advance_payment en su revisión de origen 16. No se importa, ejecuta ni modifica ese módulo. Las soluciones OCA MIG/FIX no alimentan la colección.

La construcción extrae 158 bloques candidatos. El script examples/run_demo.py incorpora dos revisiones explícitas de desarrollo, una sobre states en Field.setup y otra sobre attrs/states en el validador de vistas. No son revisiones independientes y no acreditan exhaustividad semántica del resto del corpus. Con --status verified, ambos motores recuperan los dos cambios; sus respuestas pasan la validación estructural V1. Que ambos motores recuperen dos ejemplos conocidos no demuestra que uno supere al otro.

Los cambios conservan el bloque completo de evidencia y affected_elements restringe el camino a la parte interpretada por el revisor. Esto evita usar readonly como extremo de un hallazgo revisado sobre states solo porque ambos aparecen en el mismo bloque.

No se ejecutó una nueva migración ni una comprobación funcional de origen/destino durante la construcción de R2. La ejecución de migración anterior está documentada aparte. Esta entrega verifica la consulta determinista de información, no R3 ni R4.

## Pendientes de aceptación académica

Colección completa y fuentes congeladas 16–19, responsables y juicios de pertinencia, correspondencia independiente con cambios evaluables, treinta migraciones de evaluación excluidas de ajuste, mediciones repetidas bajo condiciones de caché controladas y revisión de aplicabilidad. No se afirma C1 ≥ 90 %, superioridad frente a BM25 ni equivalencia funcional.
