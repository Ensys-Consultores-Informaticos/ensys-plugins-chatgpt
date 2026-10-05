# Plugins de Ensys para ChatGPT Desktop y Codex

Procedimientos de auditoría que trabajan directamente sobre el expediente de Gesia o sobre
el cliente de muestreo de ForSampling, y producen papeles de trabajo en Excel y Word. Cada
plugin incluye el servidor MCP local para Windows que lee los ficheros.

Hay **dos plugins** y se instala **uno solo**:

| Plugin | Para quién | Qué lleva |
|---|---|---|
| **Gesia — Expediente de auditoría** | Quien tiene la suite de Gesia | Todos los procedimientos de este canal, incluidas las pruebas de muestreo de ForSampling |
| **ForSampling — Pruebas de muestreo** | Quien tiene ForSampling sin Gesia | Las pruebas de muestreo, el papel de la NIA-ES 530 y el registro de ejecución |

Los dos comparten el programa que lee los ficheros, y con los dos activos no se sabe cuál
contesta. Si pasa, `configurar` lo avisa y dice cuál sobra.

## Instalación

En la app de ChatGPT, **Ajustes > Complementos**:

1. Pulsa **Añadir** > **Añadir un marketplace** y escribe:

   ```
   Ensys-Consultores-Informaticos/ensys-plugins-chatgpt
   ```

2. Reinicia la app. En **Ensys Plugins**, instala **Gesia — Expediente de auditoría** o
   **ForSampling — Pruebas de muestreo**, el que te corresponda.
3. Abre un chat nuevo. La descripción del plugin termina en `(MCP X.Y.Z) (vA.B.C)`: el
   primero es el programa que lee los ficheros y el segundo, el plugin.

**Para actualizar**, en la pestaña **Tienda** pulsa **Actualizar** junto a Ensys Plugins,
actualiza el plugin y reinicia la app: hasta que no reinicias, sigue cargado el servidor
anterior. Si algo no cuadra, lo más limpio es desinstalar el plugin, borrar el
marketplace con la papelera y volver a añadirlo.

## Requisitos

- **Windows**, y **Gesia** o **ForSampling** instalado.
- El **servidor API** tiene que estar en marcha. El plugin lo arranca solo si no responde;
  con Gesia, a mano sigue estando en *Herramientas > Gesia - Cuadro de mando > Arrancar
  servidor API*.
- Solo para consultar diarios `.smn`, **Microsoft Access Database Engine 2016 de 64 bits**.
  Las consultas al expediente `.gs3` no lo necesitan.

## Empezar

No se distribuye ninguna ruta de expediente, porque cada usuario y cada encargo tienen la
suya. Llama a `configurar` al empezar la sesión con la ruta del fichero y el servidor
responde con el cliente que ha encontrado, el diario vinculado y si el servidor API
contesta: conviene leer eso antes de seguir.

- **Con el plugin de Gesia**, la ruta del `.gs3`. La del diario está dentro del propio expediente y
  se deduce sola.
- **Con el de ForSampling**, la del cliente de muestreo, el `.cli`. El `.cli` no vincula
  ningún diario: cuando una prueba lo necesita, el plugin lo busca entre los que
  ForSampling ha importado y te lo propone para que lo confirmes.

`exportar_consulta` deja el resultado de una consulta en un fichero en vez de devolverlo,
que es como se trabaja con volúmenes grandes sin traérselos al chat. Esos ficheros llevan la
contabilidad del cliente, así que **al terminar hay que llamar a `limpiar_exportaciones`**,
que borra los que el propio servidor ha escrito. Si no se llama, se quedan en el disco.

## Procedimientos incluidos

Cada uno lee el expediente por el MCP, calcula con sus propios scripts y deja el papel de
trabajo en `AsistenteIA`, dentro del expediente o del cliente de muestreo. Son
**propuestas de papel de trabajo**: la valoración, el alcance y la conclusión son del
auditor que firma. La columna de la derecha dice qué lleva el plugin de ForSampling; el de
Gesia lleva todos.

| Procedimiento | Qué hace | ForSampling |
|---|---|---|
| `continuidad-saldos` | Compara la apertura del diario con los saldos auditados del ejercicio anterior | — |
| `cancelacion-saldos` | Empareja facturas con sus pagos y cobros, y deja a la vista el saldo vivo | — |
| `cuestionario-cuentas-anuales` | Revisa qué desgloses faltan en la memoria, leyendo las cuentas anuales en PDF | — |
| `estados-financieros` | Balance y cuenta de resultados comparados, la conciliación de lo presentado por el cliente a lo auditado, el patrimonio neto y el estado de flujos de efectivo con sus ajustes | — |
| `identificacion-riesgos` | Elige los riesgos del catálogo del máster conforme a la NIA-ES 315 | — |
| `fsp-cumplimiento` | Valida la muestra de una prueba de cumplimiento de ForSampling contra las facturas escaneadas | Sí |
| `fsp-mum` | Lo mismo para una prueba de muestreo por unidad monetaria | Sí |
| `fsp-mum-nia530` | Redacta en Word el papel de trabajo de la NIA-ES 530 de una prueba MUM, leído de los ficheros de ForSampling; la conclusión queda en blanco, que es del auditor | Sí |
| `registro-ejecucion` | Escribe en el chat cómo ha ido la ejecución, para reportar incidencias | Sí |

Dos procedimientos que sí están en el canal de Claude **no se distribuyen aquí**: el cuadro
de mando del diario, pendiente de rehacerse, y la investigación de la entidad en fuentes
públicas, que necesita subagentes y Codex no los tiene.

## Qué sale del equipo y qué no

Es lo que no se puede deducir mirando el resultado, así que conviene saberlo para usar el
plugin con criterio:

- **Los nombres de proveedores y clientes viajan anonimizados.** El asistente ve un código
  por cuenta, no la razón social, y el papel de trabajo recupera los nombres reales en tu
  equipo al entregarlo.
- **Las facturas escaneadas se tachan en tu equipo antes de subirlas.** Los PDF no salen de
  tu disco: sube una imagen por página con el nombre del emisor, la cabecera, el CIF, el
  IBAN, el teléfono, el correo, el pie y los márgenes en negro. **Importes, fechas y número
  de documento quedan legibles**, que es lo que la prueba necesita mirar.
- **Tú eliges.** Al empezar se te pregunta si quieres las facturas tachadas o tal cual, y con
  qué consecuencias. No se decide por ti ni se arrastra de una sesión a otra.
- **Lo que no se puede tapar se te dice.** El nombre se tapa cuando se reconoce al tercero en
  el plan de cuentas del expediente. Un membrete que es solo un logotipo, un tercero que no
  está en ese plan —un banco, un transportista— o un nombre que el reconocimiento de texto
  parte en dos renglones pueden subir a la vista. **Cuando pasa se te avisa antes de subir
  nada**, con la cuenta, para que mires esas imágenes en tu carpeta y decidas. Es la parte
  que no se puede prometer.

No compartas expedientes `.gs3`, diarios `.smn`, ficheros `config.toml`, credenciales ni
rutas personales: nada de eso hace falta para que el plugin funcione.

## Límite importante: ChatGPT Desktop frente a ChatGPT web

Este plugin contiene un ejecutable Windows y usa MCP mediante `stdio`, así que funciona en
superficies locales capaces de ejecutar el servidor: **ChatGPT Desktop y Codex en Windows**.
No funciona en `chatgpt.com`, que necesitaría exponer el servidor por un endpoint MCP HTTPS
público o un túnel; ese despliegue no forma parte de esta distribución.

## Diagnóstico

- Si el plugin no aparece, comprueba en **Ajustes > Complementos > Tienda** que está **Ensys
  Plugins**, pulsa **Actualizar** y reinicia la app.
- Si el servidor no arranca, comprueba que Windows no haya bloqueado el ejecutable y
  verifica su SHA-256 con `Get-FileHash` contra el `SHA256SUMS.txt` de su plugin
  (`plugins/gesia-auditoria/` o `plugins/forsampling-auditoria/`).
- Si no hay conexión con el servidor API, llama a `arrancar_api` o arráncalo a mano.
- Si no encuentra el expediente o el cliente de muestreo, llama a `configurar` con la ruta
  correcta.
- Si solo fallan los diarios `.smn`, revisa Microsoft Access Database Engine 2016 de 64 bits.
- Si una actualización no se refleja, desinstala el plugin, borra el marketplace con la
  papelera, vuelve a añadirlo y reinicia la app.

## Soporte

`gesia_mcp-*.exe` es software propietario de Ensys Consultores Informáticos, S.L.
Para incidencias, el propio plugin trae un **registro de ejecución** que las resume de forma
anónima: pídelo con «cómo ha ido».
