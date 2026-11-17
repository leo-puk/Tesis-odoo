# Manual de codificación R2 0.2

## Actualización de integración 0.3

Para esquema 3, una fuente es una unidad aceptada por adquisición. Sus archivos almacenados se conservan en `artifacts`; documentos y manifiestos tienen registros contextuales en `documents`. Solo diffs directos o el campo diff de PR generan candidatos. Los hashes calculados por ingestión identifican archivos almacenados, no originales HTTP. Las referencias de comparación se declaran mediante bindings y no equivalen automáticamente a SHA inmutables. La extracción desde hunks tiene alcance parcial. Las reglas de revisión, agrupación y aplicabilidad de este manual se mantienen; las descripciones posteriores de capturas antes/después corresponden al importador histórico. Véase [Integración](INTEGRACION_ADQUISITION.md).

Este manual operacionaliza el análisis de contenido de 1.3.3.1. Las decisiones de ingeniería no son citas ni modificaciones de la tesis. No se evalúa mediante un panel de expertos: se requiere revisión documental explícita de evidencias. El manual y sus reglas deben congelarse antes de la evaluación independiente.

## Unidades y tablas

- **Fuente**: repositorio/revisión o captura de una página/archivo con URL, fecha, bytes originales y texto normalizado. Tabla sources.
- **Comparación**: par de estados y salto; identifica el contexto de versiones. Tabla comparisons.
- **Fragmento de evidencia**: bloque del diff, rangos antes/después y texto. Tabla evidence. No es por sí mismo una incompatibilidad.
- **Cambio semántico**: interpretación respaldada por uno o varios fragmentos. Tabla changes. change_evidence representa la relación muchos-a-muchos; un mismo fragmento puede respaldar dos cambios con semantic_id diferentes.
- **Elemento**: identidad semántica versionada, por ejemplo modelo, campo, método o XML-ID cualificado.
- **Ocurrencia**: aparición de ese elemento en una ubicación. Conserva módulo técnico, archivo, rango y role: declaration, reference o unresolved.
- **Hallazgo**: cambio recuperado para una consulta específica, con condiciones comprobables, camino y profundidad mínima. Un hallazgo puede ser directo o indirecto.

El almacén conserva separadamente fuentes/comparaciones/evidencias. Los cambios incluyen también copias de bloques como vista de lectura para facilitar inspección; los IDs y la tabla de enlaces son la relación explícita.

## Categorías

api_refactoring: firma, renombrado o movimiento de API; behavior: modificación de comportamiento; syntax: sintaxis admitida; data: modelos/campos/datos; security: controles de acceso; manifest: empaquetado/dependencias; format: formato/comentarios sin relevancia migratoria demostrada; administrative: mantenimiento ajeno a migración; documentation: modificación documental; unclassified: candidato no interpretado.

La capa source_layer describe el archivo que contiene la evidencia. layer describe la capa afectada, inicialmente inferida del archivo y revisable explícitamente: python, xml (incluye QWeb), data (incluye seguridad) o manifest. Una advertencia escrita en Python puede explicar una adaptación XML. Documentación y administración se separan del denominador de cambios evaluables; no se convierten automáticamente en incompatibilidades.

## Estados

- candidate: diferencia observada sin interpretación completamente respaldada.
- verified: interpretación revisada con responsable, fecha con zona horaria, justificación, elementos afectados contenidos en la evidencia y comprobación documentada de vigencia en el salto.
- rejected: no procede para el cambio propuesto o candidato sustituido por una interpretación semántica explícita.
- unresolved: evidencia ambigua o insuficiente; no se fuerza una decisión.

Verified no es una demostración automática de incompatibilidad o equivalencia funcional. La verificación que registra R2 es documental y su autenticidad/aplicabilidad sigue siendo auditable. Las condiciones son required_elements o general_applicability con justificación. destination_validity requiere from_version, to_version, status=checked, explanation y evidencia concreta admitida. El programa valida consistencia; no inventa la comprobación humana.

required_elements expresa conjunción de presencias. Una revisión que necesite condiciones más complejas que el modelo actual no debe declararlas comprobadas: queda unresolved o requiere ampliar y congelar formalmente el lenguaje de condiciones. La agrupación conserva la conjunción de condiciones de sus miembros.

## Procedimiento de revisión

1. Inspeccionar fuente, revisión, comparación y fragmentos originales. Diferenciar texto añadido/eliminado de contexto.
2. Identificar la diferencia semántica y descartar de los indicadores las modificaciones administrativas o ajenas al salto.
3. Asignar categoría y capa afectada. Conservar capa de la evidencia.
4. Comprobar existencia/vigencia de la información en destino, citando evidencias del mismo salto.
5. Declarar condiciones explícitas o explicar por qué el cambio es general.
6. Registrar reviewed_at, reviewer y rationale. Si hay ambigüedad usar unresolved y explicar qué falta.
7. Para varios fragmentos de una adaptación: evidence_ids en un semantic_id común, o group_id para revisiones compatibles. Para varios cambios en un fragmento: semantic_id distintos con el mismo evidence_id.
8. Conservar todos los eventos en review_history. No sobrescribir el Word ni atribuir estos eventos a un evaluador independiente si proceden del desarrollo.

Ejemplo de forma (los marcadores no son un juicio real):

```json
{
  "semantic_id": "identidad-del-cambio",
  "evidence_ids": ["ev_ID_EXISTENTE"],
  "status": "verified",
  "reviewer": "RESPONSABLE_REAL",
  "reviewed_at": "FECHA_ISO_CON_ZONA",
  "rationale": "Justificación de la interpretación",
  "title": "English description supported by the source",
  "category": "syntax",
  "layer": "xml",
  "affected_elements": ["xml-attribute:atributo_identificado"],
  "required_elements": ["xml-attribute:atributo_identificado"],
  "destination_validity": {
    "status": "checked", "from_version": "16.0", "to_version": "17.0",
    "explanation": "Comprobación concreta de destino", "evidence_ids": ["ev_ID_EXISTENTE"]
  }
}
```

## Identidades y relaciones

Los XML-ID locales se cualifican con el módulo técnico, no con el nombre comercial. Los ya cualificados se conservan. Si la carpeta se renombró, query --module-name fija el nombre real. No se resuelve un self.x como método por su forma: se consultan declaraciones conocidas; si no hay evidencia permanece unresolved. Las declaraciones de campo/método se distinguen de referencias.

Las semillas de profundidad cero son identidades declaradas o explícitamente referidas por el módulo original y resueltas estáticamente. Se excluyen unresolved, símbolos genéricos y localizadores XPath de ese conjunto. Las relaciones de origen pueden resolver referencias mediante declaraciones de la colección en esa misma versión. No se suman enlaces administrativos a la evidencia a la distancia al elemento afectado.

Direcciones: clase→modelo (extends), método/campo→modelo (belongs_to), campo→modelo relacionado (comodel), campo→calculador (computed_by), método→campo (depends_on), uso→elemento self resuelto (self_reference), vista→campo (displays), vista/plantilla→identificador referido (inherits_or_references), plantilla→plantilla (qweb_call), registro→referencia eval (data_reference), acceso→identificador de modelo/grupo (security_reference), vista→grupo requerido/excluido (requires_group/excludes_group), declaración→propiedad usada (uses_keyword/uses_attribute), validador→atributo XML explícito de su expresión XPath (validates_xml_attribute).

Cada arista conserva todas sus ocurrencias, fuente, versión y ubicación; no solo la primera. El cruce de modelos/campos/métodos es cualificado. Los símbolos genéricos de documentación no se presentan como resolución inequívoca. Se extrae una expresión XPath; no se acredita la validez de la arquitectura combinada de Odoo.

El enlace especial anterior basado en una lista de nombres attrs/states se sustituyó por extracción de atributos de expresiones XPath presentes en el código. Una prueba con legacy_flag verifica que el mecanismo no depende de los nombres del piloto. Eso comprueba generalización técnica, no precisión académica.
