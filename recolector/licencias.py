"""Decide, artículo por artículo, si su licencia permite mostrar el texto completo.

Solo se admiten las licencias Creative Commons que permiten reutilizar y
adaptar: CC BY, CC BY-SA, CC BY-NC y CC BY-NC-SA. Ante cualquier duda la
respuesta es no: el artículo se queda con ficha, resumen y enlace al original.
"""

import datetime
import re

ADMITIDAS = {
    "by": "Atribución",
    "by-sa": "Atribución-CompartirIgual",
    "by-nc": "Atribución-NoComercial",
    "by-nc-sa": "Atribución-NoComercial-CompartirIgual",
}
CON_ND = {"by-nd", "by-nc-nd"}
JURISDICCIONES = {
    "es": "España", "ar": "Argentina", "br": "Brasil", "cl": "Chile", "co": "Colombia", "mx": "México",
    "pe": "Perú", "pt": "Portugal", "ec": "Ecuador", "cr": "Costa Rica", "gt": "Guatemala", "pr": "Puerto Rico",
    "ve": "Venezuela", "it": "Italia", "fr": "Francia", "pl": "Polonia", "igo": "IGO",
}
# Versiones del artículo a las que puede referirse la licencia en Crossref.
VERSIONES_PUBLICADAS = {"vor", "unspecified", None}

_CC = re.compile(
    r"^https?://(?:www\.)?creativecommons\.org/licenses/([a-z-]+)/(\d\.\d)"
    r"(?:/([a-z]{2,3}))?/?(?:legalcode(?:\.[a-z_-]+)?|deed\.[a-z_-]+)?/?$", re.I)
_DERECHOS_RESERVADOS = re.compile(r"(todos los derechos reservados|all rights reserved|"
                                  r"todos os direitos reservados|tous droits réservés)", re.I)


def leer_licencia_cc(url):
    """Interpreta una URL de licencia Creative Commons.

    Devuelve {codigo, version, jurisdiccion, url} o None si la URL no es una
    licencia CC reconocible sin ambigüedad.
    """
    if not url:
        return None
    coincidencia = _CC.match(url.strip())
    if not coincidencia:
        return None
    codigo, version, jurisdiccion = (coincidencia.group(1).lower(), coincidencia.group(2),
                                     (coincidencia.group(3) or "").lower() or None)
    if codigo not in ADMITIDAS and codigo not in CON_ND:
        return None
    if jurisdiccion and jurisdiccion not in JURISDICCIONES:
        return None
    return {"codigo": codigo, "version": version, "jurisdiccion": jurisdiccion, "url": url.strip()}


def ficha_licencia(cc):
    """Nombre completo en español, nombre corto y enlaces de una licencia admitida."""
    codigo, version, jurisdiccion = cc["codigo"], cc["version"], cc["jurisdiccion"]
    if version == "4.0":
        ambito = "Internacional"
    elif jurisdiccion:
        ambito = JURISDICCIONES[jurisdiccion]
    else:
        ambito = "Unported"
    base = f"https://creativecommons.org/licenses/{codigo}/{version}/" + (f"{jurisdiccion}/" if jurisdiccion else "")
    return {
        "codigo": codigo,
        "nombre": f"CC {codigo.upper()} {version}" + (f" {jurisdiccion.upper()}" if jurisdiccion else ""),
        "nombre_completo": f"Creative Commons {ADMITIDAS[codigo]} {version} {ambito}",
        "url": cc["url"],
        # El texto legal en español solo existe con seguridad para la versión 4.0.
        "url_legal": base + ("legalcode.es" if version == "4.0" else "legalcode"),
    }


def _fecha(partes):
    try:
        partes = (partes or {}).get("date-parts", [[None]])[0]
        return datetime.date(int(partes[0]), int(partes[1]) if len(partes) > 1 else 1,
                             int(partes[2]) if len(partes) > 2 else 1)
    except (TypeError, ValueError, IndexError):
        return None


def clasificar(licencias, hoy=None):
    """Clasifica la lista «license» de una obra de Crossref.

    Devuelve (apta, ficha o None, motivo). El motivo es un código estable
    para el informe: sin-licencia, solo-otra-version, varias-licencias,
    no-cc, nd, embargo o admitida.
    """
    hoy = hoy or datetime.date.today()
    licencias = licencias or []
    if not licencias:
        return False, None, "sin-licencia"
    publicadas = [l for l in licencias if l.get("content-version") in VERSIONES_PUBLICADAS]
    if not publicadas:
        return False, None, "solo-otra-version"
    leidas = [leer_licencia_cc(l.get("URL")) for l in publicadas]
    if any(l is None for l in leidas):
        return False, None, "no-cc"
    distintas = {(l["codigo"], l["version"], l["jurisdiccion"]) for l in leidas}
    if len(distintas) > 1:
        return False, None, "varias-licencias"
    cc = leidas[0]
    if cc["codigo"] in CON_ND:
        return False, None, "nd"
    for licencia in publicadas:
        inicio = _fecha(licencia.get("start"))
        if inicio and inicio > hoy:
            return False, None, "embargo"
    return True, ficha_licencia(cc), "admitida"


def contradice(ficha, urls_pagina, textos_pagina=()):
    """Comprueba si la página del artículo declara otra licencia o derechos reservados.

    urls_pagina son las URL de licencia de la página (rel="license",
    DC.rights, JATS <license>). Devuelve el motivo o None si no hay
    contradicción.
    """
    for texto in textos_pagina:
        if _DERECHOS_RESERVADOS.search(texto or ""):
            return "derechos-reservados"
    for url in urls_pagina:
        cc = leer_licencia_cc(url)
        if cc is None:
            if re.search(r"creativecommons\.org", url or "", re.I):
                return "licencia-pagina-ambigua"
            continue
        if cc["codigo"] != ficha["codigo"]:
            return "licencia-pagina-distinta"
    return None


MOTIVOS = {
    "sin-licencia": "Crossref no declara ninguna licencia para el artículo.",
    "solo-otra-version": "La licencia declarada no corresponde a la versión publicada del artículo.",
    "varias-licencias": "Crossref declara varias licencias distintas para la versión publicada.",
    "no-cc": "La licencia no es Creative Commons o no se puede interpretar sin ambigüedad.",
    "nd": "La licencia no permite obras derivadas (ND).",
    "embargo": "La licencia empieza a regir en una fecha futura.",
    "derechos-reservados": "La página del artículo indica que todos los derechos están reservados.",
    "licencia-pagina-ambigua": "La página del artículo declara una licencia que no se puede interpretar.",
    "licencia-pagina-distinta": "La página del artículo declara una licencia distinta a la de Crossref.",
}
