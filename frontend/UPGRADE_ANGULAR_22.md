# Actualización Angular 22 — RNC / frontend

Fecha: 2026-10-31. Origen: 20.3.30 → core 22.2.4; CLI/build/Material/CDK 22.2.5 donde aplica; TypeScript 6.0.3. Node de desarrollo/imagen: 24.19.0. Soporte Node: ^22.22.3 || ^24.15.0 || >=26.

Se ejecutaron migraciones oficiales por major, conservando contratos, estilos y semántica anterior con Eager/withXhr/proveedores de Zone cuando correspondía. Se retiraron baseUrl/downlevelIteration incompatibles con TS6 y se rebajaron los alias a rutas relativas. No se usó --force ni --legacy-peer-deps.

Instalación limpia: True. Build: True. Arranque de desarrollo en navegador: True. Las pruebas con fixtures no llaman APIs reales ni acreditan un despliegue.

Auditoría npm completa: 0 críticas, 0 altas, 0 moderadas, 0 bajas. Sin dev: 0 críticas, 0 altas, 0 moderadas, 0 bajas. Conteos de paquetes, no CVE únicos. 

Se conserva el formulario público y su perfil/prefijo; no se inventa otro componente RCN. Sin specs funcionales existentes.

Los gaps de arquitectura y autenticación priorizados se mantienen abiertos salvo la compatibilidad y las correcciones específicas descritas aquí. Esta actualización no publica imágenes, no despliega ni certifica seguridad completa.

Reproducción: npm ci (en Birdport, raíz con --workspace=apps/admin --workspace=apps/store --include-workspace-root); npm run build; npm start para desarrollo. Para suites existentes: npm test -- --watch=false; Karma requiere Chromium y --browsers=ChromeHeadless. Columba: npm run verify y npm run e2e desde la raíz. Fuentes oficiales: https://angular.dev/reference/versions y https://angular.dev/update-guide.

Base Git: 6bea84d610a80bce8a5296bdeef801915e92bf22. Los cambios locales previos se conservan. Evidencia de ejecución: /home/marc/.cache/tordo/angular22-pending-20261031/logs/RNC; manifiestos y hashes del diff permiten distinguir la propuesta del trabajo previo. No se crea un SHA ficticio de implementación.
