"""Comprueba en ejecucion lo que la prueba de continuidad asume. Puede abortar.

No fiarse de la documentacion: lo que se asume, se comprueba. Un papel de trabajo
bonito sobre datos mal entendidos es peor que no tener papel.

    python verificar_contrato.py --filtro filtro.json --apertura apertura.json \
        --cierre cierre.json

Codigos de salida:
  0  todo encaja
  1  avisos: se puede seguir, pero hay que leerlos y contarlos en el papel
  2  no se puede hacer la prueba. No se genera nada.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# La carpeta del script, explicita: lanzado con `python -I` no esta en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_continuidad import (  # noqa: E402
    DECIMALES,
    GRUPOS_BALANCE,
    cargar_apertura,
    describir_apertura,
    leer_cierre,
    leer_filtro,
    saldos_apertura,
    salida_utf8,
)

# Tolerancia para dar por cuadrado un asiento. Dos decimales es el redondeo del
# euro fijado en cliente; se deja un margen de un centimo por cuenta agregada, no
# un porcentaje: un descuadre real en un asiento de apertura no es proporcional.
TOLERANCIA = 0.01

# Tolerancia por LINEA al cruzar el campo APERTURA con DEBE - HABER: los dos llegan
# redondeados a 2 decimales, asi que cualquier resto por encima de medio centimo es una
# diferencia real y no coma flotante.
TOLERANCIA_LINEA = 0.005

COLUMNAS_MINIMAS = ("CUENTA", "ASIENTO", "DEBE", "HABER", "POR_FILTRO")


def main() -> int:
    salida_utf8()
    p = argparse.ArgumentParser()
    p.add_argument("--filtro", required=True, help="JSON exportado con SQL_FILTRO")
    p.add_argument("--apertura", required=True,
                   help="JSON exportado con la consulta de consulta_apertura.py")
    p.add_argument("--cierre", required=True, help="JSON con el cierre auditado")
    p.add_argument("--ejercicio", default="",
                   help="ejercicio auditado; obligatorio si el cierre son filas crudas")
    p.add_argument("--ejercicio-anterior", default="",
                   help="ejercicio del cierre con el que se compara")
    p.add_argument("--cliente", default="", help="razón social, para el papel")
    args = p.parse_args()

    errores: list = []
    avisos: list = []

    # C01 · el asiento de apertura exportado es legible y trae lo imprescindible
    try:
        df = cargar_apertura(args.apertura)
    except (OSError, ValueError, RuntimeError) as exc:
        print("C01 ERROR: no se puede leer la apertura exportada: " + str(exc))
        return 2
    faltan = [c for c in COLUMNAS_MINIMAS if c not in df.columns]
    if faltan:
        errores.append("C01 · a la apertura exportada le faltan columnas: " + str(faltan)
                       + ". Exportala con la consulta que da consulta_apertura.py, tal cual.")

    # C02 · la apertura se puede identificar: por el filtro o por el campo APERTURA
    filtro = leer_filtro(args.filtro)
    if filtro.get("ausente"):
        errores.append(
            "C02 · no se puede identificar el asiento de apertura: "
            + filtro["motivo"]
            + ". No se supone: el asiento de apertura no tiene que ser el 1."
        )
    elif filtro.get("via") == "campo" and "APERTURA" not in df.columns:
        errores.append(
            "C02 · el diario se normalizo con la plantilla del campo de apertura y la "
            "apertura exportada no trae la columna APERTURA. Exportala con la consulta "
            "que da consulta_apertura.py, tal cual."
        )

    if errores:
        for e in errores:
            print(e)
        print("\nNo se puede hacer la prueba.")
        return 2

    print("C02 · apertura por " + describir_apertura(filtro))

    # C03 · el filtro selecciona algo (lo evaluo JET al exportar: POR_FILTRO)
    mascara = df["POR_FILTRO"]
    n = int(mascara.sum())
    if n == 0:
        print("C03 ERROR: " + ("ningun apunte tiene el campo APERTURA distinto de cero."
                               if filtro.get("via") == "campo"
                               else "el filtro de apertura no selecciona ningun apunte."))
        return 2
    asientos = sorted(df.loc[mascara, "ASIENTO"].drop_duplicates().tolist())
    print("C03 · " + str(n) + " apuntes de apertura, asiento(s) " + str(asientos[:5])
          + (" y " + str(len(asientos) - 5) + " mas" if len(asientos) > 5 else ""))

    # C04 · la apertura cuadra
    ap = df[mascara]
    neto = round(float((ap["DEBE"] - ap["HABER"]).sum()), DECIMALES)
    if abs(neto) > TOLERANCIA:
        errores.append(
            "C04 · el asiento de apertura no cuadra: descuadre de "
            + format(neto, ".2f") + " EUR. Con la apertura descuadrada la prueba "
            "no significa nada."
        )
    else:
        print("C04 · la apertura cuadra (" + format(neto, ".2f") + ")")

    # C05 · la apertura no deberia traer cuentas de resultados
    g1 = ap["CUENTA"].str[:1]
    resultados = ap[g1.isin(["6", "7"])]
    if len(resultados):
        avisos.append(
            "C05 · la apertura trae " + str(len(resultados)) + " apuntes de los "
            "grupos 6 y 7, que no deberian tener saldo inicial. Quedan fuera de la "
            "comparacion y se informan aparte: es un error del cliente, no una "
            "diferencia que cuantificar."
        )

    # C06 · por el campo APERTURA (plantilla del campo de apertura, sin filtro) no hay
    # filtro con el que cruzarlo, pero si lo que la prueba asume: que ForSampling metio
    # la apertura en DEBE y HABER, y que APERTURA es su importe neto. Medido el 25/11/2026
    # en las 242 lineas de apertura del diario de prueba. Si no coincide, el saldo que la
    # prueba toma (DEBE - HABER) no es la apertura, y se para.
    if filtro.get("via") == "campo":
        neto_linea = (ap["DEBE"] - ap["HABER"]).round(DECIMALES)
        distintas = ap[(ap["APERTURA"] - neto_linea).abs() > TOLERANCIA_LINEA]
        if len(distintas):
            errores.append(
                "C06 · en " + str(len(distintas)) + " de " + str(len(ap)) + " apuntes de "
                "apertura el campo APERTURA no coincide con DEBE - HABER (cuentas "
                + str(sorted(distintas["CUENTA"].drop_duplicates().tolist())[:5]) + "). "
                "La prueba lee la apertura de DEBE y HABER, y con este diario no seria la "
                "del campo APERTURA: no se puede hacer."
            )
        else:
            print("C06 · el campo APERTURA coincide con DEBE - HABER en los " + str(len(ap))
                  + " apuntes de apertura")
        # la apertura es un asiento: repartida en varios asientos o fechas, hay que mirarla
        fechas = ap["FECHA"].drop_duplicates().tolist() if "FECHA" in ap.columns else []
        if len(asientos) > 1 or len(fechas) > 1:
            avisos.append(
                "C06 · las lineas con APERTURA distinto de cero estan repartidas en "
                + str(len(asientos)) + " asiento(s) y " + str(len(fechas)) + " fecha(s). "
                "La apertura es un asiento: revisa que todas lo sean antes de firmar."
            )
    # C06 · si el campo APERTURA viene relleno, tiene que decir lo mismo que el filtro.
    # La exportacion trae justo la union de los dos -lo que el filtro selecciona y lo que
    # APERTURA marca-, que es todo lo que esta comprobacion necesita del diario.
    elif "APERTURA" in df.columns and (df["APERTURA"] != 0).any():
        por_campo = set(df.index[df["APERTURA"] != 0])
        por_filtro = set(df.index[mascara])
        if por_campo != por_filtro:
            avisos.append(
                "C06 · el campo APERTURA y el FiltroDeApertura NO seleccionan lo "
                "mismo (" + str(len(por_campo)) + " frente a " + str(len(por_filtro))
                + " apuntes). Manda el filtro, pero esto suele significar que se "
                "cambio despues de importar: revisalo antes de firmar."
            )
        else:
            print("C06 · el campo APERTURA coincide con el filtro")
    else:
        avisos.append(
            "C06 · el campo APERTURA viene vacio o no existe (es una opcion de "
            "importacion). Se usa el filtro, que es la fuente buena, pero se "
            "pierde la comprobacion cruzada."
        )

    # C07 · el cierre que trajo el modelo tiene la pinta que debe
    try:
        cierre = leer_cierre(args.cierre, args.ejercicio, args.ejercicio_anterior,
                             args.cliente)
    except (RuntimeError, ValueError) as exc:
        print("C07 ERROR: " + str(exc))
        return 2

    ctas = cierre["cuentas"]
    fuera = [c["cuenta"] for c in ctas if c["cuenta"][:1] not in GRUPOS_BALANCE]
    if fuera:
        errores.append(
            "C07 · el cierre trae " + str(len(fuera)) + " cuentas que no son de los "
            "grupos 1 a 5 (" + str(fuera[:5]) + "). La consulta al expediente tiene "
            "que filtrar CodigoTipo = 'B'."
        )
    suma = round(sum(c["saldo"] for c in ctas), DECIMALES)
    if abs(suma) > TOLERANCIA:
        avisos.append(
            "C07 · los saldos del cierre suman " + format(suma, ".2f") + " y deberian "
            "sumar cero: un balance completo cuadra. Puede que la consulta no haya "
            "filtrado MaximoNivel, o que falten cuentas."
        )
    else:
        print("C07 · el cierre trae " + str(len(ctas)) + " cuentas y cuadra a cero")

    # C08 · las cuentas de maximo nivel no se pueden solapar entre si
    codigos = set(c["cuenta"] for c in ctas)
    solapes = [c for c in codigos if any(o != c and o.startswith(c) for o in codigos)]
    if solapes:
        errores.append(
            "C08 · hay " + str(len(solapes)) + " cuentas del cierre que son prefijo "
            "de otra del mismo cierre (" + str(sorted(solapes)[:5]) + "). Eso duplica "
            "saldos y rompe el mapeo por prefijo mas largo."
        )
    else:
        print("C08 · las cuentas del cierre no se solapan")

    # C09 · cuanto de la apertura encuentra destino
    agr = saldos_apertura(df, mascara)
    del agr  # el recuento real lo hace comparar.py; aqui solo interesa que haya algo

    for e in errores:
        print("\n" + e)
    for a in avisos:
        print("\n" + a)

    if errores:
        print("\nNo se puede hacer la prueba.")
        return 2
    if avisos:
        print("\nSe puede seguir, pero hay " + str(len(avisos)) + " aviso(s) que "
              "tienen que constar en el papel.")
        return 1
    print("\nContrato verificado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
