# RNC: copiloto de carrera con agente local

## Dirección del producto

RNC acompaña el ciclo perfil → vacante → preparación → postulación → seguimiento.
LinkedIn es el primer adaptador de navegador. El perfil del candidato y su historial
de candidaturas pertenecen a RNC; el adaptador traduce acciones concretas al DOM.

Se reutiliza el patrón de `../learnex-exporter/src/capture/browser.py`: Firefox abierto,
inicio de sesión manual, Selenium con `--connect-existing` y Marionette local. El código
de RNC es independiente; no importa módulos ni datos de Learnex.

```mermaid
flowchart LR
    UI[Interfaz Angular] --> API[FastAPI y PostgreSQL]
    CLI[rcn-agent en el equipo del usuario] --> FF[Firefox con sesión abierta]
    FF --> LI[LinkedIn]
    CLI --> LOCAL[Capturas y candidaturas en SQLite local]
```

La API central y el agente local todavía no están conectados. El agente funciona hoy
desde la terminal y puede ser invocado por herramientas de desarrollo. Un servidor
MCP y la integración con Angular son entregas futuras.

## Lo implementado

| Comando | Resultado |
| --- | --- |
| `doctor` | Diagnóstico de Firefox, geckodriver y puerto Marionette. |
| `capture-profile` | Captura nombre, titular y secciones visibles del perfil abierto. |
| `inspect-profile` | Diagnóstico limitado a encabezados y estructura del perfil, sin guardarlo. |
| `capture-job` | Captura título, empresa, ubicación, descripción y presencia de Easy Apply. |
| `inspect-application` | Describe campos, etiquetas, opciones y acciones del paso visible. |
| `inspect-application --open` | Hace clic en el botón Easy Apply y luego inspecciona el diálogo. |
| `track` | Registra explícitamente el estado de una candidatura ya capturada. |
| `applications` | Lista candidaturas locales, con filtro por estado. |

Las capturas incluyen URL canónica y fecha. Se conserva cada captura; las candidaturas
se deduplican por URL de vacante y mantienen un historial de cambios de estado. El
estado `applied` se registra únicamente con una instrucción explícita `track` del usuario;
capturar una vacante o inspeccionar un formulario nunca lo marca como enviado.

El perfil capturado es el perfil que indiques o tengas abierto. Esta entrega no verifica
que sea tu propio perfil, no genera contenido con IA, no edita LinkedIn y no rellena ni
envía formularios. La inspección de Easy Apply cubre únicamente el paso visible, no los
pasos siguientes ni formularios externos.

## Preparación en Ubuntu/Linux

```bash
cd /home/marc/Documentos/Proyects/RNC/backend
uv venv .venv
uv pip install --python .venv/bin/python -e '.[browser,dev]'
```

Se usa Selenium como dependencia opcional: la imagen Docker del backend no necesita
Firefox ni esta dependencia. Se puede ejecutar el módulo sin instalar el comando:

```bash
.venv/bin/python -m app.local_agent.cli --help
```

1. Cierra Firefox completamente cuando puedas hacerlo sin interrumpir tu trabajo.
2. Ábrelo con `firefox --marionette`.
3. En ese Firefox inicia sesión y abre tu perfil o una vacante de LinkedIn.
4. Ejecuta `.venv/bin/rcn-agent doctor` y revisa `ready`.

Ejecutar `firefox --marionette` mientras Firefox ya está abierto puede reutilizar la
instancia sin habilitar Marionette. El agente no cierra ni reinicia tu Firefox.
Con Firefox Snap usa su geckodriver (`/snap/bin/geckodriver`); el agente lo encuentra
en PATH o en esa ruta. Marionette debe escuchar en `127.0.0.1:2828`.

La exclusión entre procesos usa `flock`; esta primera versión está orientada a Linux.
Ejecuta un solo controlador de Marionette a la vez: termina el comando de Learnex
antes de conectar RNC al mismo Firefox.

## Flujo de uso

Desde `backend/`:

```bash
# Diagnóstico sin controlar pestañas ni capturar datos de la cuenta.
.venv/bin/rcn-agent doctor

# Leer el perfil abierto; --url permite elegir uno explícitamente.
.venv/bin/rcn-agent capture-profile
.venv/bin/rcn-agent capture-profile --url https://www.linkedin.com/in/tu-perfil/

# Si no se reconoce el perfil, obtener pistas de su estructura.
.venv/bin/rcn-agent inspect-profile --url https://www.linkedin.com/in/tu-perfil/

# Capturar una vacante para trabajarla localmente.
.venv/bin/rcn-agent capture-job --url https://www.linkedin.com/jobs/view/123456789/

# Guardarla en el seguimiento.
.venv/bin/rcn-agent track --job-url https://www.linkedin.com/jobs/view/123456789/ \
  --status saved --notes 'Revisar idioma y disponibilidad para LATAM'

# Abrir Easy Apply e inspeccionar las preguntas del paso actual.
.venv/bin/rcn-agent inspect-application \
  --url https://www.linkedin.com/jobs/view/123456789/ --open

# Después de completar y enviar tú la candidatura en Firefox:
.venv/bin/rcn-agent track --job-url https://www.linkedin.com/jobs/view/123456789/ \
  --status applied --notes 'Enviado desde Firefox'

.venv/bin/rcn-agent applications
.venv/bin/rcn-agent applications --status applied
```

Estados: `saved`, `preparing`, `applied`, `interview`, `offer`, `rejected`, `withdrawn`.
El seguimiento permite registrar cambios manuales; no impone una secuencia de estados.
Omitir `--notes` conserva las notas anteriores; `--notes ''` las limpia.

Los comandos devuelven JSON por stdout y errores por stderr con código de salida 1.
Si hay un error de conexión, `doctor` permite distinguir falta de geckodriver y puerto
cerrado. `doctor` devuelve código 0 cuando puede completar el diagnóstico, aunque
`ready` sea `false`.

El agente usa una pestaña existente que coincida con el recurso. Cuando indicas
`--url` y no está abierta, navega una pestaña de LinkedIn existente a esa URL; no
navega otras páginas. Puedes abrir una pestaña dedicada para RNC. Al terminar deja
la pestaña en su estado actual, incluido cualquier diálogo que haya abierto.
Sin `--url`, se prefiere la pestaña actual si es un recurso compatible. La captura
del perfil espera hasta 15 segundos a que aparezca el nombre, incluso después de
que el navegador indique que el documento terminó de cargar. Acepta encabezados
visibles `h1`, encabezados accesibles y variantes de la tarjeta superior con `h2`.

Si falla, `inspect-profile` devuelve los selectores encontrados y hasta 20 encabezados
con su etiqueta, rol, clase y texto acotado, además de identificadores de secciones.
Puede incluir tu nombre y títulos de secciones; revisa esos datos antes de compartir
la salida. No incluye el HTML completo, mensajes ni valores de formularios.

## Datos locales y límites operativos

Por defecto el archivo es `~/.local/share/rcn/career.sqlite3`, o `$XDG_DATA_HOME/rcn/`
si esa variable existe. Contiene datos profesionales y notas privadas; directorio
nuevo con permisos 700 y archivo de base con permisos 600.

Puedes elegir otra ruta o puerto pasando las opciones antes del comando:

```bash
.venv/bin/rcn-agent --data-dir ../data/local-agent applications
.venv/bin/rcn-agent --marionette-port 2828 doctor
```

Se exportan campos seleccionados del DOM visible, no cookies, contraseñas, valores
de formularios ni el HTML completo. En perfiles, las secciones contienen el texto
renderizado y pueden incluir encabezados y etiquetas de LinkedIn. Los campos que
no estén renderizados quedan vacíos; el agente no carga páginas de detalle ni hace
scroll automáticamente.

Si el DOM cambia, una vacante no carga, hay varios botones Easy Apply o aparece un
inicio de sesión/verificación, el comando se detiene. El usuario resuelve la situación
en Firefox y repite. LinkedIn puede restringir la automatización del navegador; usar
tu sesión no elimina esa limitación. Esta entrega no implementa técnicas de evasión.

La conexión reutiliza la sesión mediante los flags documentados por Mozilla:
[geckodriver --connect-existing](https://firefox-source-docs.mozilla.org/testing/geckodriver/Flags.html).
Con ese modo, eliminar la sesión de WebDriver no envía el cierre forzado usado para
un navegador lanzado por geckodriver; se verifica con una reconexión en las pruebas.

## Próximas entregas

1. **Integración con RNC:** asociar capturas al candidato y sincronizar vacantes y
   candidaturas con FastAPI. Definir identidad/autenticación antes de transportar
   datos privados al servicio alojado.
2. **Perfil profesional:** comparar el perfil capturado con la información verificada
   del CV; preparar propuestas de titular, Acerca de y experiencia con vista previa.
3. **Preparación de candidaturas:** correspondencia de preguntas y respuestas
   verificadas, carga del CV, validación de campos y revisión previa al envío.
4. **Interfaz Angular:** panel de conexión, comparación de perfil, bandeja de vacantes
   y seguimiento de candidaturas. El acceso a Firefox seguirá ocurriendo en el equipo
   del usuario, no en el contenedor remoto.
5. **MCP/skill propia:** exponer acciones concretas del agente para asistentes y un
   flujo de trabajo reutilizable. No hace falta adoptar un MCP de terceros para
   implementar el adaptador inicial.

La integración futura puede usar un agente que consulte tareas autenticadas por
HTTPS. Así el servicio central no necesita alcanzar el puerto Marionette del equipo
del usuario ni recibir su perfil de navegador.
