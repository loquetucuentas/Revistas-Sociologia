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
import urllib.parse

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


def dominio_de(url):
    return urllib.parse.urlsplit(url).netloc.lower() if url else None


def resolver(revista, informe, avisos):
    """Devuelve los números de una revista o None si no se ha podido resolver.

    Las revistas sin números van a informe (pendientes de revisión). Las que
    se cargan con datos de Crossref posiblemente desfasados van a avisos.
    """
    issns = [revista["issn_electronico"], revista["issn_impreso"]]
    motivos, numeros, bloqueado = [], [], None
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
        except ErrorRed as error:
            if error.bloqueado:
                bloqueado = error.dominio
                motivos.append(f"No se ha podido probar OAI-PMH porque la red del entorno no permite el "
                               f"dominio {error.dominio}. Mensaje: {error}")
            else:
                motivos.append(f"Error al consultar OAI-PMH: {error}")
        except ValueError as error:
            motivos.append(f"Error al consultar OAI-PMH: {error}")

    entrada = {"id": revista["id"], "titulo": revista["titulo"], "url": revista.get("url"),
               "dominio": dominio_de(revista.get("url")), "dominio_bloqueado": bloqueado,
               "issn": [i for i in issns if i], "motivos": motivos}
    if not numeros:
        informe.append(entrada)
        return None
    if anio_reciente(numeros) < limite:
        avisos.append(entrada)
    return numeros


def escribir_informe(carpeta, informe, avisos, fecha):
    escribir_datos(carpeta, "informe-no-resueltas.json", {
        "version": VERSION_DATOS, "generado": fecha, "total": len(informe), "revistas": informe,
        "total_avisos": len(avisos), "avisos": avisos})
    lineas = ["# Revistas pendientes de revisión", "",
              f"Generado el {fecha}. Revistas que aparecen en DOAJ pero de las que no se han",
              "podido obtener números ni artículos. No se muestran en la aplicación.", ""]
    bloqueados = sorted({i["dominio_bloqueado"] for i in informe + avisos if i["dominio_bloqueado"]})
    if bloqueados:
        lineas += ["Dominios que la red del entorno no permite y que habría que añadir para probar",
                   "OAI-PMH: " + ", ".join(bloqueados) + ".", ""]
    if not informe:
        lineas.append("Todas las revistas se han resuelto correctamente.")
        lineas.append("")
    for item in informe:
        lineas += [f"## {item['titulo']}", "", f"Identificador: {item['id']}. ISSN: {', '.join(item['issn'])}.",
                   f"Web: {item['url'] or 'no indicada en DOAJ'}. Dominio: {item['dominio'] or 'desconocido'}.", ""]
        lineas += [f"{n}. {m}" for n, m in enumerate(item["motivos"], 1)] + [""]
    if avisos:
        lineas += ["# Revistas cargadas con datos posiblemente desfasados", "",
                   "Se muestran en la aplicación con sus últimos números en Crossref, pero esos",
                   "números son antiguos y no se ha podido comprobar si hay otros más recientes.", ""]
        for item in avisos:
            lineas += [f"## {item['titulo']}", "", f"Identificador: {item['id']}. Dominio: {item['dominio'] or 'desconocido'}.", ""]
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
    resueltas, informe, avisos = [], [], []
    for posicion, revista in enumerate(revistas, 1):
        print(f"[{posicion}/{len(revistas)}] {revista['titulo']}", flush=True)
        numeros = resolver(revista, informe, avisos)
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
    escribir_informe(temporal, informe, avisos, fecha)

    # Los textos completos se recogen aparte (texto_completo.py): se conservan
    # y se vuelven a enlazar desde los artículos que siguen en los datos.
    textos_anteriores = os.path.join(carpeta_final, "textos")
    if os.path.isdir(textos_anteriores):
        shutil.copytree(textos_anteriores, os.path.join(temporal, "textos"))
        import texto_completo  # noqa: E402
        indice = texto_completo.leer_json(os.path.join(temporal, "textos", "indice.json"), {})
        texto_completo.aplicar_indice(temporal, indice)
    for informe_textos in ("informe-texto-completo.md", "informe-texto-completo.json", "informe-texto-completo.js"):
        if os.path.exists(os.path.join(carpeta_final, informe_textos)):
            shutil.copy2(os.path.join(carpeta_final, informe_textos), temporal)

    # Sustitución de los datos anteriores solo cuando todo ha ido bien.
    if os.path.isdir(carpeta_final):
        shutil.rmtree(carpeta_final)
    shutil.move(temporal, carpeta_final)
    print(f"Listo: {len(resueltas)} revistas resueltas, {len(informe)} pendientes de revisión, "
          f"{len(avisos)} con datos posiblemente desfasados.")


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
