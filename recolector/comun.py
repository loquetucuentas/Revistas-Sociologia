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
# Dirección de contacto del responsable del proyecto, para que cualquier
# servidor sepa a quién escribir. Se puede cambiar con CONTACTO_EMAIL.
CONTACTO = os.environ.get("CONTACTO_EMAIL", "").strip() or "loquetucuentas@gmail.com"
AGENTE = (f"RevistasSociologia/1.1 (+https://github.com/loquetucuentas/Revistas-Sociologia; "
          f"mailto:{CONTACTO})")

# Pausa mínima entre peticiones al mismo servidor, en segundos.
PAUSA = max(2.0, float(os.environ.get("RECOLECTOR_PAUSA", "2.0")))
_ultima_peticion = {}


class ErrorRed(Exception):
    """Fallo de red o respuesta HTTP no satisfactoria."""

    def __init__(self, mensaje, estado=None, dominio=None, bloqueado=False):
        super().__init__(mensaje)
        self.estado = estado
        self.dominio = dominio
        # True cuando la política de red del entorno no deja salir hacia ese dominio.
        self.bloqueado = bloqueado


def es_bloqueo_de_red(error):
    """Detecta el rechazo del proxy del entorno (CONNECT con respuesta 403)."""
    motivo = str(getattr(error, "reason", error))
    return "Tunnel connection failed: 403" in motivo


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
            raise ErrorRed(f"HTTP {error.code} en {url}", error.code, dominio=servidor) from error
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if es_bloqueo_de_red(error):
                # Reintentar no sirve: el dominio no está en la lista de permitidos.
                raise ErrorRed(f"La red del entorno no permite conectar con {servidor} "
                               f"({getattr(error, 'reason', error)})", dominio=servidor, bloqueado=True) from error
            if intento < intentos - 1:
                time.sleep(2 ** (intento + 1))
                continue
            raise ErrorRed(f"Sin conexión con {url}: {error}", dominio=servidor) from error
    raise ErrorRed(f"No se pudo descargar {url}")


def obtener_json(url, parametros=None, intentos=3):
    """Descarga y decodifica JSON; una respuesta cortada se vuelve a pedir."""
    for intento in range(intentos):
        try:
            return json.loads(obtener(url, parametros).decode("utf-8"))
        except ValueError as error:
            if intento == intentos - 1:
                raise ErrorRed(f"Respuesta JSON no válida desde {url}: {error}") from error
            time.sleep(2 ** (intento + 1))


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
    """Limpia un resumen y descarta los que solo contienen un encabezado o un signo."""
    texto = _ENCABEZADO_RESUMEN.sub("", limpiar_texto(texto))
    if len(re.findall(r"\w+", texto)) < 3:
        return ""
    return texto


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

# Palabras frecuentes de cada idioma. Las compartidas entre varios idiomas
# (de, en, la, a...) puntúan para todos y no inclinan la balanza; las
# propias de un solo idioma (y, los, do, em, et, the...) son las que deciden.
_PALABRAS = {
    "es": "a el la los las de del que y en un una unos unas por con para es se no al lo como más su sus "
          "entre sobre este esta estos estas desde también fue han ser son hacia según durante sin "
          "muy pero cuando donde le les ante tras mediante cual cuales sí otro otra nuevo nueva",
    "pt": "o a os as de do da dos das que e em um uma por com para é se não ao aos à às como mais seu sua "
          "seus suas entre sobre este esta também foi são pelo pela pelos pelas nos na nas no ou muito "
          "quando onde durante sem mas novo nova através estudo",
    "ca": "a el la els les de del dels que i en un una per amb és es no al als com més seu seva seus "
          "seves entre sobre aquest aquesta també va són pel pels sense però quan on nou nova cap",
    "fr": "à le la les de des du que et en un une par pour est se ne pas au aux comme plus son sa ses "
          "entre sur ce cette ces aussi été sont dans qui leur leurs sans mais quand où nouveau nouvelle",
    "it": "a il lo la i gli le di del della dei degli delle che e in un una per con è si non al alla come "
          "più suo sua suoi tra fra su questo questa anche stato sono nel nella nei nelle sul sulla "
          "senza ma quando dove nuovo nuova",
    "en": "the of and to in a is that for on with as by are this from be an which or at it its their "
          "between has have was were these how what among through toward towards new study",
    # En polaco se omiten «o», «do», «na» o «i», que coinciden con otros idiomas
    # y confundían títulos portugueses; los diacríticos ya lo identifican bien.
    "pl": "w z się nie jest oraz od dla przez że jako czy ich jej jego ale lub także być są który która "
          "które ze we wobec przy między wśród",
}
_PALABRAS = {idioma: set(lista.split()) for idioma, lista in _PALABRAS.items()}
# Peso de cada palabra según en cuántos idiomas aparece: 2,5 si es propia de
# uno solo, 1,5 si la comparten dos (como «e» en portugués e italiano) y 0,5
# si es común a tres o más.
_PESOS = {}
for _palabra in set().union(*_PALABRAS.values()):
    _veces = sum(_palabra in lista for lista in _PALABRAS.values())
    _PESOS[_palabra] = 2.5 if _veces == 1 else 1.5 if _veces == 2 else 0.5
# Rasgos ortográficos característicos, con su peso.
_SENALES = {
    "es": [(r"ción\b|ciones\b", 2), (r"ñ", 2), (r"[¿¡]", 3), (r"dad\b|dades\b", 1)],
    "pt": [(r"ção\b|ções\b", 3), (r"[ãõ]", 3), (r"\w(lh|nh)\w", 1), (r"dade\b|dades\b", 1),
           (r"ência\b|ências\b|ância\b", 2), (r"[êô]", 1)],
    "ca": [(r"l·l", 4), (r"ció\b|cions\b", 2), (r"\b[ld]['’]\w", 1), (r"[àèò]\w", 1)],
    "fr": [(r"\b(l|d|qu|n|s|c|j)['’]\w", 2), (r"eau\b|eaux\b", 2), (r"[èêëç]", 1), (r"tion\b|tions\b", 1)],
    "it": [(r"zione\b|zioni\b", 3), (r"\b(gli|della|delle|degli|nella|nelle)\b", 1), (r"tà\b", 2)],
    "en": [(r"\b\w+ing\b", 1), (r"\b\w+ly\b", 1), (r"th", 1), (r"tion\b|tions\b", 0.5)],
    "pl": [(r"[ąęłśżźćń]", 2), (r"ość\b|ości\b", 2), (r"(cz|sz|rz|wy|ów)", 1)],
}


def puntuar_idiomas(texto):
    """Devuelve (puntos por idioma, número de palabras) de un texto."""
    minusculas = texto.lower()
    palabras = re.findall(r"[a-zà-ÿ·ąęłśżźćń]+", minusculas)
    puntos = {}
    for idioma, frecuentes in _PALABRAS.items():
        total = sum(_PESOS[p] for p in palabras if p in frecuentes)
        for patron, peso in _SENALES[idioma]:
            total += peso * min(len(re.findall(patron, minusculas)), 6)
        puntos[idioma] = total
    return puntos, len(palabras)


def detectar_idioma(texto, minimo_palabras=3):
    """Estima el idioma de un texto con palabras frecuentes y rasgos ortográficos.

    Solo devuelve un código cuando el resultado es claro. Si el texto es
    corto o mezcla idiomas, devuelve None y la interfaz hereda el idioma
    de la página. Un idioma mal marcado hace que VoiceOver lea peor que
    si no se marca.
    """
    if not texto:
        return None
    puntos, cantidad = puntuar_idiomas(texto)
    if cantidad < minimo_palabras:
        return None
    orden = sorted(puntos.items(), key=lambda par: par[1], reverse=True)
    (primero, a), (_, b) = orden[0], orden[1]
    # Hace falta una ventaja clara en valor absoluto y en proporción.
    if a < 2.5 or a - b < 2 or a < b * 1.4:
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


def idioma_de(texto, declarado=None, minimo_palabras=3):
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
