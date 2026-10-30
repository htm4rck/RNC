# Checkout canónico y retirada del duplicado

Fecha: 2026-10-30. El repositorio remoto es
`https://github.com/htm4rck/RNC.git`; la carpeta canónica es `Proyects/RNC`.

| Evidencia | RNC | RCN duplicado |
| --- | --- | --- |
| Último desarrollo funcional confirmado | `d6d6f37`, 26-10-2026 | `9aecc64`, 05-09-2026 |
| Rama remota consolidada antes de esta entrega | `114683d` | El mismo repositorio RNC |
| Historia exclusiva del duplicado | Todas sus ramas están contenidas en `develop` remoto | Ningún commit exclusivo |
| Trabajo local | Configuración CSS ya publicada | Ocho archivos de un prototipo de evaluación de oportunidades, más la misma configuración CSS |

Se conserva el desarrollo reciente de RNC, incluido el agente Firefox, lectura de
perfiles/vacantes y preparación de Easy Apply. El prototipo antiguo no se activa
en esta consolidación: sus ocho archivos se conservan para una evaluación separada.

La carpeta `RCN` fue retirada del directorio de proyectos mediante traslado
atómico completo a un respaldo local privado. Se conservan `.git`, ramas,
archivos pendientes e ignorados y datos locales; se verificaron las huellas de
los nueve archivos pendientes. No se borró una base de datos ni se mezclaron
datos de ambos clones.

Respaldo en este equipo:
`/home/marc/.cache/tordo-ui-homologation/batch3/duplicate-backup/RCN`.
La comparación detallada está junto al respaldo en `batch3/rnc-comparison.json`.

No había procesos ni contenedores en ejecución dependiendo de RCN. El contenedor
detenido `rcn_postgres` conserva una referencia a la ruta antigua de sus datos;
para reutilizarlo se debe restaurar explícitamente el respaldo o recrearlo con
la configuración y datos elegidos de RNC. Esta entrega no lo arranca ni elimina
sus datos.

Se reutiliza el build frontend aprobado del 30-10-2026. El único cambio nuevo de
RNC es este registro; el commit usa `[skip ci]` y no dispara otro build o despliegue.
El push se verifica por SHA y el clon RNC queda limpio y sincronizado en `develop`.
