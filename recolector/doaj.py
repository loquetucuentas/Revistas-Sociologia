"""Consulta a DOAJ: revistas de sociología publicadas en español."""

import urllib.parse

from comun import (detectar_idioma, limpiar_texto, normalizar_idioma, normalizar_licencia, obtener_json, sin_tildes,
                   url_segura)

API = "https://doaj.org/api/search/journals/"
# La API de DOAJ no admite comodines (*), así que se pide el término
# "sociology", que también encuentra "Sociology (General)" y "Urban sociology".
# Después se filtra en local por código LCC HM o término con "sociolog".
CONSULTA = "bibjson.language:ES AND bibjson.subject.term:sociology"
TAMANO_PAGINA = 100


def es_de_sociologia(bibjson):
    for materia in bibjson.get("subject") or []:
        codigo = (materia.get("code") or "").upper()
        termino = (materia.get("term") or "").lower()
        if codigo.startswith("HM") or "sociolog" in termino:
            return True
    return False


def idiomas(bibjson):
    codigos = [normalizar_idioma(i) for i in bibjson.get("language") or []]
    return [c for c in codigos if c]


def convertir(registro):
    """Transforma un registro de DOAJ en la ficha de revista de la aplicación."""
    b = registro.get("bibjson") or {}
    pissn, eissn = b.get("pissn"), b.get("eissn")
    identificador = eissn or pissn
    if not identificador:
        return None
    editorial = b.get("publisher") or {}
    ref = b.get("ref") or {}
    licencias = [normalizar_licencia(l.get("url"), l.get("type")) for l in b.get("license") or []]
    materias = [limpiar_texto(m.get("term")) for m in b.get("subject") or [] if m.get("term")]
    titulo = limpiar_texto(b.get("title"))
    alternativo = limpiar_texto(b.get("alternative_title")) or None
    return {
        "id": identificador,
        "titulo": titulo,
        # Los nombres de revista son nombres propios (excepción de WCAG 3.1.2),
        # pero si el idioma es claro se marca para que VoiceOver los pronuncie bien.
        "idioma_titulo": detectar_idioma(titulo, minimo_palabras=2),
        "titulo_alternativo": alternativo,
        "idioma_titulo_alternativo": detectar_idioma(alternativo, minimo_palabras=2),
        "idiomas": idiomas(b),
        "issn_impreso": pissn,
        "issn_electronico": eissn,
        "editorial": limpiar_texto(editorial.get("name")) or None,
        "pais": editorial.get("country"),
        "materias": materias,
        "palabras_clave": [limpiar_texto(k) for k in b.get("keywords") or []],
        "licencias": [l for l in licencias if l],
        "url": url_segura(ref.get("journal")),
        "url_doaj": f"https://doaj.org/toc/{identificador}",
        "descripcion": None,
        "fuente_ficha": "DOAJ",
    }


def buscar_revistas(limite=None):
    """Devuelve las revistas de DOAJ que cumplen materia e idioma, ordenadas por título."""
    revistas, pagina = [], 1
    while True:
        datos = obtener_json(API + urllib.parse.quote(CONSULTA, safe=""),
                             {"page": pagina, "pageSize": TAMANO_PAGINA})
        resultados = datos.get("results") or []
        for registro in resultados:
            b = registro.get("bibjson") or {}
            # Se vuelve a filtrar aquí por si la consulta de DOAJ es más amplia.
            if "es" not in idiomas(b) or not es_de_sociologia(b):
                continue
            ficha = convertir(registro)
            if ficha and ficha["titulo"]:
                revistas.append(ficha)
        if len(resultados) < TAMANO_PAGINA or pagina * TAMANO_PAGINA >= datos.get("total", 0):
            break
        pagina += 1
    unicas = {r["id"]: r for r in revistas}
    ordenadas = sorted(unicas.values(), key=lambda r: sin_tildes(r["titulo"]))
    return ordenadas[:limite] if limite else ordenadas
