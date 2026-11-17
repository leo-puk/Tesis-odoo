# R2 Información local de migración de Odoo 0.2

Aplicación determinista para construir y consultar información de cambios entre versiones de Odoo. No utiliza IA, embeddings ni generación de resúmenes por modelos. Python 3.12 y NetworkX real son el entorno de referencia; el BFS alternativo se identifica solo como compatibilidad.

La autoridad metodológica es la tesis (Tabla 3, Tabla 4, 1.3.1, 1.3.3.1 y 1.3.4). El Word no se modifica. El alcance actual y sus brechas están en audit/TRAZABILIDAD.md y audit/INFORME_CUMPLIMIENTO.md; no se afirma cumplimiento académico total ni C1 ≥ 90 %.

## Documentos actuales

- docs/REPRODUCCION.md: entorno limpio, instalación fijada y comandos.
- docs/MANUAL_CODIFICACION.md: unidades, categorías, condiciones, revisión, identidades y grafo.
- docs/PROTOCOLO_EVALUACION.md: muestra, congelación, juicios, fórmulas, V1 y tiempos.
- audit/sources-inventory.json y assignments.json: fuentes/exclusiones auditables.
- audit/selection-status.json: bloqueos concretos de la evaluación independiente.
- audit/environment.json y registros de pruebas: herramientas efectivamente ejecutadas.
- docs/README-v010-historical.md: documentación anterior, conservada exclusivamente como historial.

## Uso local

```powershell
.\r2.ps1 doctor
.\r2.ps1 --help
.\r2.ps1 query examples/original_module --module-name sale_advance_payment --db examples/output/v020-demo/reviewed.sqlite --from 16.0 --to 17.0 --status verified --format json --timing-log audit/cli-timing.jsonl
```

El lanzador usa primero .venv o R2_PYTHON. Las bases de 0.1 deben reconstruirse: el esquema actual es 2 y las revisiones exigen evidencia de vigencia. No se reutiliza una colección contaminada cambiando un flag.

## Arquitectura efectiva

La recolección desde internet está separada en [r2/adquisition](r2/adquisition/README.md): transporte HTTP, fuentes documentales, metadatos GitHub y procedencia. La conversión textual está en `r2/normalization.py`; la lectura local de Git/snapshots permanece en `collection.py`. `acquire.py` conserva las importaciones anteriores como compatibilidad. Los hashes del informe de auditoría identifican la entrega previa a esta refactorización.

Recolección HTTP/Git y procedencia → extracción estática → conversión/codificación → SQLite → cruce de identidades → grafo multiorigen → filtro/orden → primera vista y resumen. El evaluador es independiente del índice.

Comandos: capture-plan, github, build, scan, query, inventory, export, show, validate-output, sample, freeze, evaluate y doctor. La API GitHub recoge metadatos de selección sin indexar soluciones; Git local se fija por SHA. Capturas HTTP conservan originales y texto normalizado con hashes distintos.

El modelo separa sources, comparisons, evidence, changes, elements y relations; change_evidence admite relaciones muchos-a-muchos. Las revisiones conservan historial y categoría. Verified requiere responsable, fecha, condiciones o generalidad justificada y evidencia de vigencia en el salto. No es una prueba automática de incompatibilidad.

Las declaraciones y referencias son diferentes. Los XML-ID son cualificados por módulo. self.x se resuelve como campo/método solo si hay evidencia estática. El grafo conserva todas las evidencias por arista y usa networkx.bfs_layers; cada relación añade una unidad y los enlaces de almacenamiento a la evidencia no alteran la distancia.

BM25 indexa solo título, elementos afectados y texto añadido/eliminado de las evidencias. No indexa el JSON administrativo. Comparte colección, unidad, consultas, salto, capa, estado y límite; no expande relaciones.

La salida está en inglés, incluye hasta diez cambios distintos y resumen del conjunto encontrado por capa, profundidad y estado. Mantiene fuentes/revisiones, condiciones, elementos, caminos y evidencias agrupadas. V1 automático se distingue de revisión lingüística y pertinencia humana. Tiempos internos, hasta serialización y hasta completar stdout se registran por separado.

Pandas crea y exporta tablas del evaluador; scikit-learn calcula P1 y C2 cuando sus unidades coinciden exactamente con los cocientes definidos. Vacíos/no aplicables se protegen antes del cálculo. No se aplican McNemar/Wilson a R2 por obligación de usar statsmodels; la discrepancia literal de Tabla 4 se documenta fuera del Word.

## Alcance del corpus y evaluación

La captura progresiva actual contiene nueve fuentes parciales para 16→17, 17→18 y 18→19. No es un corpus completo. La muestra independiente aún carece de corte confirmado, marco auditado, seis criterios revisados y responsables/juicios reales. Los casos inspeccionados, incluido sale_advance_payment, no pueden formar parte de la evaluación final.

La demostración revisada y las pruebas sintéticas verifican funcionamiento del software, no cobertura ni superioridad académica. JavaScript/Owl, transformación y equivalencia funcional siguen fuera de R2. El piloto histórico usó código adaptado, pruebas en otra base y no demostró equivalencia: sus tiempos no son T1 de R2.
