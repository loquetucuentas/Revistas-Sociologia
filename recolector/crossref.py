"""Consulta a Crossref: últimos números y artículos de una revista por ISSN."""

import re

from comun import (ErrorRed, idioma_de, limpiar_resumen, limpiar_texto, normalizar_idioma,
                   normalizar_licencia, obtener_json, slug, url_segura)

API = "https://api.crossref.org/journals/{issn}/works"
CAMPOS = "DOI,title,original-title,author,abstract,license,URL,volume,issue,published,issued,page,language,type"
FILAS = 300


def fecha(obra):
    """Devuelve (texto ISO parcial, tupla ordenable) con la fecha de publicación."""
    for clave in ("published", "issued", "published-print", "published-online"):
        partes = ((obra.get(clave) or {}).get("date-parts") or [[None]])[0]
        if partes and partes[0]:
            partes = [int(p) for p in partes if p]
            texto = "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(partes))
            return texto, tuple(partes + [0] * (3 - len(partes)))
    return None, (0, 0, 0)


def numero_ordenable(texto):
    encontrado = re.search(r"\d+", texto or "")
    return int(encontrado.group()) if encontrado else 0


def etiqueta_numero(volumen, numero, anio):
    partes = []
    if volumen:
        partes.append(f"Vol. {volumen}")
    if numero:
        partes.append(f"núm. {numero}")
    if not partes:
        partes.append("Publicación continua")
    texto = ", ".join(partes)
    return f"{texto} ({anio})" if anio else texto


def autores(obra):
    lista = []
    for autor in obra.get("author") or []:
        nombre = " ".join(p for p in (autor.get("given"), autor.get("family")) if p) or autor.get("name")
        if nombre:
            orcid = url_segura(autor.get("ORCID"))
            lista.append({"nombre": limpiar_texto(nombre), "orcid": orcid})
    return lista


def licencia(obra):
    licencias = obra.get("license") or []
    # Se prefiere la licencia de la versión publicada (vor).
    licencias.sort(key=lambda l: l.get("content-version") != "vor")
    for item in licencias:
        normalizada = normalizar_licencia(item.get("URL"))
        if normalizada:
            return normalizada
    return None


def articulo(obra):
    titulos = obra.get("title") or obra.get("original-title") or []
    titulo = limpiar_texto(titulos[0]) if titulos else ""
    if not titulo or not obra.get("DOI"):
        return None
    doi = obra["DOI"]
    resumen = limpiar_resumen(obra.get("abstract")) or None
    declarado = normalizar_idioma(obra.get("language"))
    return {
        "id": doi,
        "titulo": titulo,
        "idioma_titulo": idioma_de(titulo, declarado, minimo_palabras=5),
        "autores": autores(obra),
        "resumen": resumen,
        "idioma_resumen": idioma_de(resumen, declarado) if resumen else None,
        "licencia": licencia(obra),
        "url": f"https://doi.org/{doi}",
        "doi": doi,
        "paginas": obra.get("page"),
        "fuente": "Crossref",
    }


def agrupar(obras, cantidad=3):
    """Agrupa los artículos por volumen y número y devuelve los más recientes."""
    grupos = {}
    for obra in obras:
        art = articulo(obra)
        if not art:
            continue
        texto_fecha, orden = fecha(obra)
        volumen = limpiar_texto(obra.get("volume")) or None
        numero = limpiar_texto(obra.get("issue")) or None
        anio = orden[0] or None
        # Sin volumen ni número se agrupa por año (publicación continua).
        clave = (volumen, numero, None if (volumen or numero) else anio)
        grupo = grupos.setdefault(clave, {"volumen": volumen, "numero": numero, "anio": anio,
                                          "fecha": texto_fecha, "orden": orden, "articulos": []})
        if orden > grupo["orden"]:
            grupo["orden"], grupo["fecha"], grupo["anio"] = orden, texto_fecha, anio
        if all(a["id"] != art["id"] for a in grupo["articulos"]):
            grupo["articulos"].append(art)
    recientes = sorted(grupos.values(), reverse=True,
                       key=lambda g: (g["orden"][0], numero_ordenable(g["volumen"]),
                                      numero_ordenable(g["numero"]), g["orden"]))[:cantidad]
    return [preparar_numero(g, "Crossref") for g in recientes]


def preparar_numero(grupo, fuente):
    """Da forma final a un número: identificador, etiqueta y artículos ordenados."""
    volumen, numero, anio = grupo["volumen"], grupo["numero"], grupo["anio"]
    identificador = slug("-".join(str(p) for p in (
        f"v{volumen}" if volumen else "", f"n{numero}" if numero else "", anio or "") if p))
    articulos = sorted(grupo["articulos"], key=lambda a: (numero_ordenable(a.get("paginas")), a["titulo"]))
    return {
        "id": identificador,
        "volumen": volumen,
        "numero": numero,
        "anio": anio,
        "fecha": grupo["fecha"],
        "etiqueta": etiqueta_numero(volumen, numero, anio),
        "fuente": fuente,
        "articulos": articulos,
    }


def ultimos_numeros(issns, cantidad=3):
    """Prueba cada ISSN de la revista y devuelve los números del primero con datos."""
    ultimo_error = None
    for issn in [i for i in issns if i]:
        try:
            try:
                datos = obtener_json(API.format(issn=issn), {
                    "filter": "type:journal-article", "sort": "published", "order": "desc",
                    "rows": FILAS, "select": CAMPOS})
            except ErrorRed as error:
                if error.estado != 400:
                    raise
                # Si Crossref rechaza la selección de campos, se pide sin ella.
                datos = obtener_json(API.format(issn=issn), {
                    "filter": "type:journal-article", "sort": "published", "order": "desc", "rows": 100})
        except ErrorRed as error:
            ultimo_error = error
            continue
        obras = (datos.get("message") or {}).get("items") or []
        numeros = agrupar(obras, cantidad)
        if numeros:
            return numeros
    if ultimo_error and ultimo_error.estado != 404:
        raise ultimo_error
    return []
