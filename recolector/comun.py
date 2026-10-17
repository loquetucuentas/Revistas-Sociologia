"""Utilidades compartidas por el recolector: red, limpieza de texto,
licencias, detección de idioma y escritura de los archivos de datos.

Solo usa la biblioteca estándar de Python para que el script funcione
sin instalar nada, tanto en local como en GitHub Actions.
"""

import html
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

VERSION_DATOS = 1
CONTACTO = os.environ.get("CONTACTO_EMAIL", "").strip()
AGENTE = "RevistasSociologia/1.0 (+https://github.com/loquetucuentas/Revistas-Sociologia"
AGENTE += f"; mailto:{CONTACTO})" if CONTACTO else ")"

# Pausa mínima entre peticiones al mismo servidor, en segundos.
PAUSA = float(os.environ.get("RECOLECTOR_PAUSA", "1.0"))
_ultima_peticion = {}


class ErrorRed(Exception):
    """Fallo de red o respuesta HTTP no satisfactoria."""

    def __init__(self, mensaje, estado=None):
        super().__init__(mensaje)
        self.estado = estado


def obtener(url, parametros=None, intentos=3, tiempo_espera=40):
    """Descarga una URL y devuelve el cuerpo como bytes.

    Reintenta con espera exponencial ante errores temporales (429 y 5xx)
    y respeta una pausa entre peticiones al mismo servidor.
    """
    if parametros:
        url = f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode(parametros)}"
    servidor = urllib.parse.urlsplit(url).netloc
    for intento in range(intentos):
        espera = PAUSA - (time.monotonic() - _ultima_peticion.get(servidor, 0))
        if espera > 0:
            time.sleep(espera)
        _ultima_peticion[servidor] = time.monotonic()
        peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE})
        try:
            with urllib.request.urlopen(peticion, timeout=tiempo_espera) as respuesta:
                return respuesta.read()
        except urllib.error.HTTPError as error:
            if error.code in (429, 500, 502, 503, 504) and intento < intentos - 1:
                time.sleep(2 ** (intento + 1))
                continue
            raise ErrorRed(f"HTTP {error.code} en {url}", error.code) from error
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if intento < intentos - 1:
                time.sleep(2 ** (intento + 1))
                continue
            raise ErrorRed(f"Sin conexión con {url}: {error}") from error
    raise ErrorRed(f"No se pudo descargar {url}")


def obtener_json(url, parametros=None):
    return json.loads(obtener(url, parametros).decode("utf-8"))


# Texto

_ETIQUETAS = re.compile(r"<[^>]+>")
_ESPACIOS = re.compile(r"\s+")
_ENCABEZADO_RESUMEN = re.compile(r"^(resumen|abstract|resumo|résumé|resum)\s*[:.]?\s+", re.I)


def limpiar_texto(texto):
    """Quita etiquetas HTML o JATS, decodifica entidades y normaliza espacios."""
    if not texto:
        return ""
    texto = re.sub(r"</(jats:)?(p|sec|title)>", " ", texto)
    texto = _ETIQUETAS.sub("", texto)
    texto = html.unescape(texto)
    return _ESPACIOS.sub(" ", texto).strip()


def limpiar_resumen(texto):
    texto = limpiar_texto(texto)
    return _ENCABEZADO_RESUMEN.sub("", texto)


def sin_tildes(texto):
    forma = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in forma if unicodedata.category(c) != "Mn").lower()


def slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes(texto)).strip("-") or "sin-titulo"


def url_segura(url):
    """Devuelve la URL solo si usa http o https."""
    if url and re.match(r"^https?://", url.strip(), re.I):
        return url.strip()
    return None


# Licencias

def normalizar_licencia(url=None, nombre=None):
    """Convierte una URL o un nombre de licencia en {nombre, url}."""
    url = url_segura(url)
    if url:
        cc = re.search(r"creativecommons\.org/(licenses|publicdomain)/([a-z-]+)/(\d\.\d)?", url, re.I)
        if cc:
            tipo, codigo, version = cc.group(1), cc.group(2).lower(), cc.group(3)
            if tipo == "publicdomain":
                etiqueta = "CC0" if codigo == "zero" else "Dominio público"
            else:
                etiqueta = "CC " + codigo.upper()
            if version:
                etiqueta += " " + version
            return {"nombre": etiqueta, "url": url}
    if nombre:
        nombre = limpiar_texto(nombre)
        cc = re.match(r"^cc[ -]?(by(?:[ -](?:nc|sa|nd))*)\s*(\d\.\d)?", nombre, re.I)
        if cc:
            etiqueta = "CC " + cc.group(1).upper().replace(" ", "-")
            if cc.group(2):
                etiqueta += " " + cc.group(2)
            return {"nombre": etiqueta, "url": url}
        return {"nombre": nombre[:120], "url": url}
    if url:
        return {"nombre": "Ver licencia en la web de origen", "url": url}
    return None


# Idioma

_PALABRAS = {
    "es": "el la los las de del que y en un una por con para es se no al lo como más su sus entre sobre este esta desde también fue han ser son".split(),
    "en": "the of and to in a is that for on with as by are this from be an which or at it its their between has have was were these".split(),
    "pt": "o a os as de do da dos das que e em um uma por com para é não ao como mais seu sua entre sobre este esta também foi são".split(),
    "ca": "el la els les de del que i en un una per amb és no al com més seu seva entre sobre aquest aquesta també va són dels".split(),
    "fr": "le la les de des du que et en un une par pour est ne pas au comme plus son sa entre sur ce cette aussi été sont dans".split(),
}
_PALABRAS = {idioma: set(lista) for idioma, lista in _PALABRAS.items()}
_SENALES = {
    "es": ("ción", "ñ", " los ", " del "),
    "pt": ("ção", "ões", " não ", "ã"),
    "ca": ("ció ", " amb ", "l·l", " els "),
    "fr": (" les ", " des ", "è", " est "),
    "en": (" the ", " and ", "ing "),
}


def detectar_idioma(texto, minimo_palabras=6):
    """Estima el idioma de un texto con una lista de palabras frecuentes.

    Solo devuelve un código cuando el resultado es claro. Si el texto es
    corto o mezcla idiomas, devuelve None y la interfaz hereda el idioma
    de la página. Un idioma mal marcado hace que VoiceOver lea peor que
    si no se marca.
    """
    if not texto:
        return None
    minusculas = " " + texto.lower() + " "
    palabras = re.findall(r"[a-zà-ÿ·']+", minusculas)
    if len(palabras) < minimo_palabras:
        return None
    puntos = {}
    for idioma, frecuentes in _PALABRAS.items():
        puntos[idioma] = sum(1 for p in palabras if p in frecuentes)
        puntos[idioma] += sum(2 for s in _SENALES[idioma] if s in minusculas)
    orden = sorted(puntos.items(), key=lambda par: par[1], reverse=True)
    (primero, a), (_, b) = orden[0], orden[1]
    if a < 3 or a < b * 1.6:
        return None
    return primero


def normalizar_idioma(codigo):
    """Devuelve un código ISO 639-1 en minúsculas a partir de formas habituales."""
    if not codigo:
        return None
    codigo = codigo.strip().lower().replace("_", "-")
    equivalencias = {
        "spa": "es", "esp": "es", "spanish": "es", "español": "es", "castellano": "es",
        "eng": "en", "english": "en", "inglés": "en",
        "por": "pt", "portuguese": "pt", "português": "pt",
        "cat": "ca", "catalan": "ca", "català": "ca",
        "fra": "fr", "fre": "fr", "french": "fr", "français": "fr",
        "eus": "eu", "baq": "eu", "glg": "gl", "ita": "it", "deu": "de", "ger": "de",
    }
    codigo = equivalencias.get(codigo, codigo)
    base = codigo.split("-")[0]
    return base if re.fullmatch(r"[a-z]{2}", base) else None


def idioma_de(texto, declarado=None, minimo_palabras=6):
    """Prioriza el idioma declarado por la fuente; si no hay, lo estima."""
    return normalizar_idioma(declarado) or detectar_idioma(texto, minimo_palabras)


# Escritura

def escribir_datos(carpeta, ruta_relativa, contenido):
    """Escribe un JSON y su copia en JavaScript.

    La copia .js permite abrir index.html con doble clic (protocolo file),
    donde el navegador no deja leer JSON locales con fetch.
    """
    ruta = os.path.join(carpeta, ruta_relativa)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    texto = json.dumps(contenido, ensure_ascii=False, indent=1, sort_keys=False)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(texto + "\n")
    clave = json.dumps(ruta_relativa.replace(os.sep, "/"))
    with open(ruta[: -len(".json")] + ".js", "w", encoding="utf-8") as archivo:
        archivo.write("// Copia de " + ruta_relativa + " para abrir la aplicación sin servidor.\n")
        archivo.write("(window.DATOS_REVISTAS = window.DATOS_REVISTAS || {})[" + clave + "] = ")
        archivo.write(texto + ";\n")
