---
name: cuadro-mando-gesia
description: >
  Cuadro de mando de un expediente de Gesia en una sola página HTML, que se abre en el
  navegador sin internet: estado de la auditoría por áreas (referencias realizadas y
  verificadas), importancia relativa global y por área, los riesgos del encargo ya
  identificados, la cédula principal de cada área con cinco ejercicios y su variación
  contra la IR del área, y los ratios con su evolución. Usa este skill cuando el usuario
  pida el cuadro de mando, el panel o el dashboard del expediente, ver cómo va la
  auditoría, el estado del encargo o el avance por áreas, o diga cosas como "saca el
  cuadro de mando", "cómo vamos con este cliente" o "enséñame la cédula del área de
  compras con su variación". NO identifica riesgos nuevos (eso es identificacion-riesgos),
  no es la revisión analítica, ni la revisión de los estados financieros, ni una prueba
  de auditoría. Es para un .gs3: con un .qat o .qal de AudiQ, es manual-calidad. Requiere
  Gesia abierto con el servidor API arrancado.
---

# Cuadro de mando del expediente (Gesia)

Una foto del encargo en una página: cómo va, cuánto pesa la importancia relativa en cada
área, qué riesgos hay identificados y qué cuentas se han movido más que la IR. Replica el
Excel «Cuadro de mando Gesia» que usa la firma, sin Power Query ni modelo de datos: los filtros
son de la propia página.

La página se escribe en `<expediente>\AsistenteIA\CuadroMando\` y **nunca se publica** en
ninguna URL —ni como artifact ni en ningún servicio—: son las cifras de un cliente auditado.

**No es un papel de trabajo** y no lleva bloque de uso de IA: es una vista de lo que ya hay
en el expediente, sin conclusiones. No se sella.

---

## Cuatro reglas que gobiernan todo

**1. Todo sale del expediente, y nada se calcula de memoria.** La importancia relativa, el
avance, los riesgos, la cédula y los ratios son los que Gesia tiene guardados. Si la IR no se
ha calculado en Gesia, el panel lo dice; no la estimes tú.

**2. La cédula es la que marca el expediente:** las cuentas con `AsignadaCedulaPrincipal`
activado, cada una en su área (`CodigoAreaCP`). No se eligen otras cuentas ni se añade un nivel
de detalle que el expediente no tenga.

**3. Los ficheros no se abren**: los lee el script. Tú solo ves cuántas filas tiene cada uno y
el resumen que imprime el script.

**4. El panel no concluye.** Marca en rojo las cuentas cuya variación del último ejercicio
supera la IR de trabajo de su área, y nada más. Por qué se mueven lo averigua el auditor.

---

## Dónde están los scripts

Los scripts están en `skills/cuadro-mando/scripts/`, dentro de la raíz del plugin instalado.

**Sustituye los marcadores de los ejemplos por rutas reales antes de ejecutar.** No uses
variables de shell: en Windows el intérprete no siempre es el mismo y una variable que
funciona en una consola no existe en la otra.

- `<PLUGIN>` — la raíz del plugin instalado
- `<TRABAJO>` — una carpeta de trabajo local NUEVA para esta ejecución, con el nombre del
  procedimiento y la hora, fuera del expediente. No reutilices la de otro procedimiento ni la
  de otra conversación: los ficheros de trabajo se pisarían. Entrega los papeles por su nombre
  exacto, nunca con un comodín, y al terminar bórrala; si no se deja, di su ruta exacta.

**ChatGPT Cowork corre en el equipo del auditor**: los scripts y el MCP comparten disco, así
que lo que exporta el MCP lo leen los scripts directamente y el papel se escribe en la ruta
del expediente sin pasos intermedios.

---

## Secuencia

### Paso 1 — Expediente

```
configurar(perfil = "cuadro-mando")   # primero: marca el comienzo y seudonimiza terceros
contexto_expediente()                 # siempre, aunque ya lo tengas de antes
```

**Lo primero, antes de leer nada: `configurar(perfil = "cuadro-mando")`.** Con el perfil, el MCP
**seudonimiza los nombres de terceros** en todo lo que devuelve: si la cédula principal llega a
una cuenta de tercero, verás `PROV 40000012` o `CLI 43000007` donde iría la razón social. El
nombre no sale del equipo del auditor; la página lo recupera al final con `rehidratar`. **Nunca
preguntes al auditor a quién corresponde un token ni lo adivines.** Si `configurar()` dice
`nombres_terceros: en claro — forzado por el auditor`, es que lo ha apagado él; no lo vuelvas a
encender tú.

**Y después de `configurar`, llama SIEMPRE a `contexto_expediente()`**: de ahí salen el cliente
y la fecha de cierre para el nombre del fichero.

| Hueco | Qué es | De dónde sale |
|---|---|---|
| `<CLIENTE>` | el cliente | `RazonSocialCliente` de `contexto_expediente` |
| `<ejercicio>` | el ejercicio que se audita | el año de la `FechaCierre` de `contexto_expediente` |

**Si `configurar` avisa de que otra conversación está trabajando con otro expediente o perfil**
en el mismo servidor, **para**: díselo al auditor tal cual y no sigas hasta que confirme que esa
otra conversación ha terminado. Las dos comparten el MCP y se pisan el expediente y el perfil.

Si falta `gs3_file`, **pide la ruta**. Si el servidor API no responde, llama a `arrancar_api`.
El diario **no hace falta**: este skill no lo lee.

### Paso 2 — Exportar lo que el panel necesita

Son cinco ficheros, con estos nombres exactos, que son los que lee el script: `contexto.json`,
`ir_areas.json`, `riesgos.json`, `cedula.json` y `ratios.json`.

Los ficheros exportados van a `<TRABAJO>`, que es una carpeta local: aquí no hay contenedor ni copias que subir. Es la carpeta de esta ejecución: no la compartas con otro procedimiento ni con otra conversación.


Cuando el MCP y los scripts comparten disco —en la máquina del auditor—, `<EXPORT>` es
`<TRABAJO>` mismo: se exporta ahí y el script lee de ahí, sin subir ni copiar nada.

**Estas consultas, tal cual**: están medidas contra el Excel de la firma y cuadran al céntimo.

```
exportar_consulta(entidad = "contexto", ruta = "<EXPORT>/contexto.json")
exportar_consulta(entidad = "ratios",   ruta = "<EXPORT>/ratios.json")

exportar_consulta(
  sql = "SELECT ETAreas.CodigoArea, Areas.Area,
                IIf([Coef_Unico],[Coef_Fijo_T],[ET_T]) AS IR_Trabajo,
                IIf([Coef_Unico],[Coef_Fijo_I],[ET_I]) AS IR_Informe
         FROM CalculosIRFuentesDatos, ETAreas INNER JOIN Areas ON ETAreas.CodigoArea = Areas.CodigoArea
         WHERE ETAreas.CodigoEleccionCalculosIR = 1 AND Areas.DisponibleCalculoET = True",
  ruta = "<EXPORT>/ir_areas.json")

exportar_consulta(
  sql = "SELECT IdRiesgo, CodigoArea, Riesgo, Significativo, AMRA, TipoRiesgo, Clasificacion,
                CodigoValorRIA_RI, CodigoValorRIA_RCI, CodigoValorRIA_RIM,
                Integridad, Existencia, Exactitud, Valoracion, CodigoReferencia
         FROM RiesgosNIAS",
  ruta = "<EXPORT>/riesgos.json")

exportar_consulta(
  sql = "SELECT ca.Cuenta, c.Nombre, c.CodigoAreaCP, a.[Año], a.CodigoAuditoria, ca.SaldoAuditoria
         FROM (CuentasAuditorias AS ca INNER JOIN Auditorias AS a ON ca.CodigoAuditoria = a.CodigoAuditoria)
              INNER JOIN Cuentas AS c ON ca.Cuenta = c.Cuenta
         WHERE c.AsignadaCedulaPrincipal = True",
  ruta = "<EXPORT>/cedula.json")
```

Si `cedula.json` sale con cero filas, el expediente no tiene ninguna cuenta marcada para la
cédula principal: sigue —el panel sale sin cédula— y díselo al auditor al entregar.

### Paso 3 — Generar la página

**Si la página ya existe, pregunta antes de generarla.** Mira si en
`<expediente>\AsistenteIA\CuadroMando\` ya hay un fichero con ese nombre.
Si lo hay, **pregunta al auditor** si lo sustituye —lo habitual en un cuadro de mando, que es
una foto del momento— o si guarda el nuevo con « (rehecho AAAA-MM-DD)» antes de la extensión,
con la fecha de hoy. Ni lo sustituyas sin preguntar ni inventes otro sufijo. El nombre elegido
es el de todo lo que sigue.

```bash
python "<PLUGIN>\skills\cuadro-mando\scripts\generar_cuadro.py" --datos "<TRABAJO>" --generado "<fecha de hoy, AAAA-MM-DD>" \
    --salida "<TRABAJO>/Cuadro de mando <CLIENTE> <ejercicio>.html"
```

`--generado` es la fecha de hoy, que conoces por tu contexto: **la pones tú**, nada en este
skill lee el reloj.

Salida `2` → **para**: falta un fichero o no tiene la forma esperada, y lo dice. Salida `0` →
imprime los recuentos (áreas, riesgos, cuentas de la cédula, ratios), las cuentas cuya
variación supera la IR de su área y, si los hay, los avisos de `PARA CONTAR AL ENTREGAR`.
**No abras la página ni leas sus datos**: el resumen de pantalla ya trae lo que hay que contar.

Pásale a `--salida` la ruta del expediente directamente: el script crea el árbol `AsistenteIA`. Si el expediente está en OneDrive, el entorno puede pedir autorización antes de escribir: pídesela al usuario y repite.

**Si el expediente está en OneDrive, el entorno puede rechazar la escritura antes de ejecutar
nada** y pedir autorización expresa para escribir datos contables ahí. No es un fallo del skill:
pídesela al usuario y repite.

### Paso 4 — Recuperar los nombres y entregar

Con la página **ya en el disco del auditor**, en `<expediente>\AsistenteIA\CuadroMando\`:

```
rehidratar(ruta = "<expediente>/AsistenteIA/CuadroMando/<PÁGINA>")
```

Sustituye cada token por el nombre real, en local, y devuelve recuentos —ni un nombre vuelve
aquí—. Si devuelve cero sustituciones, es lo normal cuando la cédula no llega a cuentas de
tercero: no lo cuentes como fallo. Si hay `tokens_sin_nombre`, dilos tal cual.

Luego di dónde ha quedado la página y que se abre con doble clic en el navegador, sin internet.
Cuenta **los recuentos del script** y **las cuentas que superan la IR de su área**, por área y
con su variación, y los avisos si los hubo. Sin llamar «rehidratar» a nada delante del auditor:

> *Cuadro de mando en el expediente: `AsistenteIA\CuadroMando\<fichero>`; se abre con doble
> clic, sin internet. N áreas, M riesgos (S significativos), C cuentas en la cédula principal y
> R ratios. Superan la IR de su área: … El selector de área de «Análisis del área» filtra la
> cédula, la IR y los riesgos de esa área; el estado, la IR y los riesgos de arriba son siempre
> de todo el encargo. Los extractos temporales están borrados.*

**Aquí el papel es uno solo**: el del expediente. No hay copia de chat ni contenedor por el que viajar, así que en cuanto recuperas los nombres lleva los nombres reales en el disco del auditor. Dilo tal cual, para que sepa que ese fichero ya no está seudonimizado y trate el sitio donde lo deje en consecuencia.

### Paso 5 — Los temporales

Lo que haya escrito `exportar_consulta` lo borra
`limpiar_exportaciones(procedimiento = "cuadro-mando")`, y esa es la vía: funciona igual en
local y en Cowork —lo borra el MCP, que corre en la máquina del usuario— y borra solo lo que él
escribió **para este procedimiento**. Lo exportado por otros lo deja y lo resume en unas líneas:
no lo borres tú, dilo tal cual. Si algo no se deja borrar, lo dice con su ruta: trasládala al
usuario.

El directorio de trabajo va aparte, y se borra **desde fuera**, sin estar dentro de él:

```bash
rm -rf "<TRABAJO>"
```

Si no se deja borrar, **di la ruta exacta** de `<TRABAJO>` y qué contiene —los extractos del
cliente y la copia de la página— para que el usuario lo quite.

---

## Qué enseña la página

| Bloque | Qué lleva | Filtro de área |
|---|---|---|
| Estado de la auditoría | referencias realizadas y verificadas por área, con su barra | no: todo el encargo |
| Importancia relativa | IR de planificación, trabajo e informe, y la de cada área | no: todo el encargo |
| Riesgos del encargo | todos, con significativo, AMRA, valoración y afirmaciones | no: todo el encargo |
| Análisis del área | la cédula principal con cinco ejercicios, la variación, la IR y los riesgos del área, y un gráfico de las cuentas que se marquen | **sí**: el selector de área |
| Ratios | valor por ejercicio con su evolución; filtros de naturaleza, familia, relevancia y fase; una casilla oculta los que no tienen datos | no |

El área elegida se recuerda en el navegador, y un enlace con `#<código de área>` al final la
abre ya seleccionada.

## Lo que este skill no hace

- **No escribe en el expediente** de Gesia. El MCP solo lee; la página va a `AsistenteIA`.
- **No lee el diario.** Todo sale del `.gs3`.
- **No identifica ni valora riesgos**: enseña los que ya hay en `RiesgosNIAS`. Para
  identificarlos está identificacion-riesgos.
- **No explica las variaciones**, solo marca las que superan la IR del área.
- **No es evidencia de auditoría** ni lleva bloque de uso de IA: es una vista del expediente.
- **No se publica** en ninguna URL.

## Degradación

| Situación | Qué sale |
|---|---|
| IR sin calcular en Gesia | sale, con la IR vacía, y el script lo avisa: dilo al entregar |
| Ninguna cuenta con `AsignadaCedulaPrincipal` | sale sin cédula; dilo al entregar |
| Cuentas de la cédula sin área (`CodigoAreaCP` vacío) | no salen, y el script dice cuántas |
| Sin riesgos identificados | sale, con el bloque de riesgos vacío |
| Ratios sin calcular | salen sin valores; la casilla los oculta |
| Un solo ejercicio | sale sin variación ni marca roja |
| Falta un fichero o no es JSON | **para** (salida 2), y dice cuál |
