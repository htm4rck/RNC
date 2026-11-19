# Pruebas · RNC

Consolidación documental del 2026-11-15. Los comandos se obtuvieron de los manifiestos de esta copia; no se ejecutaron builds ni operaciones de negocio para redactar esta guía. El detalle histórico está en la wiki.

[README](../README.md) · [Mapa documental](https://dev.tordo.io/tecolyt/ui/wiki?path=Gobierno%2FDocumentacion%2FRepositorios%2FRNC%2FIndice.md)

## Preparación del entorno de prueba

Preparar las dependencias indicadas por cada script. Las pruebas que incluyen DEV, proveedores reales o mutaciones necesitan un destino explícito; esta normalización no las ejecuta ni concede esa autorización.

## Comandos por componente

| Directorio | Comando disponible | Condición |
|---|---|---|
| `frontend` | `npm run build` | Script declarado; revisar destino y requisitos antes de ejecutar |
| `frontend` | `npm run test` | Script declarado; revisar destino y requisitos antes de ejecutar |

### Fuente: `docs/VALIDACION_HOMOLOGACION_UI.md`

### Validación de homologación para desarrollo

- Repositorio: `github.com/htm4rck/RNC.git`.
- Rama de destino: `develop`.
- Base remota anterior: `d6d6f37973a68017c539c9e5270a9c13b648b437`.
- Base de la consolidación: `d6d6f37973a68017c539c9e5270a9c13b648b437`.
- Fecha de validación previa: 2026-10-30.
- Resultado: PASS: previously completed local build and compiled HTML inspection.

Se conserva la configuración propia del proyecto y se homologa la carga de CSS
mediante `optimization.styles.inlineCritical: false` cuando corresponde.
La aplicación del ajuste común se comprueba con `@tordo-io/web-security` 0.1.0.
La validación anterior se reutiliza por instrucción del usuario; no se vuelven a
lanzar suites, builds ni despliegues completos en el servidor. Este commit de
consolidación usa `[skip ci]`. Esto registra código validado en la rama de
desarrollo; no equivale a una imagen nueva construida ni a un despliegue.

Solo se incluyen los cambios de homologación y documentación enumerados en el
diff. Se preserva por separado el trabajo de otras tareas de los clones originales.
Reports y Corvus están excluidos de este proceso.

El resultado de compilación local documentado corresponde al workspace probado.
La configuración se aplica sobre la base remota conservando su historial; cuando
esa base contiene otros cambios previos, no se atribuye a este registro una nueva
validación de esos cambios. No se modifica la lógica de negocio por el ajuste CSS.

## Casos relevantes y negativos

Consultar las instrucciones específicas consolidadas abajo y los anexos registrados en README. Si no hay definición suficiente en las fuentes, el requisito queda pendiente de documentar; no se infiere un comportamiento nuevo.

## Resultado esperado y limpieza

Consultar las instrucciones específicas consolidadas abajo y los anexos registrados en README. Si no hay definición suficiente en las fuentes, el requisito queda pendiente de documentar; no se infiere un comportamiento nuevo.

## Cobertura y límites conocidos

Esta entrega comprueba documentación, enlaces y consumidores; no certifica funcionalidad ni aceptación productiva. Se conservan las limitaciones originales y los resultados fechados en la wiki.

## Aceptación y evidencia

[Fuentes y evidencias documentales](https://dev.tordo.io/tecolyt/ui/wiki?path=Gobierno%2FDocumentacion%2FRepositorios%2FRNC%2FIndice.md). Build, prueba local, despliegue y aceptación de negocio se registran por separado.
