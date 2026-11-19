# Configuración · RNC

Consolidación documental del 2026-11-15. Los comandos se obtuvieron de los manifiestos de esta copia; no se ejecutaron builds ni operaciones de negocio para redactar esta guía. El detalle histórico está en la wiki.

[README](../README.md) · [Mapa documental](https://dev.tordo.io/tecolyt/ui/wiki?path=Gobierno%2FDocumentacion%2FRepositorios%2FRNC%2FIndice.md)

## Opciones por componente

Las siguientes claves son referencias observadas en código, no una afirmación de obligatoriedad o de valor predeterminado. Los valores reales no se copian.

| Clave | Consumidor observado | Valor / requisito |
|---|---|---|

No se identificaron claves por los patrones inspeccionados; esto no demuestra ausencia de configuración. Consultar manifiestos e instrucciones específicas.

### Fuente: `docs/TORDO_PLATFORM_INTEGRATION.md`

#### Variables de entorno

Agregar al environment activo de `/opt/tordo-platform/environments/*.env`:

```bash
# --- Remote Career Navigator (activar agregando 'rcn' a COMPOSE_PROFILES) ---
RCN_TAG=main
RCN_PORT=8050
RCN_UI_PREFIX=/rcn/ui
```

Tambien agregar `rcn` a `COMPOSE_PROFILES`.

## Dependencias externas

Consultar las instrucciones específicas consolidadas abajo y los anexos registrados en README. Si no hay definición suficiente en las fuentes, el requisito queda pendiente de documentar; no se infiere un comportamiento nuevo.

## Acceso, identidad y empresa

Consultar las instrucciones específicas consolidadas abajo y los anexos registrados en README. Si no hay definición suficiente en las fuentes, el requisito queda pendiente de documentar; no se infiere un comportamiento nuevo.

## Persistencia y preparación local

Consultar las instrucciones específicas consolidadas abajo y los anexos registrados en README. Si no hay definición suficiente en las fuentes, el requisito queda pendiente de documentar; no se infiere un comportamiento nuevo.

## Rutas, puertos y prefijos

Consultar las instrucciones específicas consolidadas abajo y los anexos registrados en README. Si no hay definición suficiente en las fuentes, el requisito queda pendiente de documentar; no se infiere un comportamiento nuevo.

## Ambientes y secretos

No versionar `.env`, tokens, certificados ni valores de producción. Los nombres observados no acreditan acceso ni autorización. Usar el mecanismo de secretos y los perfiles ya definidos; los ejemplos preservados son documentales.
