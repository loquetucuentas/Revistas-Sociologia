"""Consulta OAI-PMH para revistas OJS con poca cobertura en Crossref.

OJS publica su punto OAI en la dirección de la revista seguida de /oai.
Los números se reconstruyen a partir del campo dc:source, que OJS rellena
con el volumen, el número y el año, por ejemplo
"Revista X; Vol. 12 Núm. 2 (2023); 45-67".
"""

import datetime
import re
import xml.etree.ElementTree as ET

from comun import (ErrorRed, idioma_de, limpiar_resumen, limpiar_texto, normalizar_idioma,
                   normalizar_licencia, obtener, url_segura)
from crossref import preparar_numero

NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
}
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
MAX_PAGINAS = 15
ANIOS_ATRAS = 3


def candidatos(url_revista):
    """Posibles direcciones OAI de una revista OJS a partir de su web."""
    if not url_revista:
        return []
    base = url_revista.split("?")[0].split("#")[0].rstrip("/")
    lista = []
    ojs = re.match(r"^(https?://.+?/index\.php/[^/]+)", base)
    if ojs:
        lista.append(ojs.group(1) + "/oai")
    lista.append(base + "/oai")
    if "/index.php" not in base:
        lista.append(base + "/index.php/index/oai")
    return list(dict.fromkeys(lista))


def descubrir(url_revista):
    """Devuelve el primer punto OAI que responde a Identify, o None."""
    for candidato in candidatos(url_revista):
        try:
            raiz = ET.fromstring(obtener(candidato, {"verb": "Identify"}, intentos=1, tiempo_espera=25))
        except (ErrorRed, ET.ParseError):
            continue
        if raiz.find("oai:Identify", NS) is not None:
            return candidato
    return None


def textos(metadatos, campo):
    """Lista de (texto, idioma) del campo Dublin Core indicado."""
    return [(limpiar_texto(e.text), e.get(XML_LANG)) for e in metadatos.findall(f"dc:{campo}", NS)
            if e.text and e.text.strip()]


_VOLUMEN = re.compile(r"\b(?:vol(?:umen|ume)?|v)\.?\s*(\d+[A-Za-z]?)", re.I)
_NUMERO = re.compile(r"\b(?:n[úu]m(?:ero)?|no|n[º°o]|nr|issue|n)\.?\s*(\d+(?:\s*[-/]\s*\d+)?|especial|extra\w*)", re.I)
_ANIO = re.compile(r"\((\d{4})\)")


def leer_fuente(fuente):
    """Extrae volumen, número y año de un dc:source de OJS."""
    volumen = _VOLUMEN.search(fuente)
    numero = _NUMERO.search(_VOLUMEN.sub("", fuente))
    anio = _ANIO.search(fuente)
    return (volumen.group(1) if volumen else None,
            re.sub(r"\s+", "", numero.group(1)) if numero else None,
            int(anio.group(1)) if anio else None)


def elegir_por_idioma(lista, idioma_preferido="es"):
    """Escoge el texto en español si existe; si no, el primero."""
    for texto, idioma in lista:
        if normalizar_idioma(idioma) == idioma_preferido:
            return texto, idioma
    return lista[0] if lista else (None, None)


def registro_a_articulo(registro):
    cabecera = registro.find("oai:header", NS)
    if cabecera is None or cabecera.get("status") == "deleted":
        return None
    metadatos = registro.find("oai:metadata/oai_dc:dc", NS)
    if metadatos is None:
        return None
    tipos = " ".join(t for t, _ in textos(metadatos, "type")).lower()
    if tipos and "article" not in tipos and "artículo" not in tipos:
        return None
    titulo, idioma_titulo = elegir_por_idioma(textos(metadatos, "title"))
    if not titulo:
        return None
    resumen, idioma_resumen = elegir_por_idioma(textos(metadatos, "description"))
    resumen = limpiar_resumen(resumen) or None
    identificadores = [t for t, _ in textos(metadatos, "identifier")]
    doi = next((re.sub(r"^https?://(dx\.)?doi\.org/", "", i) for i in identificadores
                if re.match(r"^(https?://(dx\.)?doi\.org/)?10\.\d{4,}/", i)), None)
    enlaces = [url_segura(i) for i in identificadores if url_segura(i) and "doi.org" not in i]
    url = next((e for e in enlaces if "/article/view/" in e), enlaces[0] if enlaces else None)
    if doi and not url:
        url = f"https://doi.org/{doi}"
    if not url:
        return None
    derechos = [t for t, _ in textos(metadatos, "rights")]
    url_licencia = next((d for d in derechos if url_segura(d)), None)
    licencia = normalizar_licencia(url_licencia, None if url_licencia else (derechos[0] if derechos else None))
    idioma_doc = normalizar_idioma(next((t for t, _ in textos(metadatos, "language")), None))
    fuentes = [t for t, _ in textos(metadatos, "source")]
    volumen = numero = anio = None
    for fuente in fuentes:
        volumen, numero, anio = leer_fuente(fuente)
        if volumen or numero:
            break
    if not anio:
        fechas = [t for t, _ in textos(metadatos, "date")]
        if fechas and re.match(r"^\d{4}", fechas[0]):
            anio = int(fechas[0][:4])
    fecha = next((t for t, _ in textos(metadatos, "date")), None)
    return {
        "volumen": volumen, "numero": numero, "anio": anio, "fecha": fecha,
        "articulo": {
            "id": doi or cabecera.findtext("oai:identifier", default=url, namespaces=NS),
            "titulo": titulo,
            "idioma_titulo": idioma_de(titulo, idioma_titulo or idioma_doc, minimo_palabras=5),
            "autores": [{"nombre": n, "orcid": None} for n, _ in textos(metadatos, "creator")],
            "resumen": resumen,
            "idioma_resumen": idioma_de(resumen, idioma_resumen or idioma_doc) if resumen else None,
            "licencia": licencia,
            "url": url,
            "doi": doi,
            "paginas": None,
            "fuente": "OAI-PMH",
        },
    }


def agrupar(registros, cantidad=3):
    grupos = {}
    for datos in registros:
        if not datos or not (datos["volumen"] or datos["numero"] or datos["anio"]):
            continue
        clave = (datos["volumen"], datos["numero"], datos["anio"])
        grupo = grupos.setdefault(clave, {"volumen": datos["volumen"], "numero": datos["numero"],
                                          "anio": datos["anio"], "fecha": datos["fecha"], "articulos": []})
        if datos["fecha"] and (not grupo["fecha"] or datos["fecha"] > grupo["fecha"]):
            grupo["fecha"] = datos["fecha"]
        if all(a["id"] != datos["articulo"]["id"] for a in grupo["articulos"]):
            grupo["articulos"].append(datos["articulo"])

    def numero(texto):
        encontrado = re.search(r"\d+", texto or "")
        return int(encontrado.group()) if encontrado else 0

    recientes = sorted(grupos.values(), reverse=True,
                       key=lambda g: (g["anio"] or 0, numero(g["volumen"]), numero(g["numero"])))[:cantidad]
    return [preparar_numero(g, "OAI-PMH") for g in recientes]


def ultimos_numeros(url_revista, cantidad=3):
    """Devuelve (punto OAI, números) o (None, []) si no hay OAI disponible."""
    punto = descubrir(url_revista)
    if not punto:
        return None, []
    desde = (datetime.date.today() - datetime.timedelta(days=365 * ANIOS_ATRAS)).isoformat()
    parametros = {"verb": "ListRecords", "metadataPrefix": "oai_dc", "from": desde}
    registros = []
    for _ in range(MAX_PAGINAS):
        raiz = ET.fromstring(obtener(punto, parametros))
        error = raiz.find("oai:error", NS)
        if error is not None:
            if error.get("code") == "noRecordsMatch":
                break
            raise ErrorRed(f"OAI-PMH respondió con error {error.get('code')}: {error.text}")
        lista = raiz.find("oai:ListRecords", NS)
        if lista is None:
            break
        registros.extend(registro_a_articulo(r) for r in lista.findall("oai:record", NS))
        testigo = lista.findtext("oai:resumptionToken", default="", namespaces=NS).strip()
        if not testigo:
            break
        parametros = {"verb": "ListRecords", "resumptionToken": testigo}
    return punto, agrupar(registros, cantidad)
