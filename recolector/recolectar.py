#!/usr/bin/env python3
"""Recolector de datos del explorador de revistas de sociología.

1. Obtiene de DOAJ las revistas de sociología publicadas en español.
2. Para cada revista, pide a Crossref sus tres últimos números por ISSN.
3. Si Crossref no tiene datos o están desfasados, prueba OAI-PMH (OJS).
4. Escribe data/revistas.json, un archivo por revista en data/revistas/
   y un informe con las revistas que no se han podido resolver.

No se inventa ningún dato: si una fuente falla, la revista va al informe.
Los datos se preparan en una carpeta temporal y solo sustituyen a los
anteriores si la recolección termina bien.

Uso: python3 recolector/recolectar.py [--limite 50] [--salida data]
"""

import argparse
import datetime
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import crossref  # noqa: E402
import doaj  # noqa: E402
import oai  # noqa: E402
from comun import VERSION_DATOS, ErrorRed, escribir_datos, sin_tildes  # noqa: E402

ANIOS_DESFASE = 2


def ahora():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def anio_reciente(numeros):
    return max((n.get("anio") or 0 for n in numeros), default=0)


def resolver(revista, informe):
    """Devuelve los números de una revista o None si no se ha podido resolver."""
    issns = [revista["issn_electronico"], revista["issn_impreso"]]
    motivos, numeros = [], []
    try:
        numeros = crossref.ultimos_numeros(issns)
        if not numeros:
            motivos.append("Crossref no tiene artículos con estos ISSN.")
    except ErrorRed as error:
        motivos.append(f"Error al consultar Crossref: {error}")

    limite = datetime.date.today().year - ANIOS_DESFASE
    if not numeros or anio_reciente(numeros) < limite:
        if numeros:
            motivos.append(f"Los datos de Crossref terminan en {anio_reciente(numeros)}; se prueba OAI-PMH.")
        try:
            punto, numeros_oai = oai.ultimos_numeros(revista.get("url"))
            if not punto:
                motivos.append("No se ha encontrado un punto OAI-PMH en la web de la revista.")
            elif not numeros_oai:
                motivos.append(f"El punto OAI-PMH {punto} no devuelve números identificables.")
            elif anio_reciente(numeros_oai) > anio_reciente(numeros):
                numeros = numeros_oai
                revista["oai"] = punto
        except (ErrorRed, ValueError) as error:
            motivos.append(f"Error al consultar OAI-PMH: {error}")

    if not numeros:
        informe.append({"id": revista["id"], "titulo": revista["titulo"], "url": revista.get("url"),
                        "issn": [i for i in issns if i], "motivos": motivos})
        return None
    return numeros


def escribir_informe(carpeta, informe, fecha):
    escribir_datos(carpeta, "informe-no-resueltas.json", {
        "version": VERSION_DATOS, "generado": fecha, "total": len(informe), "revistas": informe})
    lineas = ["# Revistas no resueltas", "",
              f"Generado el {fecha}. Revistas que aparecen en DOAJ pero de las que no se han",
              "podido obtener números ni artículos. No se muestran en la aplicación.", ""]
    if not informe:
        lineas.append("Todas las revistas se han resuelto correctamente.")
    for item in informe:
        lineas += [f"## {item['titulo']}", "", f"Identificador: {item['id']}. ISSN: {', '.join(item['issn'])}.",
                   f"Web: {item['url'] or 'no indicada en DOAJ'}.", ""]
        lineas += [f"{n}. {m}" for n, m in enumerate(item["motivos"], 1)] + [""]
    with open(os.path.join(carpeta, "informe-no-resueltas.md"), "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas))


def recolectar(limite, carpeta_final):
    fecha = ahora()
    print(f"Consultando DOAJ (límite {limite or 'sin límite'})…", flush=True)
    revistas = doaj.buscar_revistas(limite)
    print(f"DOAJ devuelve {len(revistas)} revistas.", flush=True)
    if not revistas:
        raise SystemExit("DOAJ no ha devuelto ninguna revista. No se modifican los datos actuales.")

    temporal = tempfile.mkdtemp(prefix="recoleccion-")
    resueltas, informe = [], []
    for posicion, revista in enumerate(revistas, 1):
        print(f"[{posicion}/{len(revistas)}] {revista['titulo']}", flush=True)
        numeros = resolver(revista, informe)
        if not numeros:
            continue
        archivo = f"revistas/{revista['id']}.json"
        revista["archivo"] = archivo
        revista["ultimo_numero"] = numeros[0]["etiqueta"]
        revista["fuente_numeros"] = numeros[0]["fuente"]
        escribir_datos(temporal, archivo, {
            "version": VERSION_DATOS, "generado": fecha, "es_prueba": False,
            "revista": revista, "numeros": numeros})
        resueltas.append(revista)

    if not resueltas:
        shutil.rmtree(temporal)
        raise SystemExit("No se ha resuelto ninguna revista. No se modifican los datos actuales.")

    resueltas.sort(key=lambda r: sin_tildes(r["titulo"]))
    escribir_datos(temporal, "revistas.json", {
        "version": VERSION_DATOS, "generado": fecha, "es_prueba": False,
        "fuentes": ["DOAJ", "Crossref", "OAI-PMH"], "idiomas_incluidos": ["es"],
        "total": len(resueltas), "revistas": resueltas})
    escribir_informe(temporal, informe, fecha)

    # Sustitución de los datos anteriores solo cuando todo ha ido bien.
    if os.path.isdir(carpeta_final):
        shutil.rmtree(carpeta_final)
    shutil.move(temporal, carpeta_final)
    print(f"Listo: {len(resueltas)} revistas resueltas, {len(informe)} en el informe.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limite", type=int, default=50, help="número máximo de revistas (0 sin límite)")
    parser.add_argument("--salida", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    argumentos = parser.parse_args()
    try:
        recolectar(argumentos.limite or None, os.path.abspath(argumentos.salida))
    except ErrorRed as error:
        raise SystemExit(f"No se ha podido completar la recolección: {error}") from error


if __name__ == "__main__":
    main()
