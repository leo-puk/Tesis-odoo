# Pendientes de R2

Este Markdown conserva los pendientes totales y las últimas decisiones para revisarlos uno por uno. Cruza semánticamente las 31 observaciones originales con las 14 decisiones recientes. Según el criterio solicitado, los puntos ausentes de la última lista se consideran corregidos por cruce; esa ausencia no acredita por sí sola una corrección técnica completa. El detalle distingue avances implementados, límites documentados y validación académica pendiente.

## Pendientes totales del listado original

Listado histórico; algunos puntos ya tienen avances o correcciones.

- **T01.** Unificar la documentación histórica y vigente de entrega.
- **T02.** Implementar la recolección mediante la API REST de GitHub.
- **T03.** Integrar las descargas documentales con el constructor de R2.
- **T04.** Registrar fechas de captura y procedencia de las fuentes.
- **T05.** Completar el corpus de los tres saltos de versión.
- **T06.** Validar el corte temporal y los seis criterios de selección.
- **T07.** Normalizar los XML-ID locales por módulo.
- **T08.** Representar las llamadas entre plantillas QWeb.
- **T09.** Construir relaciones semánticas de seguridad desde CSV.
- **T10.** Distinguir campos y métodos al resolver referencias Python.
- **T11.** Exigir evidencia estructurada de vigencia para cambios verificados.
- **T12.** Permitir relaciones múltiples entre evidencias y cambios semánticos.
- **T13.** Comprobar la generalización con casos reales de construcción.
- **T14.** Distinguir hashes de bytes originales y texto normalizado.
- **T15.** Ratificar las semillas de hallazgos directos e indirectos.
- **T16.** Acreditar la ejecución efectiva de NetworkX.
- **T17.** Conservar todas las evidencias de cada arista.
- **T18.** Calibrar la pertinencia del ordenamiento con casos de construcción.
- **T19.** Distinguir candidatos y cambios verificados en resultados y contadores.
- **T20.** Mostrar elementos, versiones y evidencias completas en la salida textual.
- **T21.** Justificar y congelar los campos documentales de BM25.
- **T22.** Reproducir los parámetros de consulta desde el evaluador.
- **T23.** Resolver el uso metodológico de pandas, scikit-learn y statsmodels.
- **T24.** Validar estado, salto y elemento en las correspondencias de C1.
- **T25.** Reportar separadamente hallazgos pertinentes ausentes del MIG.
- **T26.** Completar la revisión lingüística y autenticidad de evidencias para V1.
- **T27.** Ratificar el límite operacional de T1.
- **T28.** Controlar orden experimental, repeticiones y caché.
- **T29.** Ampliar las pruebas sobre importación, identidades, relaciones y versiones.
- **T30.** Delimitar el alcance probatorio del piloto histórico.
- **T31.** Completar la evaluación independiente y verificar los indicadores de tesis.

## Últimos pendientes

- **P01.** Elegir el modelo y snapshot de R4.
- **P02.** Confirmar el corte documentado y la fecha de separación experimental.
- **P03.** Definir las fuentes generales posteriores al corte admisibles en R2.
- **P04.** Designar al responsable de revisar los seis criterios de selección.
- **P05.** Designar al responsable de los juicios de pertinencia y cobertura.
- **P06.** Designar al responsable de revisar el inglés de las salidas.
- **P07.** Fijar los repositorios y revisiones del corpus de construcción.
- **P08.** Ratificar la definición de consultas y semillas de profundidad cero.
- **P09.** Fijar la profundidad máxima del recorrido.
- **P10.** Calibrar y congelar el ordenamiento utilizando exclusivamente casos de construcción.
- **P11.** Ratificar P1 como promedio de consultas con precisión definida.
- **P12.** Elegir el límite operacional de T1.
- **P13.** Fijar las repeticiones y condiciones de caché para medir tiempos.
- **P14.** Resolver la discrepancia metodológica sobre statsmodels en R2.

## Resueltos o corregidos según el cruce

Veinte puntos originales no aparecen temáticamente en las decisiones recientes. Los matices de cierre se conservan en el detalle.

- **C01 / T01.** La entrega distingue la documentación vigente del material histórico.
- **C02 / T02.** La recolección incorpora la API REST de GitHub.
- **C03 / T03.** Las capturas documentales alimentan una colección reconstruible.
- **C04 / T04.** Las capturas registran procedencia temporal y hashes.
- **C07 / T07.** Los XML-ID locales se normalizan por módulo.
- **C08 / T08.** Las plantillas QWeb incluyen relaciones de llamada.
- **C09 / T09.** La extracción representa relaciones de seguridad.
- **C10 / T10.** La resolución estática distingue campos, métodos y referencias pendientes.
- **C11 / T11.** Las revisiones incluyen condiciones y vigencia del salto.
- **C12 / T12.** Cambios y evidencias admiten enlaces múltiples.
- **C14 / T14.** Los hashes distinguen bytes originales y texto normalizado.
- **C16 / T16.** La ejecución efectiva de NetworkX tiene registros separados.
- **C17 / T17.** Las aristas conservan múltiples evidencias.
- **C19 / T19.** Los resultados distinguen candidatos y cambios verificados.
- **C20 / T20.** La presentación amplía la información explícita de cada hallazgo.
- **C22 / T22.** El evaluador explicita los parámetros de consulta.
- **C24 / T24.** C1 incorpora controles de correspondencia y aplicabilidad.
- **C25 / T25.** Los hallazgos pertinentes fuera del MIG se reportan separadamente.
- **C29 / T29.** La suite amplía las pruebas técnicas del sistema.
- **C30 / T30.** Los límites del piloto histórico están documentados.

## Detalle de todas las listas

### Detalle del listado total

#### T01. Unificar la documentación histórica y vigente de entrega.

Observación original: La carpeta revision corresponde a una etapa previa del sistema. Describe R2 como no implementado y al selector como independiente; el paquete posterior ya incorpora esas funciones. Es necesario unificar la documentación de entrega.

Cruce: ausente de las decisiones recientes; clasificado como C01. Véase el alcance de corrección al final.

#### T02. Implementar la recolección mediante la API REST de GitHub.

Observación original: La API REST de GitHub definida en la Tabla 4 no está implementada en R2. La recolección admite Git local y snapshots, pero no obtiene metadatos de PR, revisiones ni criterios de selección mediante esa API.

Cruce: ausente de las decisiones recientes; clasificado como C02. Véase el alcance de corrección al final.

#### T03. Integrar las descargas documentales con el constructor de R2.

Observación original: Los descargadores de documentación están separados del constructor R2. Generan archivos e inventarios, pero no los convierten directamente en fuentes del manifiesto que consume el paquete.

Cruce: ausente de las decisiones recientes; clasificado como C03. Véase el alcance de corrección al final.

#### T04. Registrar fechas de captura y procedencia de las fuentes.

Observación original: Las descargas usan direcciones mutables. Conservan SHA256 de la copia, pero sus registros no incluyen una fecha de captura ni una revisión upstream fijada. El hash identifica lo descargado; falta completar su procedencia temporal.

Cruce: ausente de las decisiones recientes; clasificado como C04. Véase el alcance de corrección al final.

#### T05. Completar el corpus de los tres saltos de versión.

Observación original: La colección de demostración cubre únicamente dos archivos del núcleo para 16→17. No acredita el alcance de fuentes y saltos 16→17, 17→18 y 18→19 previsto para R2.

Cruce: conserva relación con P03, P07. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T06. Validar el corte temporal y los seis criterios de selección.

Observación original: La exclusión de evaluación depende de metadatos declarados. El selector aplica correctamente split y la procedencia transitiva, pero no comprueba el corte temporal ni los seis criterios de selección de la tesis.

Cruce: conserva relación con P01, P02, P04. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T07. Normalizar los XML-ID locales por módulo.

Observación original: Los XML-ID locales no se normalizan con el nombre del módulo. Una declaración view_order_form puede quedar separada de una referencia sale_advance_payment.view_order_form; también pueden coincidir identificadores locales de módulos distintos.

Cruce: ausente de las decisiones recientes; clasificado como C07. Véase el alcance de corrección al final.

#### T08. Representar las llamadas entre plantillas QWeb.

Observación original: Las llamadas QWeb t-call se registran como elementos, sin una relación de llamada. Esto limita el recorrido entre plantillas.

Cruce: ausente de las decisiones recientes; clasificado como C08. Véase el alcance de corrección al final.

#### T09. Construir relaciones semánticas de seguridad desde CSV.

Observación original: La extracción CSV recoge identificadores, pero no construye sus relaciones semánticas. Falta representar de forma explícita relaciones de seguridad con modelos y grupos.

Cruce: ausente de las decisiones recientes; clasificado como C09. Véase el alcance de corrección al final.

#### T10. Distinguir campos y métodos al resolver referencias Python.

Observación original: Una referencia self.x puede generar una relación hacia un método aunque x sea un campo. El extractor no resuelve suficientemente esa distinción antes de crear self_reference.

Cruce: ausente de las decisiones recientes; clasificado como C10. Véase el alcance de corrección al final.

#### T11. Exigir evidencia estructurada de vigencia para cambios verificados.

Observación original: La categoría verified exige responsable y justificación, pero no evidencia estructurada de vigencia en destino. La revisión puede aceptarse sin registrar por separado cómo se comprobó la aplicabilidad a la versión destino.

Cruce: ausente de las decisiones recientes; clasificado como C11. Véase el alcance de corrección al final.

#### T12. Permitir relaciones múltiples entre evidencias y cambios semánticos.

Observación original: Se permite agrupar varios fragmentos en un cambio, pero no dividir explícitamente un mismo fragmento en varios cambios semánticos. El modelo no representa completamente esa relación entre evidencia y cambio.

Cruce: ausente de las decisiones recientes; clasificado como C12. Véase el alcance de corrección al final.

#### T13. Comprobar la generalización con casos reales de construcción.

Observación original: El reconocimiento de ciertos cambios está especializado en nombres del ejemplo. attrs, states, invisible, readonly y t-call reciben tratamiento explícito; falta comprobar su generalización con otros casos de construcción.

Cruce: conserva relación con P10. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T14. Distinguir hashes de bytes originales y texto normalizado.

Observación original: Los hashes de archivos se calculan sobre texto decodificado o normalizado. Deben distinguirse de los hashes de los bytes originales para evitar atribuirles una trazabilidad que no representan.

Cruce: ausente de las decisiones recientes; clasificado como C14. Véase el alcance de corrección al final.

#### T15. Ratificar las semillas de hallazgos directos e indirectos.

Observación original: Todos los elementos extraídos se utilizan como semillas de profundidad cero. Incluye referencias encontradas en el módulo. La convención debe fijarse metodológicamente porque cambia la interpretación de hallazgos directos e indirectos.

Cruce: conserva relación con P08, P09. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T16. Acreditar la ejecución efectiva de NetworkX.

Observación original: NetworkX está implementado, pero su ejecución no está garantizada. Si falta la biblioteca, se usa otro BFS. En las pruebas que ejecuté se utilizó stdlib_bfs_fallback; esa ejecución no acredita el uso efectivo de NetworkX.

Cruce: ausente de las decisiones recientes; clasificado como C16. Véase el alcance de corrección al final.

#### T17. Conservar todas las evidencias de cada arista.

Observación original: Cuando varias fuentes respaldan la misma arista, el grafo conserva una sola evidencia. La condición not graph.has_edge(...) impide añadir los respaldos posteriores a esa arista.

Cruce: ausente de las decisiones recientes; clasificado como C17. Véase el alcance de corrección al final.

#### T18. Calibrar la pertinencia del ordenamiento con casos de construcción.

Observación original: El ordenamiento es reproducible, pero su pertinencia no está calibrada con casos reales de construcción. Tener reglas deterministas no demuestra que los primeros resultados sean los más relevantes.

Cruce: conserva relación con P10. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T19. Distinguir candidatos y cambios verificados en resultados y contadores.

Observación original: La consulta mezcla candidatos y verificados por defecto. El resumen cuenta ambos; debe distinguirlos para que “cambios encontrados” no se interprete como cambios confirmados.

Cruce: ausente de las decisiones recientes; clasificado como C19. Véase el alcance de corrección al final.

#### T20. Mostrar elementos, versiones y evidencias completas en la salida textual.

Observación original: La vista textual omite información explícita por hallazgo. No presenta claramente el elemento afectado y las versiones origen/destino; en agrupaciones tampoco muestra todos los bloques de evidencia. El JSON contiene más información.

Cruce: ausente de las decisiones recientes; clasificado como C20. Véase el alcance de corrección al final.

#### T21. Justificar y congelar los campos documentales de BM25.

Observación original: BM25 indexa el registro JSON completo. Incluye contenido de evidencia junto con metadatos y datos de revisión, que también pueden influir en el ranking. Falta justificar y congelar los campos documentales indexados.

Cruce: conserva relación con P07, P10. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T22. Reproducir los parámetros de consulta desde el evaluador.

Observación original: El evaluador no permite reproducir todos los parámetros de consulta. No transmite un filtro de estado ni un límite configurable; utiliza los valores predeterminados de retrieve().

Cruce: ausente de las decisiones recientes; clasificado como C22. Véase el alcance de corrección al final.

#### T23. Resolver el uso metodológico de pandas, scikit-learn y statsmodels.

Observación original: No se utilizan pandas, scikit-learn ni statsmodels, aunque aparecen asignados a R2 en la Tabla 4. Las métricas se calculan con Python estándar. Hay que justificar la sustitución o ajustar la implementación según una función metodológica pertinente.

Cruce: conserva relación con P14. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T24. Validar estado, salto y elemento en las correspondencias de C1.

Observación original: C1 verifica que los cambios citados existan, pero no comprueba su estado, salto y elemento. Una correspondencia humana puede apuntar a un cambio candidato o inadecuado sin que el evaluador la rechace por esos motivos.

Cruce: ausente de las decisiones recientes; clasificado como C24. Véase el alcance de corrección al final.

#### T25. Reportar separadamente hallazgos pertinentes ausentes del MIG.

Observación original: Los hallazgos pertinentes ausentes del MIG no se reportan en una categoría diferenciada. El evaluador permite pertinencia sin vinculación a referencias, pero no genera el registro separado previsto en la tesis.

Cruce: ausente de las decisiones recientes; clasificado como C25. Véase el alcance de corrección al final.

#### T26. Completar la revisión lingüística y autenticidad de evidencias para V1.

Observación original: V1 comprueba solo parte de la conformidad exigida. Valida campos y algunas consistencias, pero no el idioma de los textos ni la autenticidad completa de las evidencias contra las fuentes.

Cruce: conserva relación con P05, P06. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T27. Ratificar el límite operacional de T1.

Observación original: T1 termina antes de validar, serializar e imprimir la salida. Actualmente representa tiempo interno de recuperación y preparación del resultado; no todo el tiempo hasta presentar la primera vista y el resumen en la CLI.

Cruce: conserva relación con P12. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T28. Controlar orden experimental, repeticiones y caché.

Observación original: El evaluador ejecuta primero las repeticiones del grafo y después las de BM25. No alterna el orden y admite caché declarada como uncontrolled; falta controlar estas condiciones para comparar tiempos.

Cruce: conserva relación con P13. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T29. Ampliar las pruebas sobre importación, identidades, relaciones y versiones.

Observación original: Las once pruebas no cubren varias brechas relevantes. Predominan snapshots sintéticos; faltan pruebas del importador con Git real, identidades entre módulos, relaciones QWeb y seguridad, y casos representativos de los tres saltos.

Cruce: ausente de las decisiones recientes; clasificado como C29. Véase el alcance de corrección al final.

#### T30. Delimitar el alcance probatorio del piloto histórico.

Observación original: El piloto histórico no demuestra una migración autónoma ni equivalencia funcional. Reutilizó código previamente adaptado y ejecutó las pruebas en una base diferente de la actualizada. Sus tiempos tampoco corresponden al T1 de consulta R2.

Cruce: ausente de las decisiones recientes; clasificado como C30. Véase el alcance de corrección al final.

#### T31. Completar la evaluación independiente y verificar los indicadores de tesis.

Observación original: La evaluación independiente de tesis sigue pendiente. No se ha acreditado la muestra de 30 MIG, los juicios definitivos ni el cumplimiento de C1 o la diferencia de precisión frente a BM25.

Cruce: conserva relación con P01, P02, P04, P05, P06, P07, P11. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

### Detalle de los últimos pendientes

#### P01. Elegir el modelo y snapshot de R4.

Identificar proveedor, modelo y snapshot exacto. El usuario confirmó que aún no están definidos.

#### P02. Confirmar el corte documentado y la fecha de separación experimental.

Documentar el corte de entrenamiento y la frontera entre construcción y evaluación. Agosto de 2025 sigue siendo ilustrativo.

#### P03. Definir las fuentes generales posteriores al corte admisibles en R2.

Precisar qué documentación general posterior al corte se permite, especialmente para 18→19; distinguirla de migraciones reservadas.

#### P04. Designar al responsable de revisar los seis criterios de selección.

Revisar mantenedor independiente, módulo único, versiones consecutivas, pruebas automatizadas, dependencias comunitarias públicas y ausencia de FIX de comportamiento.

#### P05. Designar al responsable de los juicios de pertinencia y cobertura.

Asignar revisores reales para pertinencia, correspondencias y cobertura; completar los juicios independientes antes de evaluar.

#### P06. Designar al responsable de revisar el inglés de las salidas.

Completar la revisión humana del inglés. La validación estructural automática no acredita conformidad lingüística.

#### P07. Fijar los repositorios y revisiones del corpus de construcción.

Delimitar repositorios, revisiones o capturas, alcance, exclusiones y codificación. Nueve unidades parciales no constituyen el corpus completo.

#### P08. Ratificar la definición de consultas y semillas de profundidad cero.

Definir qué declaraciones y referencias constituyen semillas y cómo se interpreta la distancia de cada hallazgo.

#### P09. Fijar la profundidad máxima del recorrido.

Determinar el límite de BFS y registrarlo en el protocolo congelado.

#### P10. Calibrar y congelar el ordenamiento utilizando exclusivamente casos de construcción.

Ajustar reglas, prioridades y desempates con construcción. Congelar también los campos documentales de BM25 antes de evaluar.

#### P11. Ratificar P1 como promedio de consultas con precisión definida.

Confirmar agregación macro y tratamiento de consultas sin precisión definida; conservar resultados y denominadores individuales.

#### P12. Elegir el límite operacional de T1.

Elegir entre hasta validación y serialización o hasta completar stdout de la CLI. Conservar separadas las otras medidas.

#### P13. Fijar las repeticiones y condiciones de caché para medir tiempos.

Definir repeticiones, calentamiento, caché y entorno; mantener orden contrabalanceado y medidas individuales.

#### P14. Resolver la discrepancia metodológica sobre statsmodels en R2.

pandas y scikit-learn ya se ejecutaron con funciones concretas. statsmodels está instalado, pero no se usó sin inferencia justificada.

### Detalle de los puntos corregidos por cruce

#### C01. La entrega distingue la documentación vigente del material histórico.

Procedencia: T01. No se afirma haber reescrito toda la carpeta externa revision.

#### C02. La recolección incorpora la API REST de GitHub.

Procedencia: T02. La API se ejecutó. La ampliación reciente recibió HTTP 403; la selección completa sigue pendiente.

#### C03. Las capturas documentales alimentan una colección reconstruible.

Procedencia: T03. La colección documental actual tiene inventario y reconstrucción offline; los descargadores antiguos son antecedentes.

#### C04. Las capturas registran procedencia temporal y hashes.

Procedencia: T04. Una captura mutable no se presenta como commit upstream. No se inventaron revisiones.

#### C07. Los XML-ID locales se normalizan por módulo.

Procedencia: T07. El informe registra normalización e identidades separadas entre módulos.

#### C08. Las plantillas QWeb incluyen relaciones de llamada.

Procedencia: T08. El informe registra llamadas y herencia QWeb.

#### C09. La extracción representa relaciones de seguridad.

Procedencia: T09. El informe registra referencias de grupos, datos y seguridad.

#### C10. La resolución estática distingue campos, métodos y referencias pendientes.

Procedencia: T10. Las referencias no resueltas conservan ese estado, sin inventar un método.

#### C11. Las revisiones incluyen condiciones y vigencia del salto.

Procedencia: T11. La estructura está implementada; el corpus general todavía carece de revisión independiente.

#### C12. Cambios y evidencias admiten enlaces múltiples.

Procedencia: T12. El modelo incorpora enlaces M:N para agrupación y división semántica.

#### C14. Los hashes distinguen bytes originales y texto normalizado.

Procedencia: T14. Cada representación conserva su identidad; no se atribuye al texto el hash de bytes.

#### C16. La ejecución efectiva de NetworkX tiene registros separados.

Procedencia: T16. Hay registros con NetworkX real, compatibilidad y segundo entorno limpio.

#### C17. Las aristas conservan múltiples evidencias.

Procedencia: T17. La prueba de recorrido indirecto conserva varios respaldos sobre una arista.

#### C19. Los resultados distinguen candidatos y cambios verificados.

Procedencia: T19. Los 432 fragmentos candidatos no se presentan como 432 incompatibilidades verificadas.

#### C20. La presentación amplía la información explícita de cada hallazgo.

Procedencia: T20. La aceptación lingüística sigue pendiente; este cruce no certifica por sí solo cada requisito visual.

#### C22. El evaluador explicita los parámetros de consulta.

Procedencia: T22. Estado, límite y profundidad son parámetros compartidos y reproducibles.

#### C24. C1 incorpora controles de correspondencia y aplicabilidad.

Procedencia: T24. Se comprueban salto, elemento, vigencia y condiciones además de la existencia del cambio.

#### C25. Los hallazgos pertinentes fuera del MIG se reportan separadamente.

Procedencia: T25. Su ausencia del MIG no implica automáticamente un falso positivo.

#### C29. La suite amplía las pruebas técnicas del sistema.

Procedencia: T29. Hay 33 casos bajo tres condiciones. No son 99 requisitos ni demuestran representatividad académica completa.

#### C30. Los límites del piloto histórico están documentados.

Procedencia: T30. Se corrigió su interpretación. No se ejecutó otra migración autónoma ni se acreditó equivalencia funcional.

### Fuentes y límites

- Fuente original: adjunto d97080b3-b253-49b5-8617-f6af55f7fff6/Texto pegado.txt, con 31 observaciones.
- Fuente reciente: respuesta anterior con 14 decisiones, conservadas en significado.
- Estado consultado: [Informe de cumplimiento](audit/INFORME_CUMPLIMIENTO.md).
- Cruce: 11 observaciones relacionadas con decisiones recientes y 20 ausentes, clasificadas como corregidas.
- El corpus sigue parcial y sin codificación independiente completa. La evaluación final y los treinta MIG elegibles continúan pendientes.
- El piloto histórico conserva sus limitaciones. Documentarlas no equivale a haberlas eliminado experimentalmente.
- Este registro no modifica la tesis ni acredita resultados académicos nuevos.
