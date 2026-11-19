# Desarrollo · RNC

Consolidación documental del 2026-11-15. Los comandos se obtuvieron de los manifiestos de esta copia; no se ejecutaron builds ni operaciones de negocio para redactar esta guía. El detalle histórico está en la wiki.

[README](../README.md) · [Mapa documental](https://dev.tordo.io/tecolyt/ui/wiki?path=Gobierno%2FDocumentacion%2FRepositorios%2FRNC%2FIndice.md)

## Requisitos y versiones

| Manifiesto | Stack | Requisito observado |
|---|---|---|
| `backend/pyproject.toml` | Python | Versión declarada en el manifiesto/wrapper; no se fija otra versión aquí |
| `frontend/package.json` | Node | node: `^22.22.3 \|\| ^24.15.0 \|\| >=26.0.0`; @angular/core: `22.2.4`; typescript: `~6.0.3` |

## Instalación

| Directorio | Instalación | Condición |
|---|---|---|
| `frontend` | `npm ci` | Consultar requisitos del manifiesto |

## Ejecución local

| Directorio | Comando disponible | Condición |
|---|---|---|
| `frontend` | `npm run start` | Script declarado; preparar configuración y dependencias |

## Estructura y puntos de extensión

Directorios existentes: `backend`, `docs`, `frontend`. La responsabilidad detallada se conserva en los fragmentos y anexos siguientes.

## Convenciones específicas y flujo de cambios

Aplicar las instrucciones AGENTS.md más cercanas cuando existan y las referencias centrales de [Arquitectura/Estandares](https://dev.tordo.io/tecolyt/ui/wiki?path=Arquitectura%2FEstandares%2FIndice.md). Las reglas específicas y contratos de la revisión conservan prioridad sobre una plantilla genérica.

## Diagnóstico local

Las instrucciones o referencias específicas se conservan a continuación; sus fuentes y limitaciones siguen identificadas.

### Fuente: `docs/LOCAL_CAREER_AGENT.md`

Consultar **Preparación en Ubuntu/Linux** en la [fuente local conservada](LOCAL_CAREER_AGENT.md). Se mantiene por sus consumidores; contrastar versiones y comandos con los manifiestos de arriba.

### Fuente: `docs/LOCAL_CAREER_AGENT.md`

Consultar **Preparar una solicitud con contacto y CV precargado** en la [fuente local conservada](LOCAL_CAREER_AGENT.md). Se mantiene por sus consumidores; contrastar versiones y comandos con los manifiestos de arriba.
