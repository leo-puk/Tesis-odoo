# Entrega de integración R2 0.3

Integración ejecutada el 16 de noviembre de 2026. El componente final del usuario permanece en `r2/adquisition`: sus nueve archivos coinciden byte a byte con el registro previo al movimiento. El Word conserva su SHA256 original. La comprobación reproducible está en integration-030-state.json y adquisition-final-baseline.json.

## Resultado implementado

- La CLI exige catálogo en capture-plan y bindings externos en build. delete-units invoca la eliminación final. La CLI propia del componente también funciona con python -m r2.adquisition.
- Ingestión offline de unidades accepted, exclusión de otros estados, validación de rutas y asignación externa de versiones/referencias.
- Conversión de diffs textuales y PR JSON; contexto documental y manifiestos separados de los cambios. No se crean cambios a partir de comentarios ni de diferencias artificiales entre vacío y documento.
- SQLite esquema 3 conserva fuentes, archivos completos consumidos, documentos, elementos, relaciones, cambios y evidencias. Las consultas y exportaciones siguen funcionando tras eliminar temporales.
- Motor de consulta estructural y BM25 adaptado a esquema 3; conserva lectura de esquema 2. Se mantienen anotaciones, agrupación de evidencias y evaluación de ingeniería.
- Cliente de selección académica aislado en evaluation_sources, con proyección de metadatos sin soluciones. La política fija final no tiene interruptor de inclusión OCA. Las llamadas antiguas que intenten habilitarlo fallan.
- Las bases anteriores no se sobrescribieron. build-legacy se reserva explícitamente a reconstrucción local histórica, con metadata diferenciada; no es admisión por catálogo.

## Verificación ejecutada

67 pruebas aprobadas: 21 originales del componente final, 33 de regresión y 13 de nueva integración. El adaptador externo ejecuta las pruebas originales contra el paquete activo sin modificarlas. Registro completo: integration-030-tests.txt.

La demostración examples/output/v030-session creó dos unidades sintéticas, una colección con un candidato de diff, un documento contextual y una salida estructural conforme. No se conectó a internet. run.json y query.json conservan el resultado. Las pruebas también verificaron PR completos, consulta BM25, persistencia tras borrado, versiones ausentes, diffs truncados y rutas inseguras.

Se construyó un wheel 0.3.0 sin acceso a índices ni resolución de dependencias. La importación aislada desde el wheel confirmó los paquetes adquisition, ingestion y conversion. Los archivos Python finales dentro del wheel conservan los mismos hashes; no incorpora archivos de reference, archive ni research.

## Límites conservados

No se ejecutaron capturas reales ni una migración. El catálogo real requiere revisión y el ejemplo mantiene allowed_urls vacío. Los hunks no reconstruyen archivos completos; el grafo puede carecer de anclas o relaciones fuera de ellos. Documentos convertidos no equivalen a originales HTTP; los hashes nuevos identifican artefactos consumidos por ingestión.

La evaluación independiente, corpus completo, responsables, juicios y decisiones académicas no se declaran terminados. Las colecciones nuevas no reciben assignment_audited por estar accepted: antes de una evaluación académica necesitan auditoría independiente y conexión explícita de ese registro. --development sirve únicamente a comprobaciones de ingeniería.

Los informes anteriores conservan los estados de sus entregas. Esta integración no redefine retrospectivamente sus capturas ni resultados.

## Lectura y ejecución

- ../docs/INTEGRACION_ADQUISITION.md: contratos, almacenamiento y límites.
- ../docs/REPRODUCCION.md: comandos vigentes.
- ../examples/run_session_demo.py: demostración sintética reproducible.
- ../reference/adquisition-final: entrega original del usuario.
- ../archive/adquisition-v020: implementación anterior.
