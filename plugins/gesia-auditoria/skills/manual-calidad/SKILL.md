---
name: manual-calidad-gesia
description: >
  Manual de calidad de la firma (AudiQ, NIGC 1) en una sola página HTML que se abre sin
  internet: el mapa de los riesgos de la firma de nivel medio, alto y extremo en su matriz de
  probabilidad e impacto, las plantillas y modelos que cita cada procedimiento con su enlace
  al fichero, y el texto de cada procedimiento legible al pulsarlo. Usa este skill cuando el
  usuario pida ver o consultar el manual de calidad, el sistema de gestión de la calidad
  (SGCC), el mapa de riesgos de la firma, las plantillas o modelos del manual, o un
  procedimiento de AudiQ, o el cuadro de mando o panel del manual, de AudiQ o del SGCC, o diga
  cosas como "haz el cuadro de mando del manual", "dónde está la plantilla de la carta de
  renuncia" o "qué riesgos altos tiene la firma". Trabaja sobre un .qat o .qal de AudiQ: con
  uno activo, «cuadro de mando» es este skill. NO es un encargo (.gs3): sus riesgos son
  identificacion-riesgos y su estado, cuadro-mando. Requiere el servidor API de Gesia.
---

# Manual de calidad de la firma (AudiQ)

Una página con el manual de calidad de la firma para consultarlo sin abrir AudiQ: qué riesgos
de la firma están en nivel medio o superior, qué plantilla corresponde a cada procedimiento y
qué dice cada procedimiento. Solo sale lo que el manual tiene **disponible**.

La página se escribe en `<carpeta del manual>\AsistenteIA\ManualCalidad\`, junto al `.qat` o
`.qal`, y **tiene que quedarse ahí**: los enlaces a las plantillas son relativos a esa carpeta, y
si la página se mueve dejan de abrir. Si la firma mueve la carpeta del manual entera, con la
página dentro, siguen funcionando.

**No es un papel de trabajo** ni lleva bloque de uso de IA: es una vista del manual, sin
conclusiones. No se sella y **no se publica** en ninguna URL.

---

## Tres reglas que gobiernan todo

**1. Todo sale del manual.** Los niveles de riesgo, los textos y los vínculos son los que AudiQ
tiene guardados. Nada se resume, se reescribe ni se valora: el texto de cada procedimiento sale
tal cual, con formato.

**2. Los ficheros no se abren**: los lee el script. Tú solo ves cuántas filas tiene cada uno y el
resumen que imprime el script.

**3. Si el script dice que no, no hay página.** Antes de escribir comprueba que el fichero es un
manual de AudiQ, que la matriz de riesgo es la esperada y que cada nivel guardado casa con ella.
Si algo falla, para (salida 2) y dice qué: díselo al usuario tal cual. **No lo rodees** cambiando
datos ni filtros.

---

## Dónde están los scripts

Los scripts están en `skills/manual-calidad/scripts/`, dentro de la raíz del plugin instalado.

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

### Paso 1 — El manual

```
configurar(gs3_file = "<ruta del .qat o .qal>", perfil = "manual-calidad")
```

El parámetro se llama `gs3_file` pero vale para AudiQ: la extensión decide el producto. Es el
`.qat` (el manual en trabajo) o el `.qal` (el publicado) de la firma; los dos sirven igual. Si el
usuario no ha dado la ruta, **mira antes de preguntar**: lista la carpeta que tienes a mano.. Si en su raíz hay **un solo** `.qat` o
`.qal`, es ese: úsalo y dile cuál. Si hay varios o ninguno, **pídesela**. La respuesta tiene que decir `producto: audiQ`; si
dice Gesia, es un expediente de encargo y este skill no aplica.

**Si `configurar` avisa de que otra conversación está trabajando con otro fichero o perfil** en
el mismo servidor, **para**: díselo al usuario tal cual y no sigas hasta que confirme que esa otra
conversación ha terminado.

Si el servidor API no responde, llama a `arrancar_api`. **Si `configurar` no acepta el perfil
`manual-calidad`**, el plugin instalado es anterior a este skill: dile al usuario que lo
actualice y para.

### Paso 2 — Exportar lo que la página necesita

Son ocho ficheros, con estos nombres exactos, que son los que lee el script: `manual.json`,
`areas.json`, `valores_ria.json`, `ejes.json`, `riesgos.json`, `referencias.json`,
`guias.json` y `vinculos.json`.

Los ficheros exportados van a `<TRABAJO>`, que es una carpeta local: aquí no hay contenedor ni copias que subir. Es la carpeta de esta ejecución: no la compartas con otro procedimiento ni con otra conversación.


Cuando el MCP y los scripts comparten disco —en la máquina del usuario—, `<EXPORT>` es
`<TRABAJO>` mismo: se exporta ahí y el script lee de ahí, sin subir ni copiar nada.

**Estas consultas, tal cual.** Los campos de riesgo engañan —`CodigoValorRIA_RCI` es la
probabilidad y `CodigoValorRIA_RI` el impacto— y el script ya lo sabe: no los renombres.

```
exportar_consulta(
  sql = "SELECT c.Proyecto, c.TipoMDB, d.NombreFichero, d.Version, d.FechaPublicacion,
                d.HipervinculosRelativos, d.CodigoTipoFichero
         FROM ControlEnSys AS c, DatosAuditoria AS d",
  ruta = "<EXPORT>/manual.json")

exportar_consulta(sql = "SELECT CodigoArea, Area FROM Areas", ruta = "<EXPORT>/areas.json")

exportar_consulta(sql = "SELECT CodigoRIA, CodigoValorRIA, ValorRIA, Color FROM ValoresRIA",
                  ruta = "<EXPORT>/valores_ria.json")

exportar_consulta(
  sql = "SELECT 'P' AS Eje, CodigoValorRIA, ValorRIA FROM ValoresProbabilidadRIA
         UNION ALL SELECT 'I' AS Eje, CodigoValorRIA, ValorRIA FROM ValoresImpactoRIA",
  ruta = "<EXPORT>/ejes.json")

exportar_consulta(
  sql = "SELECT IdRiesgo, Riesgo, CodigoTipoRiesgo, CodigoArea, CodigoReferencia,
                CodigoValorRIA_RCI, CodigoValorRIA_RI, CodigoValorRIA_RIM,
                Descripcion, Procedimientos, Recomendacion
         FROM RiesgosNIAS",
  ruta = "<EXPORT>/riesgos.json")

exportar_consulta(
  sql = "SELECT CodigoReferencia, CodigoArea, Referencia, CodigoTipoGuia, CodigoClaseReferencia,
                Disponible, Comentario
         FROM Referencias",
  ruta = "<EXPORT>/referencias.json")

exportar_consulta(
  sql = "SELECT CodigoGuia, CodigoOrden, Punto, DesglosePunto, CodigoReferencia, Descripcion,
                FicheroVinculado
         FROM DetalleGuias",
  ruta = "<EXPORT>/guias.json")

exportar_consulta(entidad = "vinculos", ruta = "<EXPORT>/vinculos.json")
```

El último es el que dice, mirando el disco del usuario, qué plantillas existen: **el script no
puede comprobarlo él**. Si `exportar_consulta` no admite `entidad = "vinculos"`, el plugin es
anterior a este skill: dile al usuario que lo actualice y para.

Si `exportar_consulta` dice que ha enmascarado identificadores, es lo normal: tapa siempre DNI,
CIF, teléfonos y similares, y en un manual suele ser el NIF de la propia firma. Sigue; el script
lo cuenta y se dice al entregar.

### Paso 3 — Generar la página

```bash
python "<PLUGIN>\skills\manual-calidad\scripts\generar_manual.py" --datos "<TRABAJO>" --generado "<fecha de hoy, AAAA-MM-DD>" \
    --salida "<TRABAJO>"
```

`--generado` es la fecha de hoy, que conoces por tu contexto: **la pones tú**, nada en este skill
lee el reloj. `--salida` es una carpeta: **el nombre de la página lo pone el script**: el del
manual tal como sale en AudiQ, **sin versión** y sin los caracteres que Windows no admite, para que
rehacer la página pise la anterior. Lo imprime en la línea `nombre:`. Ese es `<PÁGINA>` en todo
lo que sigue.

Salida `2` → **para**: falta un fichero, no tiene la forma esperada o no cumple el contrato, y lo
dice. Salida `0` → imprime los recuentos (riesgos por nivel, procedimientos, plantillas, rotas) y,
si los hay, los avisos de `PARA CONTAR AL ENTREGAR`. **No abras la página ni leas sus datos**: el
resumen de pantalla ya trae lo que hay que contar.

**Si ya hay una página en el destino, pregunta antes de dejar la nueva.** Mira si en
`<carpeta del manual>\AsistenteIA\ManualCalidad\` hay **cualquier** fichero `.html`, no solo uno
con el nombre de ahora. Esa carpeta es solo de este
manual, así que cualquier página que haya es una anterior, aunque se llame de otra forma: las de
versiones anteriores del skill llevaban otro nombre (con la versión del manual, o el título de la
página), y la del manual cambia si se renombra en AudiQ. Si hay alguna, **di cuáles y pregunta
al usuario**:

- **sustituirla** —lo habitual: es una vista del manual, y la nueva refleja su estado de hoy—. Si
  se llama igual, la nueva la pisa; si se llama distinto, deja la nueva y pide al usuario que
  borre la anterior, diciéndole su nombre: no la borres tú;
- o **guardar la nueva al lado** con « (rehecho AAAA-MM-DD)» antes de la extensión, con la fecha
  de hoy.

Ni la sustituyas sin preguntar ni inventes otro sufijo.

**Déjala en su sitio.** En local, cópiala:

```bash
mkdir -p "<carpeta del manual>/AsistenteIA/ManualCalidad"
cp "<TRABAJO>/<PÁGINA>" "<carpeta del manual>/AsistenteIA/ManualCalidad/<PÁGINA>"
```

Pásale a `--salida` la ruta del expediente directamente: el script crea el árbol `AsistenteIA`. Si el expediente está en OneDrive, el entorno puede pedir autorización antes de escribir: pídesela al usuario y repite.

**Si la carpeta está en OneDrive, el entorno puede rechazar la escritura antes de ejecutar nada**
y pedir autorización expresa. No es un fallo del skill: pídesela al usuario y repite.

### Paso 4 — Entregar

El mensaje de entrega es **el último**: va después de limpiar los temporales (paso 5), porque
lleva también lo que diga la limpieza.

Di dónde ha quedado la página, que se abre con doble clic en el navegador, sin internet, y que
**no hay que moverla** de esa carpeta o las plantillas dejan de abrir. Cuenta **los recuentos del
script** y, si los hubo, los avisos —sobre todo las plantillas **rotas**, que son ficheros que el
manual enlaza y no están donde dice—. Y si `limpiar_exportaciones` avisó de ficheros que no son de
este procedimiento (`aviso` / `no_escritos_por_mi`), cuéntalo **aparte, en una línea**, con su
carpeta: pueden llevar datos de un cliente de otra sesión.

> *Manual de calidad en `AsistenteIA\ManualCalidad\<fichero>`, junto al manual; se abre con doble
> clic, sin internet, y tiene que quedarse en esa carpeta para que las plantillas abran. En el mapa
> hay N riesgos de nivel medio o superior (E extremo, A alto, M medio); P procedimientos y T
> plantillas, de las que R no se encuentran: … Los extractos temporales están borrados.*
>
> *Aparte, y no es de este procedimiento: la limpieza ha visto N fichero(s) de otras sesiones en
> `<carpeta>`, del `<fecha>`; no los he tocado, míralos.*

Dos cosas que conviene decir si vienen al caso:

- **El nombre de la página sale del nombre del manual dentro de AudiQ**, no del nombre del fichero
  en el disco. Si el usuario ha renombrado el `.qal` sin volver a publicar el manual, el nombre de
  la página no cambia: cambia al republicarlo.

### Paso 5 — Los temporales

Lo que haya escrito `exportar_consulta` lo borra
`limpiar_exportaciones(procedimiento = "manual-calidad")`, y esa es la vía: funciona igual en
local y en Cowork —lo borra el MCP, que corre en la máquina del usuario— y borra solo lo que él
escribió **para este procedimiento**. Lo exportado por otros lo deja y lo resume: no lo borres
tú, dilo tal cual. Si algo no se deja borrar, lo dice con su ruta: trasládala al usuario.

El directorio de trabajo va aparte, y se borra **desde fuera**, sin estar dentro de él:

```bash
rm -rf "<TRABAJO>"
```

Si no se deja borrar, **di la ruta exacta** de `<TRABAJO>` y qué contiene —los extractos del
manual y la copia de la página— para que el usuario lo quite.

### Si después preguntan por un procedimiento

La página ya tiene el texto de cada procedimiento: lo primero es mandar ahí al usuario («pulsa F)03
en Procedimientos»). Si hay que consultarlo en el manual, el texto de un procedimiento está en
`DetalleGuias` **por `CodigoGuia`**, que es el código del procedimiento:

```
consultar_gesia(sql = "SELECT CodigoOrden, DesglosePunto, Left(Descripcion, 300) AS Texto
                       FROM DetalleGuias WHERE CodigoGuia = 'F)03' ORDER BY CodigoOrden")
```

**No por `CodigoReferencia`**: en `DetalleGuias` ese campo es el código que **cita** cada punto
—una plantilla, otro procedimiento—, no el procedimiento al que pertenece. Filtrar por él da cero
filas y parece que el procedimiento no existe. `Descripcion` es memo: pide un trozo con `Left()`,
nunca entera.

---

## Qué enseña la página

| Bloque | Qué lleva |
|---|---|
| Mapa de riesgos | la matriz 5×5 (probabilidad en vertical, impacto en horizontal) con los riesgos de nivel **medio, alto y extremo**; al pulsar una casilla, la lista se queda con sus riesgos. Cada riesgo, con descripción, respuesta prevista y recomendación, y enlace a su procedimiento o a las plantillas de su área. Filtros de área y de tipo (O.I. o calidad) |
| Plantillas | el índice del manual: **todos** los procedimientos disponibles de cada área, cada uno con las plantillas que cita o con «sin plantillas citadas»; al final, las plantillas del área que no cita ninguno. Cada plantilla abre su fichero o dice que no se encuentra. El buscador encuentra procedimientos por código o título y plantillas por código o nombre |
| Procedimientos | los procedimientos disponibles por área; al pulsar uno se abre su texto completo con sus títulos y listas, sus plantillas y sus diagramas. Los códigos de plantilla del texto abren el fichero; los de otro procedimiento, ese procedimiento. Buscador en el texto |

## Lo que este skill no hace

- **No escribe en AudiQ.** El MCP solo lee; la página va a `AsistenteIA`.
- **No valora ni identifica riesgos**: enseña la valoración que el manual ya tiene. Los riesgos
  muy bajos, bajos y sin valorar no salen.
- **No enseña lo no disponible**: ni procedimientos, ni sus plantillas, ni el enlace desde un
  riesgo.
- **No resume ni reescribe** el texto del manual.
- **No es un encargo de auditoría**: para los riesgos de un cliente, identificacion-riesgos; para
  el estado de un encargo, cuadro-mando.
- **No es evidencia de auditoría** ni lleva bloque de uso de IA. **No se publica** en ninguna URL.

## Degradación

| Situación | Qué sale |
|---|---|
| Ningún riesgo de nivel medio o superior | la matriz sin casillas activas y la lista vacía; el script lo avisa |
| Riesgos sin valorar | no salen; el script dice cuántos |
| Riesgo que apunta a algo no disponible o que no existe | sale, sin enlace; el script lo cuenta |
| Procedimiento sin texto en su guía | sale con el resumen de la referencia; el script lo avisa |
| Plantilla sin fichero vinculado | sale, con «sin fichero vinculado» |
| Plantilla cuyo fichero no está | sale, marcada «no se encuentra el fichero»; el script la nombra |
| Punto de la guía con el título y el texto juntos | el título sale como título y el texto como texto |
| La página abierta fuera de `AsistenteIA\ManualCalidad\` | lo avisa arriba con la ruta correcta y abre las plantillas por su ruta completa en ese equipo |
| Fecha de publicación posterior a la de hoy | sale; el script lo avisa |
| Un procedimiento cita una plantilla con el código mal escrito (`AQ)03` por `F)AQ/03`) | queda como texto y la plantilla, en «otras del área»; el script nombra cada cita y, si la ve, la plantilla que seguramente quería decir. Se corrige en AudiQ |
| El nombre del manual y su campo de versión no dicen la misma versión | la página lleva las dos; el script lo avisa |
| No es AudiQ, no es un manual, la matriz no es la esperada o un nivel no casa con ella | **para** (salida 2), y dice por qué |
| Falta un fichero, no es JSON o le falta una columna | **para** (salida 2), y dice cuál |
