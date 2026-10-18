"""Convierte el texto completo de un artículo (HTML o XML JATS) en la
estructura propia de la aplicación, sin scripts, estilos, marcos ni recursos
externos.

La estructura es un árbol JSON: cada nodo es una cadena de texto o una
lista [etiqueta, atributos, hijo, hijo...]. La aplicación lo construye con
createElement y textContent, nunca con innerHTML, y solo admite las
etiquetas y atributos de esta lista blanca.

Fidelidad: no se cambia ni se resume el texto. Tras convertir, se compara el
texto del original (sin lo que nunca es contenido: scripts, estilos,
formularios) con el del resultado, ignorando solo los espacios. Si no
coinciden, o si aparece algo que no se sabe reproducir con fidelidad
(fórmulas, vídeos, marcos), se lanza NoConvertible y el artículo se excluye.
"""

import html
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from comun import detectar_idioma, normalizar_idioma, url_segura

BLOQUES = {"section", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "li", "blockquote", "table",
           "caption", "thead", "tbody", "tfoot", "tr", "th", "td", "figure", "figcaption", "dl", "dt",
           "dd", "aside", "pre"}
EN_LINEA = {"em", "strong", "i", "b", "u", "sub", "sup", "br", "a", "q", "cite", "small", "span", "code",
            "abbr", "s", "mark"}
PERMITIDAS = BLOQUES | EN_LINEA | {"figura"}  # «figura»: imagen sustituida por su descripción
ATRIBUTOS = {"lang", "id", "href", "colspan", "rowspan", "scope", "start", "title", "alt", "rol"}

# Lo que nunca es texto del artículo y se descarta entero, con su contenido.
DESCARTAR = {"script", "style", "noscript", "template", "form", "button", "input", "select", "textarea",
             "nav", "head", "title", "meta", "link"}
# Lo que no se puede reproducir con fidelidad: si aparece, el artículo se excluye.
NO_REPRODUCIBLE = {"math", "iframe", "frame", "frameset", "object", "embed", "video", "audio", "canvas",
                   "svg", "applet"}


class NoConvertible(Exception):
    """El texto no se puede convertir con fidelidad; el artículo se excluye."""


def texto_plano(nodo):
    if isinstance(nodo, str):
        return nodo
    etiqueta, atributos, *hijos = nodo
    if etiqueta == "figura":
        return ""
    return "".join(texto_plano(h) for h in hijos)


def normalizar_espacios(texto):
    return re.sub(r"\s+", "", html.unescape(texto or ""))


def comprobar_fidelidad(texto_original, arbol):
    """Lanza NoConvertible si el texto convertido no es idéntico al original."""
    original = normalizar_espacios(texto_original)
    convertido = normalizar_espacios("".join(texto_plano(n) for n in arbol))
    if original != convertido:
        # Se busca la primera diferencia para que el informe sea útil.
        posicion = next((i for i, (a, b) in enumerate(zip(original, convertido)) if a != b),
                        min(len(original), len(convertido)))
        raise NoConvertible(f"El texto convertido no coincide con el original a partir de «"
                            f"{original[max(0, posicion - 30):posicion + 30]}».")


def contar(arbol, etiqueta):
    total = 0
    for nodo in arbol:
        if isinstance(nodo, list):
            total += (nodo[0] == etiqueta) + contar(nodo[2:], etiqueta)
    return total


# Identificadores: se renombran con un prefijo propio para no chocar con la
# aplicación, y los enlaces internos se reescriben con el mismo prefijo.

def id_propio(valor):
    limpio = re.sub(r"[^A-Za-z0-9_-]+", "-", valor or "").strip("-")
    return f"t-{limpio}" if limpio else None


def enlace(href):
    """Devuelve el href permitido: interno (#t-...) o externo http(s); si no, None."""
    if not href:
        return None
    href = href.strip()
    if href.startswith("#"):
        return "#" + (id_propio(href[1:]) or "")
    return url_segura(href)


# Conversión de HTML (galeradas de OJS, OpenEdition, SciELO)

_RENOMBRAR = {"article": "section", "main": "section", "header": None, "footer": None, "div": None,
              "font": None, "center": None, "big": None, "tt": "code", "strike": "s", "del": "s",
              "ins": "u", "kbd": "code", "samp": "code", "var": "i", "dfn": "i", "address": "p",
              "hgroup": None, "h1": "h1", "img": "img", "hr": None, "wbr": None, "picture": None,
              "source": None, "col": None, "colgroup": None, "label": None, "bdi": None, "bdo": None,
              "time": None, "data": None, "ruby": None, "rt": None, "rp": None, "details": None,
              "summary": "p", "sup": "sup", "sub": "sub"}


class _LectorHTML(HTMLParser):
    """Construye un árbol simple a partir de HTML, tolerando etiquetas sin cerrar."""

    VACIAS = {"br", "img", "hr", "meta", "link", "input", "col", "wbr", "source", "area", "base", "embed",
              "param", "track"}
    CIERRE_IMPLICITO = {"p": {"p", "div", "ul", "ol", "table", "h1", "h2", "h3", "h4", "h5", "h6",
                              "blockquote", "section", "figure", "dl", "pre"},
                        "li": {"li"}, "dt": {"dt", "dd"}, "dd": {"dt", "dd"}, "tr": {"tr"},
                        "td": {"td", "th", "tr"}, "th": {"td", "th", "tr"}}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = ["#raiz", {}]
        self.pila = [self.raiz]

    def handle_starttag(self, etiqueta, atributos):
        for abierta, cierran in self.CIERRE_IMPLICITO.items():
            if etiqueta in cierran and self.pila[-1][0] == abierta:
                self.pila.pop()
        nodo = [etiqueta, dict((k.lower(), v or "") for k, v in atributos)]
        self.pila[-1].append(nodo)
        if etiqueta not in self.VACIAS:
            self.pila.append(nodo)

    def handle_startendtag(self, etiqueta, atributos):
        self.pila[-1].append([etiqueta, dict((k.lower(), v or "") for k, v in atributos)])

    def handle_endtag(self, etiqueta):
        for i in range(len(self.pila) - 1, 0, -1):
            if self.pila[i][0] == etiqueta:
                del self.pila[i:]
                return

    def handle_data(self, datos):
        self.pila[-1].append(datos)


def leer_html(texto):
    lector = _LectorHTML()
    lector.feed(texto)
    lector.close()
    return lector.raiz


def buscar(nodo, condicion):
    """Primer descendiente que cumple la condición."""
    if isinstance(nodo, str):
        return None
    if condicion(nodo):
        return nodo
    for hijo in nodo[2:]:
        encontrado = buscar(hijo, condicion)
        if encontrado is not None:
            return encontrado
    return None


def texto_html(nodo):
    """Texto de un nodo de HTML leído, sin lo que nunca es contenido."""
    if isinstance(nodo, str):
        return nodo
    if nodo[0] in DESCARTAR or nodo[0] == "#comentario":
        return ""
    return "".join(texto_html(h) for h in nodo[2:])


def _nivel_minimo(nodo, minimo=7):
    if isinstance(nodo, str):
        return minimo
    if re.fullmatch(r"h[1-6]", nodo[0]):
        minimo = min(minimo, int(nodo[0][1]))
    for hijo in nodo[2:]:
        minimo = _nivel_minimo(hijo, minimo)
    return minimo


def convertir_html(contenedor, idioma_pagina=None):
    """Convierte un nodo de HTML leído en el árbol propio y comprueba la fidelidad.

    contenedor es el elemento que contiene el texto del artículo (por
    ejemplo el body de una galerada). Los encabezados se desplazan para que
    el primer nivel usado sea h2: el h1 de la vista es el título.
    """
    desplazamiento = 2 - _nivel_minimo(contenedor)

    def atributos_de(origen, destino):
        resultado = {}
        idioma = normalizar_idioma(origen[1].get("lang") or origen[1].get("xml:lang"))
        if idioma and idioma != (idioma_pagina or "es"):
            resultado["lang"] = idioma
        identificador = id_propio(origen[1].get("id") or origen[1].get("name"))
        if identificador and destino != "br":
            resultado["id"] = identificador
        if destino in ("td", "th"):
            for clave in ("colspan", "rowspan"):
                if re.fullmatch(r"\d{1,3}", origen[1].get(clave, "")):
                    resultado[clave] = origen[1][clave]
            if destino == "th" and origen[1].get("scope") in ("row", "col", "rowgroup", "colgroup"):
                resultado["scope"] = origen[1]["scope"]
        if destino == "ol" and re.fullmatch(r"\d{1,4}", origen[1].get("start", "")):
            resultado["start"] = origen[1]["start"]
        if destino == "abbr" and origen[1].get("title"):
            resultado["title"] = origen[1]["title"]
        return resultado

    def convertir(nodo):
        if isinstance(nodo, str):
            return [nodo]
        etiqueta = nodo[0]
        if etiqueta in DESCARTAR or etiqueta.startswith("#"):
            return []
        if etiqueta in NO_REPRODUCIBLE:
            raise NoConvertible(f"El texto contiene un elemento que no se puede reproducir con fidelidad: <{etiqueta}>.")
        hijos = [h for hijo in nodo[2:] for h in convertir(hijo)]
        if etiqueta == "img":
            alt = nodo[1].get("alt")
            return [["figura", {"alt": alt.strip()} if alt and alt.strip() else {}]]
        if re.fullmatch(r"h[1-6]", etiqueta):
            nivel = min(6, int(etiqueta[1]) + desplazamiento)
            return [[f"h{max(2, nivel)}", atributos_de(nodo, "h")] + hijos]
        if etiqueta == "a":
            destino = enlace(nodo[1].get("href"))
            atributos = atributos_de(nodo, "a")
            if destino:
                atributos["href"] = destino
            if not destino and not atributos:
                return hijos
            return [["a", atributos] + hijos]
        destino = _RENOMBRAR.get(etiqueta, etiqueta)
        if destino is None or destino not in PERMITIDAS:
            # Envoltorios sin significado (div, span con estilos...): se conservan
            # sus hijos y, si declaraban idioma o eran destino de enlaces, un span.
            atributos = atributos_de(nodo, "span")
            return [["span", atributos] + hijos] if atributos else hijos
        return [[destino, atributos_de(nodo, destino)] + hijos]

    arbol = [h for hijo in contenedor[2:] for h in convertir(hijo)]
    comprobar_fidelidad(texto_html(contenedor), arbol)
    return arbol


# Conversión de XML JATS

XLINK = "{http://www.w3.org/1999/xlink}href"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_JATS_EN_LINEA = {"italic": "i", "bold": "b", "underline": "u", "sup": "sup", "sub": "sub", "sc": "span",
                  "monospace": "code", "strike": "s", "roman": "span", "sans-serif": "span", "abbrev": "abbr",
                  "named-content": "span", "styled-content": "span", "inline-supplementary-material": "span",
                  "email": "span", "uri": "a", "ext-link": "a", "xref": "a", "break": "br", "target": "span",
                  "underline-start": "span", "underline-end": "span", "overline": "span", "chem-struct": "span",
                  "price": "span", "season": "span", "string-name": "span", "name": "span", "surname": "span",
                  "given-names": "span", "prefix": "span", "suffix": "span", "collab": "span",
                  "article-title": "span", "source": "i", "year": "span", "volume": "span", "issue": "span",
                  "fpage": "span", "lpage": "span", "publisher-name": "span", "publisher-loc": "span",
                  "pub-id": "span", "etal": "span", "date-in-citation": "span", "comment": "span",
                  "person-group": "span", "edition": "span", "elocation-id": "span", "issn": "span",
                  "isbn": "span", "page-range": "span", "chapter-title": "span", "trans-title": "span",
                  "trans-source": "span", "conf-name": "span", "conf-date": "span", "conf-loc": "span",
                  "institution": "span", "role": "span", "size": "span", "date": "span", "day": "span",
                  "month": "span", "patent": "span", "part-title": "span", "data-title": "span",
                  "version": "span", "series": "span", "gov": "span", "std": "span", "annotation": "span",
                  "label": "span", "attrib": "cite", "sig": "span", "sig-block": "p", "x": "span"}
_JATS_BLOQUES = {"p": "p", "disp-quote": "blockquote", "boxed-text": "aside", "table-wrap-foot": "aside", "def-list": "dl",
                 "term": "dt", "def": "dd", "verse-group": "blockquote", "verse-line": "p", "preformat": "pre",
                 "statement": "aside", "ack": "section", "app-group": "section", "app": "section",
                 "glossary": "section", "notes": "section", "fn-group": "section", "ref-list": "section",
                 "sec": "section", "speech": "blockquote", "speaker": "b"}


def _local(etiqueta):
    return etiqueta.split("}")[-1] if isinstance(etiqueta, str) else ""


def texto_xml(elemento):
    """Texto de un elemento JATS tal como se reproduce (sin imágenes)."""
    return "".join(elemento.itertext())


def convertir_jats(raiz, idioma_pagina=None):
    """Convierte body y back de un artículo JATS en el árbol propio.

    Devuelve (árbol, avisos de derechos, URL de licencias declaradas).
    """
    if _local(raiz.tag) != "article":
        raise NoConvertible("El XML no es un artículo JATS.")
    cuerpo = raiz.find("body")
    if cuerpo is None or not texto_xml(cuerpo).strip():
        raise NoConvertible("El XML JATS no incluye el cuerpo del artículo.")
    for elemento in raiz.iter():
        nombre = _local(elemento.tag)
        if nombre in ("math", "tex-math", "inline-formula", "disp-formula", "media", "alternatives"):
            raise NoConvertible(f"El texto contiene un elemento que no se puede reproducir con fidelidad: <{nombre}>.")

    idioma_documento = normalizar_idioma(raiz.get(XML_LANG)) or idioma_pagina or "es"

    def atributos_de(elemento):
        resultado = {}
        idioma = normalizar_idioma(elemento.get(XML_LANG))
        if idioma and idioma != idioma_documento:
            resultado["lang"] = idioma
        identificador = id_propio(elemento.get("id"))
        if identificador:
            resultado["id"] = identificador
        return resultado

    def hijos_de(elemento, nivel):
        lista = [elemento.text] if elemento.text else []
        for hijo in elemento:
            lista.extend(convertir(hijo, nivel))
            if hijo.tail:
                lista.append(hijo.tail)
        return lista

    def convertir(elemento, nivel):
        nombre = _local(elemento.tag)
        if nombre in ("graphic", "inline-graphic"):
            alt = elemento.find("alt-text")
            descripcion = (texto_xml(alt).strip() if alt is not None else "")
            return [["figura", {"alt": descripcion} if descripcion else {}]]
        if nombre in ("alt-text", "long-desc", "object-id", "permissions"):
            # El texto alternativo ya va dentro de la figura; los permisos van en la atribución.
            if nombre in ("alt-text", "long-desc") or nombre == "object-id":
                return []
            return []
        if nombre == "title":
            return [[f"h{max(2, min(6, nivel))}", atributos_de(elemento)] + hijos_de(elemento, nivel)]
        if nombre in ("sec", "ack", "app", "app-group", "glossary", "notes", "fn-group", "ref-list"):
            return [["section", atributos_de(elemento)] + hijos_de(elemento, nivel + 1)]
        if nombre in ("list",):
            ordenada = elemento.get("list-type") in ("order", "arabic", "alpha-lower", "alpha-upper",
                                                      "roman-lower", "roman-upper")
            return [["ol" if ordenada else "ul", atributos_de(elemento)] + hijos_de(elemento, nivel)]
        if nombre == "list-item":
            return [["li", atributos_de(elemento)] + hijos_de(elemento, nivel)]
        if nombre in ("fig", "table-wrap", "fig-group", "table-wrap-group", "chem-struct-wrap",
                      "supplementary-material", "graphic-group"):
            return [["figure", atributos_de(elemento)] + hijos_de(elemento, nivel)]
        if nombre == "caption":
            return [["figcaption", atributos_de(elemento)] + hijos_de(elemento, nivel)]
        if nombre in ("table", "thead", "tbody", "tfoot", "tr", "th", "td", "col", "colgroup"):
            if nombre in ("col", "colgroup"):
                return []
            atributos = atributos_de(elemento)
            for clave in ("colspan", "rowspan"):
                if re.fullmatch(r"\d{1,3}", elemento.get(clave, "")):
                    atributos[clave] = elemento.get(clave)
            if nombre == "th" and elemento.get("scope") in ("row", "col", "rowgroup", "colgroup"):
                atributos["scope"] = elemento.get("scope")
            return [[nombre, atributos] + hijos_de(elemento, nivel)]
        if nombre in ("fn", "ref"):
            return [["aside" if nombre == "fn" else "p", dict(atributos_de(elemento), rol=nombre)]
                    + hijos_de(elemento, nivel)]
        if nombre in ("mixed-citation", "element-citation", "citation", "nlm-citation"):
            return [["span", atributos_de(elemento)] + hijos_de(elemento, nivel)]
        if nombre in _JATS_BLOQUES:
            return [[_JATS_BLOQUES[nombre], atributos_de(elemento)] + hijos_de(elemento, nivel)]
        if nombre in _JATS_EN_LINEA:
            destino = _JATS_EN_LINEA[nombre]
            atributos = atributos_de(elemento)
            if destino == "a":
                if nombre == "xref" and elemento.get("rid"):
                    atributos["href"] = "#" + (id_propio(elemento.get("rid").split()[0]) or "")
                else:
                    href = url_segura(elemento.get(XLINK) or (texto_xml(elemento) if nombre == "uri" else None))
                    if href:
                        atributos["href"] = href
                    else:
                        destino = "span"
            if destino == "br":
                return [["br", {}]]
            return [[destino, atributos] + hijos_de(elemento, nivel)]
        raise NoConvertible(f"Elemento JATS no reconocido: <{nombre}>.")

    arbol = []
    for parte in (cuerpo, raiz.find("back")):
        if parte is None:
            continue
        arbol.extend(n for hijo in parte for n in _con_cola(convertir(hijo, 1), hijo))
        if parte.text and parte.text.strip():
            raise NoConvertible("El XML tiene texto suelto fuera de los elementos.")

    def texto_reproducible(elemento):
        partes = [elemento.text or ""]
        for hijo in elemento:
            if _local(hijo.tag) not in ("alt-text", "long-desc", "object-id", "permissions", "col", "colgroup"):
                partes.append(texto_reproducible(hijo))
            partes.append(hijo.tail or "")
        return "".join(partes)

    original = "".join(texto_reproducible(p) for p in (cuerpo, raiz.find("back")) if p is not None)
    comprobar_fidelidad(original, arbol)

    avisos, urls = [], []
    for permisos in raiz.iter("permissions"):
        for hijo in permisos:
            nombre = _local(hijo.tag)
            if nombre in ("copyright-statement", "license") and texto_xml(hijo).strip():
                avisos.append(re.sub(r"\s+", " ", texto_xml(hijo)).strip())
            if nombre == "license" and hijo.get(XLINK):
                urls.append(hijo.get(XLINK))
            for referencia in hijo.iter():
                if _local(referencia.tag) == "license_ref" and (referencia.text or "").strip():
                    urls.append(referencia.text.strip())
    return arbol, list(dict.fromkeys(avisos)), list(dict.fromkeys(urls))


def _con_cola(nodos, elemento):
    if elemento.tail and elemento.tail.strip():
        raise NoConvertible("El XML tiene texto suelto entre secciones.")
    return nodos


def leer_jats(contenido):
    """Analiza XML JATS sin resolver entidades externas ni DTD."""
    texto = contenido.decode("utf-8") if isinstance(contenido, bytes) else contenido
    texto = re.sub(r"<!DOCTYPE[^>\[]*(\[[^\]]*\])?>", "", texto, count=1, flags=re.S)
    if "<!ENTITY" in texto:
        raise NoConvertible("El XML declara entidades propias.")
    try:
        raiz = ET.fromstring(texto)
    except ET.ParseError as error:
        raise NoConvertible(f"El XML no se puede leer: {error}") from error
    # Se quitan los espacios de nombres de JATS para tratar las etiquetas por su nombre.
    for elemento in raiz.iter():
        if isinstance(elemento.tag, str) and elemento.tag.startswith("{") and "xlink" not in elemento.tag \
                and "XML/1998" not in elemento.tag and "ali" not in elemento.tag.split("}")[0]:
            if "mathml" in elemento.tag.lower():
                continue
            elemento.tag = elemento.tag.split("}")[1]
    return raiz


# Marcas de idioma en párrafos sin lang declarado

def marcar_idiomas(arbol, idioma_base="es"):
    """Añade lang a párrafos y encabezados cuyo idioma el detector distingue con claridad."""
    for nodo in arbol:
        if not isinstance(nodo, list):
            continue
        etiqueta, atributos = nodo[0], nodo[1]
        if "lang" in atributos:
            continue
        if etiqueta in ("p", "li", "h2", "h3", "h4", "h5", "h6", "blockquote", "figcaption", "td", "th", "dd"):
            idioma = detectar_idioma(texto_plano(nodo), minimo_palabras=8)
            if idioma and idioma != idioma_base:
                atributos["lang"] = idioma
                continue
        marcar_idiomas(nodo[2:], idioma_base)
    return arbol


# Tabla de contenidos y comprobaciones finales

def tabla_de_contenidos(arbol):
    """Lista de (id, nivel, texto) de los encabezados; añade id a los que no tienen."""
    entradas, contador = [], [0]

    def recorrer(nodos):
        for nodo in nodos:
            if not isinstance(nodo, list):
                continue
            if re.fullmatch(r"h[2-4]", nodo[0]):
                contador[0] += 1
                if "id" not in nodo[1]:
                    nodo[1]["id"] = f"t-seccion-{contador[0]}"
                texto = re.sub(r"\s+", " ", texto_plano(nodo)).strip()
                if texto:
                    entradas.append({"id": nodo[1]["id"], "nivel": int(nodo[0][1]), "texto": texto,
                                     "lang": nodo[1].get("lang")})
            recorrer(nodo[2:])

    recorrer(arbol)
    return entradas


def ids_y_enlaces(arbol):
    ids, internos = set(), []

    def recorrer(nodos):
        for nodo in nodos:
            if not isinstance(nodo, list):
                continue
            if "id" in nodo[1]:
                ids.add(nodo[1]["id"])
            if nodo[0] == "a" and nodo[1].get("href", "").startswith("#"):
                internos.append(nodo)
            recorrer(nodo[2:])

    recorrer(arbol)
    return ids, internos


def _enlaza_a(nodo, ids_destino):
    """True si el nodo contiene un enlace interno a alguno de esos ids."""
    if not isinstance(nodo, list):
        return False
    if nodo[0] == "a" and nodo[1].get("href", "")[1:] in ids_destino:
        return True
    return any(_enlaza_a(h, ids_destino) for h in nodo[2:])


def _por_id(arbol, identificador):
    return next((n for n in _recorrer(arbol) if n[1].get("id") == identificador), None)


def _recorrer(nodos):
    for nodo in nodos:
        if isinstance(nodo, list):
            yield nodo
            yield from _recorrer(nodo[2:])


def preparar(arbol):
    """Deja el árbol listo: enlaces internos rotos convertidos en texto e ids de vuelta.

    Devuelve (árbol, vueltas). vueltas indica, para cada nota o referencia
    que no tiene ya un enlace de vuelta en el original, el id de la primera
    llamada, para que la aplicación añada un enlace «Volver al texto».
    """
    ids, internos = ids_y_enlaces(arbol)
    for nodo in internos:
        if nodo[1]["href"][1:] not in ids:
            # Un enlace interno sin destino no lleva a ninguna parte: queda como texto.
            del nodo[1]["href"]
            nodo[0] = "span"
    # Cada llamada a nota recibe un id para poder volver a ella desde la nota.
    vistos = {}
    for nodo in internos:
        if "href" in nodo[1] and "id" not in nodo[1]:
            destino = nodo[1]["href"][1:]
            vistos[destino] = vistos.get(destino, 0) + 1
            nodo[1]["id"] = f"t-llamada-{destino[2:]}-{vistos[destino]}"
            ids.add(nodo[1]["id"])
    vueltas = {}
    for nodo in internos:
        if "href" not in nodo[1]:
            continue
        destino = nodo[1]["href"][1:]
        if destino in vueltas:
            continue
        objetivo = _por_id(arbol, destino)
        # Si el destino es otro enlace (la llamada a la que vuelve una nota),
        # no es una nota: no se le añade un enlace de vuelta, que quedaría
        # anidado dentro de otro enlace.
        if objetivo is not None and objetivo[0] == "a":
            continue
        llamadas = {n[1]["id"] for n in internos if n[1].get("href") == "#" + destino and "id" in n[1]}
        # Si la nota ya enlaza de vuelta a su llamada (como en Word u OpenEdition), no se añade otro.
        if objetivo is not None and not _enlaza_a(objetivo, llamadas) and nodo[1].get("id"):
            vueltas[destino] = nodo[1]["id"]
    return arbol, vueltas


def validar(arbol):
    """Última barrera: solo etiquetas y atributos de la lista blanca, y href seguros."""
    for nodo in arbol:
        if isinstance(nodo, str):
            continue
        if not isinstance(nodo, list) or len(nodo) < 2 or nodo[0] not in PERMITIDAS or not isinstance(nodo[1], dict):
            raise NoConvertible(f"Nodo no permitido en el resultado: {str(nodo)[:60]}")
        for clave, valor in nodo[1].items():
            if clave not in ATRIBUTOS or not isinstance(valor, str):
                raise NoConvertible(f"Atributo no permitido: {clave}")
            if clave == "href" and not (valor.startswith("#t-") or re.match(r"^https?://", valor)):
                raise NoConvertible(f"Enlace no permitido: {valor[:60]}")
        validar(nodo[2:])
    return arbol
