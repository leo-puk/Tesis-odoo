# Fichas de selección independiente

Continuación del 14 de noviembre de 2026. Se prepararon expedientes para las primeras candidatas del orden aleatorio ya registrado en cada estrato:

- 17.0: OCA/l10n-brazil#5342.
- 18.0: OCA/connector-shopify#28.
- 19.0: OCA/account-invoicing#2468.

Son candidatas, no migraciones elegibles confirmadas. El primer acceso REST devolvió HTTP 403; las siguientes solicitudes no se realizaron tras ese fallo. summary.json y los archivos de cada carpeta conservan el estado. No se descargaron parches ni soluciones, no se añadió contenido al índice y ningún criterio se aprobó automáticamente.

Para reanudar cuando el acceso esté disponible, desde la raíz del paquete:

```powershell
.\.venv\Scripts\python.exe -m audit.prepare_review_packets audit/selection-input.json --output audit/review-packets --per-stratum 1
```

La utilidad reutiliza capturas ya obtenidas, conserva el inventario original y produce selection-input-enriched.json separado. Distingue observaciones automáticas (rutas de manifiestos/pruebas, aprobación del head por alguien distinto del autor) de los seis criterios que requieren evidencia y responsable. No equipara aprobación con identidad de mantenedor ni presencia de una prueba con prueba ejecutable.

El control de HTTP ahora archiva cabeceras de límite y reinicio permitidas y conserva cada fallo con fecha, sin tokens. Puede utilizarse GH_TOKEN/GITHUB_TOKEN configurado localmente; no debe pegarse un token en el chat. Las preguntas pendientes sobre modelo/corte y responsables siguen sin responderse y no se sustituyen por supuestos.

Tres pruebas nuevas verifican que no se aprueben criterios, que se respete una aprobación retirada y que se conserven las decisiones previas de revisión. Son pruebas del programa, no resultados empíricos de la tesis.
