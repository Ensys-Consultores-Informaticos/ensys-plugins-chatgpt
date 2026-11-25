"""Apertura del diario y mapeo de cuentas para la prueba de continuidad de saldos.

No imprime: devuelve datos. Quien llama decide que hacer con ellos.

Desde la 1.25.0 del MCP el diario NO sale entero del equipo del auditor. Antes el skill
comprimia el .smn y lo subia al contenedor de Cowork para leerlo con mdbtools: todas las
tablas y columnas, nombres y conceptos incluidos, para usar un solo asiento. Ahora el MCP
exporta dos cosas pequenas y nada mas:

  1. la configuracion de normalizacion (campo Datos de CfgNormalizacion), con SQL_FILTRO:
     el FiltroDeApertura y la plantilla de campos con que se normalizo el diario;
  2. el asiento de apertura, con la consulta que arma sql_apertura() a partir de eso:
     solo las columnas que la prueba usa, el filtro evaluado en JET como POR_FILTRO,
     y los nombres de terceros seudonimizados por el perfil.

La apertura se identifica de una de dos maneras, y ninguna se adivina (25/11/2026):
  - por el FiltroDeApertura que el auditor definio al normalizar, o
  - si no hay filtro y el diario se normalizo con la plantilla que trae el campo
    APERTURA, por ese campo: la apertura son las lineas con APERTURA <> 0.

Es la minimizacion del dato: a la herramienta solo va lo que el procedimiento necesita.
El expediente (.gs3) llega igual que siempre, en el JSON que exporta el MCP.
Ver docs/contrato-datos.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

# Redondeo del euro. Los importes del diario llegan con error de coma flotante
# (86863532.92000002 frente a 86863532.92000031 para el mismo numero), asi que
# todo se redondea a 2 decimales ANTES de comparar. Decidido en cliente.
DECIMALES = 2

# Grupos que entran en la prueba: solo balance. Los grupos 6 y 7 se regularizan
# contra resultados al cierre y no tienen saldo de apertura; el 0, el 8 y el 9
# quedan fuera (23/08/2026).
GRUPOS_BALANCE = ("1", "2", "3", "4", "5")

# Operadores del FiltroDeApertura que este skill sabe traducir. La notacion la
# genera el modulo .NET de importacion de Gesia (ForSampling): los nombres son los
# del codigo que traduce el filtro en GesiaIA, portado de ese importador. Ante un
# operador desconocido se ABORTA en vez de adivinar: interpretar mal el filtro
# selecciona el asiento equivocado y el resultado sale plausible y falso.
#
# Medido el 28/10/2026 en 391 diarios reales: los 112 que traen filtro usan
# «Es igual a» o «Comienza por», todos de tipo Texto y de una sola fila. Los
# nombres anteriores («es distinto de», «empieza por», «termina por») no los
# genera Gesia; se quedan como sinonimos para no romper nada.
OPERADORES = {
    "es igual a": "==",
    "es distinto a": "!=",
    "comienza por": "empieza",
    "contiene": "contiene",
    "finaliza por": "termina",
    "no contiene": "no_contiene",
    # sinonimos anteriores
    "es distinto de": "!=",
    "empieza por": "empieza",
    "termina por": "termina",
}

# Operadores que Gesia SI genera y este skill NO traduce: se para diciendo cual es.
# Ninguno aparece en los 391 diarios medidos, y traducirlos exige decidir como se
# comparan numeros, fechas y booleanos, que aqui se comparan como texto.
NO_SOPORTADOS = {
    "rango": "compara entre Valor1 y Valor2, y aqui el campo se compara como texto",
    "es": "compara un campo Verdadero/Falso",
}

# En Gesia, cualquier otro texto en la casilla del operador va tal cual a la consulta
# como comparador (>, <, >=...). Se para igual, pero diciendo que es eso.
COMPARADORES = (">", "<", ">=", "<=", "=", "<>")

# Valor1 = «<nulo>» es campo vacio (IS NULL / IS NOT NULL). En GesiaIA no se traduce
# igual en todos los operadores, asi que no hay una semantica que copiar: se para.
VALOR_NULO = "<nulo>"

# El filtro vive en CfgNormalizacion, en el registro cuyo Concepto es FiltroDeApertura, y
# la plantilla con que se normalizo el diario en el registro «Configuracion de campos».
# Las dos cosas van en la misma consulta y solo se pide Datos: Concepto se llama como la
# columna del diario que el MCP retiene, y el MCP quita del fichero toda columna que no
# este en la lista blanca del perfil. Las filas se distinguen por la forma de Datos: el
# filtro es CAMPO|Tipo|Operador|..., la plantilla un numero. El acento de «Configuracion»
# se esquiva con el comodin. No se filtra por TipoNormalizacion: hay .smn antiguos sin esa
# columna, y la consulta fallaria donde la de solo el filtro funcionaba (medido el 25/11/2026).
SQL_FILTRO = ("SELECT Datos FROM CfgNormalizacion WHERE Trim(Concepto) = 'FiltroDeApertura' "
              "OR Concepto LIKE 'Configuraci%campos'")

# Las plantillas de ForSampling para normalizar un diario («Configuracion de campos»).
# Medido el 25/11/2026: 242 diarios reales con la 0 y 6 con la 1, y un diario de la 2
# hecho para la prueba. En la 2 no hay FiltroDeApertura, y ForSampling construye las
# columnas asi, en el 100 % de las lineas:
#     DEBE = DEBESA + max(APERTURA, 0)      HABER = HABERSA + max(-APERTURA, 0)
# es decir, DEBE y HABER SI llevan la apertura, y APERTURA es su importe neto con signo.
PLANTILLAS = {
    "0": "DEBE y HABER",
    "1": "SALDO",
    "2": "campo de APERTURA",
}
PLANTILLA_CAMPO_APERTURA = "2"

# Las columnas del diario que la prueba usa. Ni CONCEPTO ni ninguna otra.
COLUMNAS_APERTURA = ("FECHA", "ASIENTO", "CUENTA", "NOMBRE", "DEBE", "HABER")


def salida_utf8() -> None:
    """La consola de Windows no es UTF-8 por defecto y parte los acentos."""
    for flujo in ("stdout", "stderr"):
        f = getattr(sys, flujo)
        if hasattr(f, "reconfigure"):
            f.reconfigure(encoding="utf-8")


def _no_se_traduce(crudo: str, motivo: str) -> dict:
    return {"ausente": True, "motivo": motivo + ". Se para en vez de adivinar.", "crudo": crudo}


def interpretar_filtro(crudo: str) -> dict:
    """Traduce el texto del FiltroDeApertura.

    El asiento de apertura se fija al normalizar el diario y NO tiene que ser el
    numero 1: en el expediente de calibracion era el 3495. El filtro tiene esta forma:

        CAMPO|Tipo|Operador|Valor1|Valor2|Comparacion| descripcion legible

    Medido en expedientes reales:  CONCEPTO|Texto|Es igual a|Apertura|||...
                                   CONCEPTO|Texto|Comienza por|Apertura|||...
    El ejemplo de partida era por ASIENTO, asi que el campo, el operador y el
    valor son todos variables y hay que leerlos, no suponerlos.

    Comparacion (Y/O) encadena con la fila siguiente: un filtro de varias
    condiciones no se traduce, y leer_filtro ya para si hay mas de una fila.

    Devuelve {campo, tipo, operador, valor, crudo}, o {ausente: True, motivo}.
    """
    partes = str(crudo or "").split("|")
    if len(partes) < 4:
        return {"ausente": True, "motivo": "filtro ilegible: " + repr(crudo)}
    original = partes[2].strip()
    operador = original.lower()
    if operador not in OPERADORES:
        if operador in NO_SOPORTADOS:
            return _no_se_traduce(crudo, "operador " + repr(original) + " no soportado: "
                                  + NO_SOPORTADOS[operador])
        if operador in COMPARADORES:
            return _no_se_traduce(crudo, "operador " + repr(original) + " no soportado: es un "
                                  "comparador, y aqui el campo se compara como texto")
        return _no_se_traduce(crudo, "operador no soportado: " + repr(partes[2])
                              + ". Los conocidos son " + str(sorted(OPERADORES)))
    tipo = partes[1].strip()
    if tipo.lower() == "fecha":
        return _no_se_traduce(crudo, "filtro sobre un campo de tipo Fecha, y aqui el campo se "
                              "compara como texto")
    valor = partes[3].strip()
    if valor.lower() == VALOR_NULO:
        return _no_se_traduce(crudo, "filtro por campo vacio (" + VALOR_NULO + ")")
    if len(partes) > 5 and partes[5].strip():
        return _no_se_traduce(crudo, "el filtro encadena otra condicion (Comparacion = "
                              + repr(partes[5].strip()) + ") y solo se traduce una")
    campo = partes[0].strip()
    # el campo va a parar a una consulta: solo un nombre de columna, nada mas
    if not campo.replace("_", "").isalnum():
        return {"ausente": True, "motivo": "campo de filtro raro: " + repr(campo), "crudo": crudo}
    return {
        "campo": campo,
        "tipo": tipo,
        "operador": operador,
        "valor": valor,
        "crudo": crudo,
    }


def _sin_filtro(plantilla) -> dict:
    """Sin FiltroDeApertura ni plantilla del campo de apertura: no hay forma de saber cual es
    el asiento de apertura, y se dice como se arregla. 130 de los 248 diarios medidos el
    25/11/2026 estan asi: normalizados con DEBE y HABER y sin filtro."""
    if plantilla is None:
        motivo = "CfgNormalizacion no tiene FiltroDeApertura"
    elif plantilla in PLANTILLAS:
        motivo = ("el diario se normalizo con la plantilla de " + PLANTILLAS[plantilla]
                  + " y sin filtro de apertura")
    else:
        motivo = ("el diario se normalizo con una plantilla desconocida (" + repr(plantilla)
                  + ") y sin filtro de apertura")
    return {"ausente": True, "plantilla": plantilla,
            "motivo": motivo + ". La apertura se define al normalizar el diario: con un filtro "
                      "de apertura, o con la plantilla que trae el campo APERTURA. Hay que "
                      "definirla y volver a importar el diario"}


def leer_filtro(ruta) -> dict:
    """Lee como se identifica la apertura, del fichero que deja exportar_consulta con SQL_FILTRO.

    Devuelve el filtro traducido (via «filtro»), la identificacion por el campo APERTURA
    (via «campo») si no hay filtro y la plantilla es la que trae ese campo, o {ausente,
    motivo}. Si hay filtro manda el filtro, sea cual sea la plantilla: es lo que el auditor
    definio expresamente, y C06 lo cruza con el campo APERTURA."""
    try:
        filas = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"ausente": True, "motivo": "no se puede leer el filtro exportado: " + str(exc)}
    if not isinstance(filas, list):
        return {"ausente": True, "motivo": "el fichero del filtro no es una lista de filas"}
    datos = []
    for fila in filas:
        clave = next((k for k in fila if str(k).lower() == "datos"), None) if isinstance(fila, dict) else None
        if clave is None:
            return {"ausente": True, "motivo": "la fila del filtro no trae la columna Datos"}
        datos.append(str(fila[clave] if fila[clave] is not None else "").strip())
    # la plantilla es un numero y el FiltroDeApertura va con barras (CAMPO|Tipo|...). Lo que
    # no es ninguna de las dos es una configuracion de otro formato: un .smn antiguo guarda
    # en «Configuracion de campos» la lista de campos (medido el 25/11/2026, uno de 391)
    plantillas = sorted({d for d in datos if d.isdigit()})
    filtros = [d for d in datos if "|" in d]
    otras = [d for d in datos if not d.isdigit() and "|" not in d]
    plantilla = plantillas[0] if len(plantillas) == 1 else None
    if len(filtros) > 1:
        return {"ausente": True, "plantilla": plantilla,
                "motivo": "hay " + str(len(filtros)) + " FiltroDeApertura: es un filtro de "
                          "varias condiciones encadenadas con Y/O, y solo se traduce una. "
                          "Se para en vez de adivinar."}
    if filtros:
        filtro = interpretar_filtro(filtros[0])
        filtro["plantilla"] = plantilla
        if not filtro.get("ausente"):
            filtro["via"] = "filtro"
        return filtro
    if len(plantillas) > 1:
        # en un .smn conviven normalizaciones de varios tipos (diario, bancos...) y la consulta
        # no las separa: 0 de 248 diarios medidos trae dos, pero si llega no se elige una
        return {"ausente": True, "plantilla": None,
                "motivo": "la configuracion trae " + str(len(plantillas)) + " plantillas de "
                          "normalizacion (" + ", ".join(plantillas) + ") y ningun filtro de "
                          "apertura: no se sabe cual es la del diario. Se para en vez de adivinar."}
    if plantilla == PLANTILLA_CAMPO_APERTURA:
        return {"via": "campo", "campo": "APERTURA", "plantilla": plantilla,
                "crudo": "APERTURA <> 0 (plantilla con campo de apertura, sin FiltroDeApertura)"}
    if plantilla is None and otras:
        return _sin_filtro(otras[0][:60])
    return _sin_filtro(plantilla)


def describir_apertura(filtro: dict) -> str:
    """Como se ha identificado la apertura, en una linea legible para la pantalla y el papel."""
    if filtro.get("via") == "campo":
        return ("campo APERTURA distinto de cero (el diario se normalizo con la plantilla "
                "del campo de apertura, sin filtro)")
    return "filtro " + filtro["campo"] + " " + filtro["operador"] + " " + repr(filtro["valor"])


def condicion_jet(filtro: dict) -> str:
    """El filtro como condicion de JET, con la misma semantica que aplicar_filtro():
    texto sin espacios a los lados y sin distinguir mayusculas; un nulo es texto vacio.

    Salvo en los negativos («Es distinto a», «No contiene»): ahi un nulo queda FUERA,
    como en Gesia, que pasa el filtro a JET sin IIf, y alli NULL <> 'x' no es verdadero.
    Como texto vacio entraria en la apertura todo apunte que no tenga ese campo."""
    campo = "[" + filtro["campo"] + "]"
    col = "LCase(Trim(IIf(IsNull(" + campo + "), '', " + campo + ")))"
    valor = filtro["valor"].lower().replace("'", "''")
    op = OPERADORES[filtro["operador"]]
    if op == "==":
        return col + " = '" + valor + "'"
    if op == "!=":
        return "(" + campo + " IS NOT NULL AND " + col + " <> '" + valor + "')"
    # en LIKE, % y _ son comodines: el valor se escapa entre corchetes
    lit = valor.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]")
    if op == "no_contiene":
        return "(" + campo + " IS NOT NULL AND " + col + " NOT LIKE '%" + lit + "%')"
    patron = {"contiene": "%" + lit + "%", "empieza": lit + "%", "termina": "%" + lit}[op]
    return col + " LIKE '" + patron + "'"


def sql_apertura(filtro: dict, con_campo_apertura: bool = True) -> str:
    """La consulta del asiento de apertura: lo que el filtro selecciona y, si el diario
    trae el campo APERTURA, tambien lo que ese campo marca, para la comprobacion C06.

    Por el campo (plantilla del campo de apertura, sin filtro) son las lineas con
    APERTURA <> 0, todas con POR_FILTRO = 1. Sin la columna no hay apertura que leer."""
    cols = ", ".join(COLUMNAS_APERTURA)
    if filtro.get("via") == "campo":
        if not con_campo_apertura:
            raise RuntimeError(
                "el diario se normalizo con la plantilla del campo de apertura y no trae la "
                "columna APERTURA: no hay de donde leer la apertura")
        return "SELECT " + cols + ", APERTURA, 1 AS POR_FILTRO FROM Diario WHERE APERTURA <> 0"
    cond = condicion_jet(filtro)
    if con_campo_apertura:
        return ("SELECT " + cols + ", APERTURA, IIf(" + cond + ", 1, 0) AS POR_FILTRO "
                "FROM Diario WHERE (" + cond + ") OR (APERTURA <> 0)")
    return "SELECT " + cols + ", 1 AS POR_FILTRO FROM Diario WHERE " + cond


def _numerica(serie: pd.Series) -> pd.Series:
    return (pd.to_numeric(serie.astype(str).str.replace(",", ".", regex=False), errors="coerce")
            .fillna(0.0).round(DECIMALES))


def cargar_apertura(ruta) -> pd.DataFrame:
    """Trae el asiento de apertura exportado, con los importes numericos y POR_FILTRO
    como booleano. Las columnas se normalizan a mayusculas."""
    filas = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not isinstance(filas, list):
        raise RuntimeError("el fichero de apertura no es una lista de filas")
    df = pd.DataFrame(filas)
    df.columns = [str(c).upper() for c in df.columns]
    for col in ("DEBE", "HABER", "APERTURA"):
        if col in df.columns:
            df[col] = _numerica(df[col])
    if "POR_FILTRO" in df.columns:
        df["POR_FILTRO"] = _numerica(df["POR_FILTRO"]) != 0
    for col in ("CUENTA", "ASIENTO", "NOMBRE"):
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
    # el ASIENTO llega numerico desde ODBC: 3495.0 se escribe 3495
    if "ASIENTO" in df.columns:
        df["ASIENTO"] = df["ASIENTO"].str.replace(r"\.0$", "", regex=True)
    return df


def aplicar_filtro(df: pd.DataFrame, filtro: dict) -> pd.Series:
    """El filtro sobre un diario completo en pandas. Ya no lo usa la prueba -lo evalua JET
    al exportar-: lo usa el arnes para comprobar que condicion_jet() selecciona lo mismo."""
    campo = filtro["campo"]
    if campo not in df.columns:
        raise RuntimeError(
            "el filtro de apertura usa el campo " + repr(campo) + ", que no existe "
            "en el diario. Columnas: " + str(sorted(df.columns))
        )
    nulo = df[campo].isna()
    col = df[campo].fillna("").astype(str).str.strip().str.lower()
    valor = filtro["valor"].lower()
    op = OPERADORES[filtro["operador"]]
    if op == "==":
        return col == valor
    if op == "!=":
        return ~nulo & (col != valor)
    if op == "contiene":
        return col.str.contains(valor, regex=False)
    if op == "no_contiene":
        return ~nulo & ~col.str.contains(valor, regex=False)
    if op == "empieza":
        return col.str.startswith(valor)
    return col.str.endswith(valor)


def saldos_apertura(df: pd.DataFrame, mascara: pd.Series) -> pd.DataFrame:
    """Saldo de apertura por cuenta del cliente, al maximo desglose del diario.

    El saldo es DEBE - HABER, no el campo APERTURA: APERTURA es una opcion de
    importacion y puede venir vacia, mientras que DEBE y HABER estan siempre. Con la
    plantilla del campo de apertura tambien: ForSampling mete la apertura en DEBE y
    HABER (medido el 25/11/2026), y verificar_contrato (C06) para si no coinciden.
    """
    ap = df[mascara].copy()
    ap["SALDO_AP"] = (ap["DEBE"] - ap["HABER"]).round(DECIMALES)
    agr = ap.groupby("CUENTA", as_index=False)["SALDO_AP"].sum()
    agr["SALDO_AP"] = agr["SALDO_AP"].round(DECIMALES)
    return agr


def mapear_a_maximo_nivel(cuentas: list, nivel: set) -> dict:
    """Asigna cada cuenta del diario a su cuenta de maximo nivel del expediente.

    Regla fijada en cliente: el prefijo mas largo que exista como
    cuenta de maximo nivel. Hace falta porque el maximo nivel NO es un numero
    fijo de digitos: en el expediente de calibracion hay 204 cuentas de maximo nivel
    a 3 digitos
    y 234 a 4, segun la rama del plan contable. Truncar el diario a N digitos
    daria mal el resultado en una de las dos.

    Devuelve {cuenta_diario: cuenta_maximo_nivel o None}. El None no es un error
    del skill: es una cuenta abierta que el expediente no reconoce, y se informa.
    """
    mapa = {}
    for cta in cuentas:
        destino = None
        for corte in range(len(cta), 0, -1):
            if cta[:corte] in nivel:
                destino = cta[:corte]
                break
        mapa[cta] = destino
    return mapa


def _num_es(v) -> float:
    """Los saldos del expediente llegan como texto con coma decimal."""
    return round(float(str(v).replace(",", ".").strip() or 0), DECIMALES)


def leer_cierre(ruta, ejercicio: str = "", anterior: str = "",
                cliente: str = "") -> dict:
    """Lee el cierre auditado, en cualquiera de las dos formas que puede venir.

    1. Lista cruda de filas, tal como la deja `exportar_consulta` del MCP:
       [{"Cuenta": "100", "Nombre": "...", "SaldoAuditoria": "-12149313,0000"}]
       Es la forma preferida: el dato va del expediente al fichero sin pasar por
       el contexto del modelo. Los metadatos -ejercicios y cliente- se pasan como
       argumento, porque la consulta no los trae.

    2. Objeto con metadatos, que es como se escribia a mano antes de que el MCP
       supiera exportar. Se mantiene para no romper lo que ya funciona.
    """
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))

    if isinstance(datos, list):
        if not datos:
            raise RuntimeError("el fichero de cierre no trae ninguna fila")
        faltan = [c for c in ("Cuenta", "SaldoAuditoria") if c not in datos[0]]
        if faltan:
            raise RuntimeError(
                "a las filas del cierre les faltan columnas: " + str(faltan)
                + ". La consulta tiene que pedir Cuenta, Nombre y SaldoAuditoria."
            )
        if not ejercicio or not anterior:
            raise RuntimeError(
                "con un fichero de filas crudas hay que indicar el ejercicio y el "
                "anterior: la consulta no los trae."
            )
        return {
            "cliente": cliente,
            "ejercicio": str(ejercicio),
            "ejercicio_anterior": str(anterior),
            "cuentas": [
                {"cuenta": str(f["Cuenta"]).strip(),
                 "nombre": str(f.get("Nombre") or "").strip(),
                 "saldo": _num_es(f["SaldoAuditoria"])}
                for f in datos
            ],
        }

    for clave in ("ejercicio", "ejercicio_anterior", "cuentas"):
        if clave not in datos:
            raise RuntimeError("el JSON de cierre no trae " + repr(clave))
    if not datos["cuentas"]:
        raise RuntimeError("el JSON de cierre no trae ninguna cuenta")
    for c in datos["cuentas"]:
        c["cuenta"] = str(c["cuenta"]).strip()
        c["nombre"] = str(c.get("nombre", "")).strip()
        c["saldo"] = round(float(c["saldo"]), DECIMALES)
    return datos
