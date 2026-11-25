"""Da la consulta con la que el MCP exporta el asiento de apertura. Puede abortar.

    python consulta_apertura.py --filtro filtro.json [--sin-campo-apertura]

Lee lo que se exporto con la consulta de SQL_FILTRO -el FiltroDeApertura y la plantilla
con que se normalizo el diario- y escribe en pantalla, en una linea que empieza por SQL:,
la consulta que hay que pasar tal cual a exportar_consulta(fuente="diario"). La consulta
trae solo las columnas que la prueba usa y el filtro ya evaluado en JET (POR_FILTRO): el
diario no sale entero del equipo. Sin filtro y con la plantilla del campo de apertura, la
apertura son las lineas con APERTURA <> 0.

--sin-campo-apertura cuando columnas(fuente="diario", tabla="Diario") no lista APERTURA,
que es una opcion de importacion: sin el, la consulta fallaria por un campo inexistente.
Con la plantilla del campo de apertura y sin esa columna no hay apertura: para.

Codigos de salida:
  0  la consulta esta en pantalla
  2  la apertura no se puede identificar: no se puede hacer la prueba
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# La carpeta del script, explicita: lanzado con `python -I` no esta en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_continuidad import (  # noqa: E402
    SQL_FILTRO,
    describir_apertura,
    leer_filtro,
    salida_utf8,
    sql_apertura,
)


def main() -> int:
    salida_utf8()
    p = argparse.ArgumentParser()
    p.add_argument("--filtro", required=True, help="el JSON exportado con SQL_FILTRO")
    p.add_argument("--sin-campo-apertura", action="store_true",
                   help="el Diario no trae la columna APERTURA")
    args = p.parse_args()

    filtro = leer_filtro(args.filtro)
    if filtro.get("ausente"):
        print("C02 ERROR: no se puede identificar el asiento de apertura: " + filtro["motivo"]
              + ". No se supone: el asiento de apertura no tiene que ser el 1.")
        print("  (el filtro se exporta con: " + SQL_FILTRO + ")")
        return 2
    try:
        sql = sql_apertura(filtro, not args.sin_campo_apertura)
    except RuntimeError as exc:
        print("C02 ERROR: no se puede identificar el asiento de apertura: " + str(exc) + ".")
        return 2
    print("C02 · apertura por " + describir_apertura(filtro))
    print("SQL: " + sql)
    return 0


if __name__ == "__main__":
    sys.exit(main())
