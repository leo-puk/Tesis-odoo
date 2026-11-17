# Prueba funcional con módulo OCA real

Resultado: aprobada.

Entrada: sale_advance_payment 16.0.1.0.0; salto consultado 16→17.

HTTP y revisión se simularon. El código OCA y los dos snapshots del núcleo son copias reales locales sin modificar.

La colección produjo 158 hunks candidatos; no son incompatibilidades confirmadas.

La consulta inicial por grafo recuperó 19 candidatos y mostró los primeros diez; su pertinencia no se evaluó independientemente.

Las dos anotaciones de revisión simuladas permiten comprobar que grafo y BM25 recuperan exactamente los cambios esperados:

- Odoo 17 warns that the states field property is no longer supported
- Odoo 17 rejects attrs/states attributes in view validation

El control sin esas condiciones y el salto 17→18 devolvieron cero hallazgos revisados. La consulta siguió funcionando después de borrar los temporales.

El módulo OCA se usó solo como entrada; la unidad de solución OCA de control se excluyó antes de la red. No se ejecutó Odoo ni se migró o modificó el módulo. No se prueba equivalencia funcional ni cobertura de todas las incompatibilidades.

La revisión es una entrada mock del test, no una capacidad de verificación automática ni un juicio independiente. Este módulo ya estaba reservado como caso de desarrollo y continúa excluido de evaluación final.

report.json conserva comprobaciones, hashes y procedencia; query-graph.json y query-bm25.json contienen los resultados. mock-response.diff conserva la respuesta simulada.
