#!/usr/bin/env python3
"""Texto completo de los artículos cuya licencia lo permite.

Dos pasos, que se lanzan por separado:

1. metadatos: pregunta a Crossref (solo a api.crossref.org) la licencia, la
   página del artículo y los enlaces de texto completo de cada artículo de
   data. Clasifica la licencia y escribe data/textos/estado.json y la lista
   de dominios de revista que habría que consultar.
2. textos: para los artículos con licencia admitida, descarga la versión
   HTML o XML JATS de la web de la revista, respetando robots.txt, con
   al menos dos segundos entre peticiones a un mismo servidor, sin repetir
   descargas de lo que no ha cambiado y deteniéndose ante limitaciones de
   tráfico. Nunca usa PDF. Convierte el texto a la estructura propia de la
   aplicación (saneado.py) y escribe un archivo por artículo en data/textos.

Todo artículo que no se muestre queda en data/informe-texto-completo.md con
el motivo.

Uso: python3 recolector/texto_completo.py metadatos|textos [--datos data]
"""

import argparse
import datetime
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import licencias  # noqa: E402
from comun import ErrorRed, obtener_json  # noqa: E402

API = "https://api.crossref.org"
CAMPOS = "DOI,license,link,resource,URL,author"
# Tipos de contenido que pueden ser texto completo aprovechable. El PDF no.
TIPOS_TEXTO = {"text/html", "application/xhtml+xml", "application/xml", "text/xml",
               "application/jats+xml", "unspecified"}


def ahora():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def leer_json(ruta, defecto=None):
    try:
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        return defecto


def escribir_json(ruta, contenido):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=1)
        archivo.write("\n")


def articulos_de(carpeta):
    """Recorre (revista, número, artículo) de los datos actuales."""
    listado = leer_json(os.path.join(carpeta, "revistas.json"))
    for revista in listado["revistas"]:
        datos = leer_json(os.path.join(carpeta, revista["archivo"]))
        for numero in datos["numeros"]:
            for articulo in numero["articulos"]:
                yield datos["revista"], numero, articulo


def enlaces_texto(obra):
    """Enlaces de texto completo que declara Crossref, sin PDF."""
    enlaces = []
    for enlace in obra.get("link") or []:
        tipo = (enlace.get("content-type") or "unspecified").split(";")[0].strip().lower()
        url = enlace.get("URL") or ""
        if tipo in TIPOS_TEXTO and url.startswith(("http://", "https://")) and not url.lower().endswith(".pdf"):
            enlaces.append({"url": url, "tipo": tipo, "uso": enlace.get("intended-application")})
    return enlaces


def pagina_articulo(obra):
    return ((obra.get("resource") or {}).get("primary") or {}).get("URL")


def consultar_revista(issns, dois):
    """Pide a Crossref los metadatos de los DOI indicados, por ISSN y, si faltan, uno a uno."""
    encontrados = {}
    for issn in issns:
        if not issn:
            continue
        try:
            datos = obtener_json(f"{API}/journals/{issn}/works", {
                "filter": "type:journal-article", "sort": "published", "order": "desc",
                "rows": 300, "select": CAMPOS})
        except ErrorRed:
            continue
        for obra in (datos.get("message") or {}).get("items") or []:
            doi = (obra.get("DOI") or "").lower()
            if doi in dois:
                encontrados[doi] = obra
    for doi in sorted(dois - set(encontrados)):
        try:
            datos = obtener_json(f"{API}/works/{urllib.parse.quote(doi, safe='/')}")
            encontrados[doi] = datos.get("message") or {}
        except ErrorRed:
            pass
    return encontrados


def paso_metadatos(carpeta):
    estado_ruta = os.path.join(carpeta, "textos", "estado.json")
    estado = leer_json(estado_ruta, {"articulos": {}})
    por_revista = {}
    for revista, numero, articulo in articulos_de(carpeta):
        por_revista.setdefault(revista["id"], (revista, []))[1].append((numero, articulo))

    for posicion, (revista, lista) in enumerate(por_revista.values(), 1):
        print(f"[{posicion}/{len(por_revista)}] {revista['titulo']}", flush=True)
        dois = {a["doi"].lower() for _, a in lista if a.get("doi")}
        obras = consultar_revista([revista.get("issn_electronico"), revista.get("issn_impreso")], dois)
        for numero, articulo in lista:
            doi = articulo["doi"].lower()
            obra = obras.get(doi)
            registro = estado["articulos"].setdefault(doi, {})
            registro.update({"revista": revista["id"], "numero": numero["id"], "titulo": articulo["titulo"]})
            if obra is None:
                registro.update({"apta": False, "motivo": "sin-metadatos", "licencia": None})
                continue
            apta, ficha, motivo = licencias.clasificar(obra.get("license"))
            registro.update({
                "apta": apta, "motivo": motivo, "licencia": ficha,
                "licencias_crossref": [{"url": l.get("URL"), "version": l.get("content-version")}
                                       for l in obra.get("license") or []],
                "pagina": pagina_articulo(obra), "enlaces": enlaces_texto(obra),
                # Apellidos y nombre por separado, para la cita en estilo APA.
                "autores_cita": [{"apellidos": a.get("family"), "nombre_pila": a.get("given"), "nombre": a.get("name")}
                                 for a in obra.get("author") or [] if a.get("family") or a.get("name")],
            })
    estado["metadatos_actualizados"] = ahora()
    escribir_json(estado_ruta, estado)
    return estado


def dominios(estado):
    """Dominios de revista que el paso de textos necesitaría consultar."""
    resultado = {}
    for registro in estado["articulos"].values():
        if not registro.get("apta"):
            continue
        urls = [registro.get("pagina")] + [e["url"] for e in registro.get("enlaces") or []]
        for url in filter(None, urls):
            dominio = urllib.parse.urlsplit(url).netloc.lower()
            resultado.setdefault(dominio, set()).add(registro["revista"])
    return {d: sorted(r) for d, r in sorted(resultado.items())}


MOTIVOS_TEXTO = {
    "sin-metadatos": "Crossref no devuelve los metadatos del artículo.",
    "solo-pdf": "La revista solo ofrece el texto completo en PDF, que no se usa.",
    "no-convertible": "El HTML o XML no se ha podido convertir con fidelidad.",
    "robots": "robots.txt de la revista no permite descargar la página.",
    "limite-trafico": "El servidor de la revista ha pedido reducir el tráfico; se volverá a intentar en otra ejecución.",
    "dominio-no-permitido": "La red del entorno no permite el dominio de la revista.",
    "servidor": "No se ha podido descargar la página del artículo.",
}


def situacion(registro):
    """(clave de estado, motivo legible, detalle) de un artículo."""
    if not registro.get("apta"):
        motivo = registro.get("motivo")
        return "excluido", licencias.MOTIVOS.get(motivo) or MOTIVOS_TEXTO.get(motivo, motivo), None
    resultado = registro.get("resultado")
    if not resultado:
        return "pendiente", "Todavía no se ha intentado descargar el texto.", None
    motivo = resultado.get("motivo")
    texto = licencias.MOTIVOS.get(motivo) or MOTIVOS_TEXTO.get(motivo, motivo)
    detalle = resultado.get("detalle")
    if isinstance(detalle, list):
        detalle = " ".join(detalle)
    return resultado["estado"], texto, detalle


def escribir_resultados(carpeta, estado):
    """Índice de textos, marca en cada artículo e informe de exclusiones."""
    indice = {doi: r["resultado"]["archivo"] for doi, r in estado["articulos"].items()
              if (r.get("resultado") or {}).get("estado") == "disponible"
              and os.path.exists(os.path.join(carpeta, r["resultado"]["archivo"]))}
    escribir_json(os.path.join(carpeta, "textos", "indice.json"), indice)
    aplicar_indice(carpeta, indice)

    grupos = {}
    for doi, registro in sorted(estado["articulos"].items(), key=lambda par: (par[1]["revista"], par[0])):
        clave, motivo, detalle = situacion(registro)
        grupos.setdefault(clave, []).append((doi, registro, motivo, detalle))
    titulos = {r["id"]: r["titulo"] for r in leer_json(os.path.join(carpeta, "revistas.json"))["revistas"]}
    resumen = {clave: len(lista) for clave, lista in grupos.items()}
    revistas_con_texto = sorted({estado["articulos"][d]["revista"] for d in indice})
    escribir_json(os.path.join(carpeta, "informe-texto-completo.json"), {
        "generado": ahora(), "resumen": resumen, "revistas_con_texto": revistas_con_texto,
        "articulos": {doi: {"estado": situacion(r)[0], "motivo": situacion(r)[1], "detalle": situacion(r)[2],
                            "revista": r["revista"], "titulo": r["titulo"]}
                      for doi, r in estado["articulos"].items()}})

    nombres = {"disponible": "Con lectura completa en la aplicación", "sin-texto": "Licencia admitida, pero solo hay PDF",
               "excluido": "Excluidos", "pendiente": "Pendientes de un nuevo intento"}
    lineas = ["# Texto completo: artículos incluidos y excluidos", "",
              f"Generado el {ahora()}. Solo se muestra el texto completo de los artículos cuya licencia, declarada en",
              "Crossref y sin contradicción en la página del artículo, es CC BY, CC BY-SA, CC BY-NC o CC BY-NC-SA,",
              "y de los que la revista publica una versión HTML o XML JATS que se ha podido convertir con fidelidad.",
              "Los demás conservan su ficha, su resumen y el enlace al original.", "", "## Resumen", ""]
    for clave in ("disponible", "sin-texto", "excluido", "pendiente"):
        lineas.append(f"{nombres[clave]}: {resumen.get(clave, 0)} artículos.")
    lineas += ["", f"Revistas con al menos un artículo legible en la aplicación: {len(revistas_con_texto)}.", ""]
    motivos = {}
    for clave in ("sin-texto", "excluido", "pendiente"):
        for _, _, motivo, _ in grupos.get(clave, []):
            motivos[motivo] = motivos.get(motivo, 0) + 1
    if motivos:
        lineas += ["## Motivos de exclusión", ""]
        lineas += [f"{n}. {motivo} {total} artículos." for n, (motivo, total) in
                   enumerate(sorted(motivos.items(), key=lambda par: -par[1]), 1)] + [""]
    if estado.get("dominios_detenidos"):
        lineas += ["## Servidores que no se han consultado o se han dejado de consultar", ""]
        lineas += [f"{dominio}: {motivo}" for dominio, motivo in sorted(estado["dominios_detenidos"].items())] + [""]
    for clave in ("sin-texto", "excluido", "pendiente"):
        if not grupos.get(clave):
            continue
        lineas += [f"## {nombres[clave]}", ""]
        actual = None
        for doi, registro, motivo, detalle in grupos[clave]:
            if registro["revista"] != actual:
                actual = registro["revista"]
                lineas += [f"### {titulos.get(actual, actual)}", ""]
            lineas.append(f"{doi}, «{registro['titulo']}». {motivo}" + (f" Detalle: {detalle}" if detalle else ""))
            lineas.append("")
    with open(os.path.join(carpeta, "informe-texto-completo.md"), "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas))
    return resumen, revistas_con_texto


def aplicar_indice(carpeta, indice):
    """Añade a cada artículo de data/revistas la ruta de su texto completo, si lo tiene."""
    from comun import escribir_datos

    listado = leer_json(os.path.join(carpeta, "revistas.json"))
    for revista in listado["revistas"]:
        datos = leer_json(os.path.join(carpeta, revista["archivo"]))
        cambiado = False
        for numero in datos["numeros"]:
            for articulo in numero["articulos"]:
                archivo = indice.get((articulo.get("doi") or "").lower())
                if articulo.get("texto_completo") != archivo:
                    if archivo:
                        articulo["texto_completo"] = archivo
                    else:
                        articulo.pop("texto_completo", None)
                    cambiado = True
        if cambiado:
            escribir_datos(carpeta, revista["archivo"], datos)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paso", choices=["metadatos", "textos"])
    parser.add_argument("--datos", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    argumentos = parser.parse_args()
    carpeta = os.path.abspath(argumentos.datos)
    if argumentos.paso == "metadatos":
        estado = paso_metadatos(carpeta)
        lista = dominios(estado)
        escribir_json(os.path.join(carpeta, "textos", "dominios.json"), lista)
        aptos = sum(1 for r in estado["articulos"].values() if r.get("apta"))
        print(f"{aptos} artículos con licencia admitida en {len(lista)} dominios.")
    else:
        import textos  # noqa: E402  (paso 2, en su propio módulo)
        textos.paso_textos(carpeta)
        resumen, revistas = escribir_resultados(carpeta, leer_json(os.path.join(carpeta, "textos", "estado.json")))
        print(f"Resultado: {resumen}. Revistas con texto: {len(revistas)}.")


if __name__ == "__main__":
    main()
