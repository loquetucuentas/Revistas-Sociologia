"""Paso 2 del texto completo: descarga respetuosa y conversión.

Reglas de recolección:
1. User-Agent con el nombre del proyecto y la dirección de contacto (comun.AGENTE).
2. Se lee robots.txt de cada servidor y no se pide nada que prohíba. Si no se
   puede leer por un error del servidor o de la red, no se consulta ese servidor.
3. Al menos dos segundos entre peticiones a un mismo servidor.
4. Peticiones condicionales (ETag y Last-Modified) y resumen del contenido:
   lo que no ha cambiado no se vuelve a descargar ni a convertir.
5. Ante 429 o 503 se deja de consultar ese servidor el resto de la ejecución.
6. No se reintenta de forma insistente, no se cambia de identidad y no se
   intenta sortear ningún bloqueo. Las redirecciones se siguen a mano para
   comprobar robots.txt también en el destino.
7. Nunca se descarga ni se usa un PDF.
"""

import datetime
import gzip
import hashlib
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

import licencias
import saneado
from comun import AGENTE, PAUSA, escribir_datos, es_bloqueo_de_red, idioma_de, normalizar_idioma, slug

MAX_REDIRECCIONES = 4
MAX_BYTES = 8 * 1024 * 1024
TIEMPO_ESPERA = 40
VERSION_TEXTOS = 1


class Detenido(Exception):
    """El servidor pide que se reduzca el tráfico o no permite la petición."""

    def __init__(self, motivo, dominio, tipo="servidor"):
        super().__init__(motivo)
        self.motivo = motivo
        self.dominio = dominio
        # servidor, limite, red, robots o pdf
        self.tipo = tipo


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *argumentos, **opciones):
        return None


_abridor = urllib.request.build_opener(_SinRedirecciones)


class Cliente:
    """Cliente HTTP respetuoso: robots.txt, pausas, condicionales y parada ante límites."""

    def __init__(self, cache):
        self.cache = cache            # url -> {etag, modificado, sha256}
        self.robots = {}              # dominio -> RobotFileParser o False
        self.ultima = {}              # dominio -> instante de la última petición
        self.detenidos = {}           # dominio -> motivo
        self.tipos = {}               # dominio -> tipo de detención
        self.peticiones = 0

    def _esperar(self, dominio):
        espera = PAUSA - (time.monotonic() - self.ultima.get(dominio, -1e9))
        if espera > 0:
            time.sleep(espera)
        self.ultima[dominio] = time.monotonic()

    def _pedir(self, url, cabeceras):
        dominio = urllib.parse.urlsplit(url).netloc.lower()
        if dominio in self.detenidos:
            raise Detenido(self.detenidos[dominio], dominio, self.tipos.get(dominio, "servidor"))
        self._esperar(dominio)
        self.peticiones += 1
        peticion = urllib.request.Request(url, headers=dict({"User-Agent": AGENTE, "Accept-Encoding": "gzip"},
                                                             **cabeceras))
        try:
            respuesta = _abridor.open(peticion, timeout=TIEMPO_ESPERA)
            return respuesta.status, respuesta.headers, self._leer(respuesta)
        except urllib.error.HTTPError as error:
            if error.code in (429, 503):
                motivo = f"El servidor ha respondido {error.code} (limitación de tráfico o servicio no disponible)"
                if error.headers.get("Retry-After"):
                    motivo += f"; pide esperar {error.headers['Retry-After']}"
                self.detenidos[dominio] = motivo + ". No se le hacen más peticiones en esta ejecución."
                self.tipos[dominio] = "limite"
                raise Detenido(self.detenidos[dominio], dominio, "limite") from error
            if error.code in (401, 403) and not url.endswith("/robots.txt"):
                self.detenidos[dominio] = (f"El servidor ha denegado el acceso (respuesta {error.code}). "
                                           "No se le hacen más peticiones en esta ejecución.")
                self.tipos[dominio] = "denegado"
                raise Detenido(self.detenidos[dominio], dominio, "denegado") from error
            return error.code, error.headers, b""
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if es_bloqueo_de_red(error):
                tipo, motivo = "red", "La red del entorno no permite este dominio."
            elif isinstance(getattr(error, "reason", None), ssl.SSLCertVerificationError):
                # Nunca se desactiva la verificación: el servidor queda pendiente.
                tipo = "tls"
                motivo = ("El certificado de seguridad del servidor no se puede verificar "
                          f"({error.reason.verify_message}); no se desactiva la verificación.")
            else:
                tipo, motivo = "servidor", f"Sin conexión con el servidor: {getattr(error, 'reason', error)}."
            self.tipos[dominio] = tipo
            self.detenidos[dominio] = motivo
            raise Detenido(self.detenidos[dominio], dominio, tipo) from error

    @staticmethod
    def _leer(respuesta):
        datos = respuesta.read(MAX_BYTES + 1)
        if len(datos) > MAX_BYTES:
            raise Detenido("La respuesta supera el tamaño máximo admitido.", urllib.parse.urlsplit(respuesta.url).netloc)
        if (respuesta.headers.get("Content-Encoding") or "").lower() == "gzip":
            datos = gzip.decompress(datos)
        return datos

    def permitido(self, url):
        partes = urllib.parse.urlsplit(url)
        dominio = partes.netloc.lower()
        if dominio not in self.robots:
            robots_url = f"{partes.scheme}://{partes.netloc}/robots.txt"
            estado, _, cuerpo = self._pedir(robots_url, {})
            lector = urllib.robotparser.RobotFileParser()
            if estado == 200:
                lector.parse(cuerpo.decode("utf-8", "replace").splitlines())
                self.robots[dominio] = lector
            elif estado in (404, 410):
                lector.parse([])          # sin robots.txt: todo permitido
                self.robots[dominio] = lector
            else:
                # 401, 403, errores del servidor u otras respuestas: no se consulta.
                self.robots[dominio] = False
                self.detenidos[dominio] = f"No se ha podido leer robots.txt (respuesta {estado}); no se consulta el servidor."
                self.tipos[dominio] = "robots"
        lector = self.robots[dominio]
        return bool(lector) and lector.can_fetch(AGENTE, url)

    def obtener(self, url):
        """Descarga una URL. Devuelve (url final, tipo, cuerpo o None si no ha cambiado)."""
        for _ in range(MAX_REDIRECCIONES + 1):
            # Se usa siempre https: es la misma página por una conexión cifrada.
            if url.lower().startswith("http://"):
                url = "https://" + url[len("http://"):]
            if url.lower().split("?")[0].endswith(".pdf"):
                raise Detenido("El enlace lleva a un PDF; no se usa.", "", "pdf")
            if not self.permitido(url):
                dominio = urllib.parse.urlsplit(url).netloc.lower()
                raise Detenido(self.detenidos.get(dominio) or "robots.txt no permite descargar esta página.", dominio, "robots")
            anterior = self.cache.get(url, {})
            cabeceras = {}
            if anterior.get("etag"):
                cabeceras["If-None-Match"] = anterior["etag"]
            if anterior.get("modificado"):
                cabeceras["If-Modified-Since"] = anterior["modificado"]
            estado, encabezados, cuerpo = self._pedir(url, cabeceras)
            if estado in (301, 302, 303, 307, 308) and encabezados.get("Location"):
                url = urllib.parse.urljoin(url, encabezados["Location"])
                continue
            tipo = (encabezados.get("Content-Type") or "").split(";")[0].strip().lower()
            if estado == 304:
                return url, anterior.get("tipo", tipo), None
            if estado != 200:
                raise Detenido(f"La página ha respondido con el código {estado}.", urllib.parse.urlsplit(url).netloc)
            if tipo == "application/pdf" or cuerpo[:5] == b"%PDF-":
                raise Detenido("El enlace lleva a un PDF; no se usa.", "", "pdf")
            resumen = hashlib.sha256(cuerpo).hexdigest()
            cambiado = resumen != anterior.get("sha256")
            self.cache[url] = {"etag": encabezados.get("ETag"), "modificado": encabezados.get("Last-Modified"),
                               "sha256": resumen, "tipo": tipo}
            return url, tipo, cuerpo if cambiado else None
        raise Detenido("Demasiadas redirecciones.", urllib.parse.urlsplit(url).netloc)


def decodificar(cuerpo):
    for codificacion in re.findall(rb'charset=["\']?([A-Za-z0-9_-]+)', cuerpo[:2048])[:1] + [b"utf-8"]:
        try:
            return cuerpo.decode(codificacion.decode("ascii"))
        except (LookupError, UnicodeDecodeError):
            continue
    return cuerpo.decode("utf-8", "replace")


# Lectura de la página del artículo

def _atributo_clase(nodo):
    return " " + (nodo[1].get("class") or "") + " "


def _todos(nodo, condicion, lista=None):
    lista = [] if lista is None else lista
    if isinstance(nodo, list):
        if condicion(nodo):
            lista.append(nodo)
        for hijo in nodo[2:]:
            _todos(hijo, condicion, lista)
    return lista


def leer_pagina(texto, url):
    """Extrae de la página del artículo las galeradas, las licencias y los avisos de derechos."""
    raiz = saneado.leer_html(texto)
    galeradas, licencias_pagina, avisos = [], [], []
    for enlace in _todos(raiz, lambda n: n[0] == "a" and n[1].get("href")):
        etiqueta = re.sub(r"\s+", " ", saneado.texto_html(enlace)).strip()
        clase = _atributo_clase(enlace)
        href = urllib.parse.urljoin(url, enlace[1]["href"])
        if "license" in (enlace[1].get("rel") or "").split():
            licencias_pagina.append(href)
        es_galerada = " obj_galley_link " in clase or " galley_link " in clase or "/article/view/" in href
        if es_galerada and re.fullmatch(r"(?i)(html|xml|jats|jats xml|texto completo html|html \(.*\)|xml \(.*\))", etiqueta):
            formato = "xml" if re.match(r"(?i)xml|jats", etiqueta) else "html"
            galeradas.append({"url": href, "formato": formato, "etiqueta": etiqueta})
    for meta in _todos(raiz, lambda n: n[0] in ("meta", "link")):
        nombre = (meta[1].get("name") or meta[1].get("property") or "").lower()
        if nombre in ("dc.rights", "dcterms.rights", "dc.rights.license", "dcterms.license"):
            contenido = meta[1].get("content") or ""
            (licencias_pagina if re.match(r"^https?://", contenido) else avisos).append(contenido)
        if meta[0] == "link" and "license" in (meta[1].get("rel") or "").split() and meta[1].get("href"):
            licencias_pagina.append(meta[1]["href"])
        if nombre in ("citation_fulltext_html_url",) and meta[1].get("content"):
            galeradas.append({"url": urllib.parse.urljoin(url, meta[1]["content"]), "formato": "html",
                              "etiqueta": "citation_fulltext_html_url"})
        if nombre in ("citation_xml_url",) and meta[1].get("content"):
            galeradas.append({"url": urllib.parse.urljoin(url, meta[1]["content"]), "formato": "xml",
                              "etiqueta": "citation_xml_url"})
    # Bloque de derechos de OJS: se conserva su texto tal cual.
    for bloque in _todos(raiz, lambda n: " copyright " in _atributo_clase(n) or " item copyright " in _atributo_clase(n)):
        texto_bloque = re.sub(r"\s+", " ", saneado.texto_html(bloque)).strip()
        if texto_bloque:
            avisos.append(texto_bloque)
    vistas = set()
    unicas = [g for g in galeradas if not (g["url"] in vistas or vistas.add(g["url"]))]
    # Primero XML JATS y después HTML.
    unicas.sort(key=lambda g: g["formato"] != "xml")
    return unicas, list(dict.fromkeys(licencias_pagina)), list(dict.fromkeys(avisos))


def contenedor_html(texto, url):
    """Devuelve (nodo con el texto del artículo, plataforma, lang) o lanza NoConvertible.

    Solo se aceptan estructuras conocidas: el archivo de una galerada HTML de
    OJS (su body entero es el artículo) y las páginas de OpenEdition.
    """
    raiz = saneado.leer_html(texto)
    html_nodo = saneado.buscar(raiz, lambda n: n[0] == "html")
    idioma = normalizar_idioma((html_nodo or ["", {}])[1].get("lang") or (html_nodo or ["", {}])[1].get("xml:lang"))
    marco = saneado.buscar(raiz, lambda n: n[0] == "iframe" and (
        n[1].get("id") == "htmlGalleyFrame" or (n[1].get("name") or "") in ("htmlFrame", "htmlGalleyFrame")))
    if marco is not None:
        return None, "ojs-visor", urllib.parse.urljoin(url, (marco[1].get("src") or "").strip())
    if "openedition.org" in url:
        partes = [saneado.buscar(raiz, lambda n, i=i: n[1].get("id") == i) for i in ("text", "notes", "bibliography", "appendix")]
        partes = [p for p in partes if p is not None]
        if not partes or partes[0][1].get("id") != "text":
            raise saneado.NoConvertible("No se encuentra el texto del artículo en la página de OpenEdition.")
        return ["#raiz", {}] + partes, "openedition", idioma
    if "/article/download/" in url:
        # El archivo de la galerada es el artículo; si no trae body, lo es entero.
        cuerpo = saneado.buscar(raiz, lambda n: n[0] == "body") or raiz
        if not saneado.texto_html(cuerpo).strip():
            raise saneado.NoConvertible("La galerada HTML está vacía.")
        return cuerpo, "ojs-galerada", idioma
    raise saneado.NoConvertible("No se reconoce la estructura de la página HTML; no se puede asegurar qué parte es el artículo.")


def descargar_texto(cliente, galerada):
    """Descarga una galerada o enlace de texto completo. Devuelve (formato, url, cuerpo, plataforma)."""
    url = galerada["url"]
    if galerada["formato"] == "xml" and "/article/view/" in url:
        url = url.replace("/article/view/", "/article/download/")
    url_final, tipo, cuerpo = cliente.obtener(url)
    return url_final, tipo, cuerpo


# Paso completo

def ruta_texto(doi):
    return f"textos/{slug(doi)[:120]}.json"


def paso_textos(carpeta):
    from texto_completo import articulos_de, ahora, escribir_json, leer_json  # evita dependencia circular

    estado_ruta = os.path.join(carpeta, "textos", "estado.json")
    estado = leer_json(estado_ruta)
    if not estado:
        raise SystemExit("Falta data/textos/estado.json: ejecuta antes el paso de metadatos.")
    cliente = Cliente(estado.setdefault("cache", {}))
    articulos = {a["doi"].lower(): (r, n, a) for r, n, a in articulos_de(carpeta)}

    # Se reparten los artículos por dominio y se intercalan, para que la pausa
    # por servidor no alargue la ejecución sin necesidad.
    colas = {}
    for doi, registro in estado["articulos"].items():
        if registro.get("apta") and doi in articulos and registro.get("pagina"):
            colas.setdefault(urllib.parse.urlsplit(registro["pagina"]).netloc.lower(), []).append(doi)
    orden = []
    while any(colas.values()):
        for dominio in list(colas):
            if colas[dominio]:
                orden.append(colas[dominio].pop(0))

    for posicion, doi in enumerate(orden, 1):
        registro = estado["articulos"][doi]
        revista, numero, articulo = articulos[doi]
        print(f"[{posicion}/{len(orden)}] {doi}", flush=True)
        registro["resultado"] = procesar(cliente, carpeta, registro, revista, numero, articulo, ahora())
        if posicion % 20 == 0:
            escribir_json(estado_ruta, estado)
    estado["textos_actualizados"] = ahora()
    estado["dominios_detenidos"] = cliente.detenidos
    escribir_json(estado_ruta, estado)
    print(f"Peticiones a webs de revistas: {cliente.peticiones}.")


def procesar(cliente, carpeta, registro, revista, numero, articulo, fecha):
    """Intenta obtener el texto de un artículo. Devuelve {estado, motivo, ...}."""
    archivo = ruta_texto(articulo["doi"])
    ruta = os.path.join(carpeta, archivo)
    try:
        url_pagina, _, cuerpo = cliente.obtener(registro["pagina"])
        if cuerpo is None and os.path.exists(ruta) and registro.get("resultado", {}).get("estado") == "disponible":
            return dict(registro["resultado"], comprobado=fecha)
        if cuerpo is None:
            # La página no ha cambiado pero no hay texto previo: se vuelve a pedir entera.
            cliente.cache.pop(registro["pagina"], None)
            url_pagina, _, cuerpo = cliente.obtener(registro["pagina"])
        galeradas, licencias_pagina, avisos = leer_pagina(decodificar(cuerpo), url_pagina)
        motivo = licencias.contradice(registro["licencia"], licencias_pagina, avisos)
        if motivo:
            return {"estado": "excluido", "motivo": motivo, "detalle": "Licencias en la página: " +
                    (", ".join(licencias_pagina) or "ninguna") + "."}
        for enlace in registro.get("enlaces") or []:
            if enlace["tipo"] in ("text/xml", "application/xml", "application/jats+xml"):
                galeradas.insert(0, {"url": enlace["url"], "formato": "xml", "etiqueta": "Crossref"})
            elif enlace["tipo"] in ("text/html", "application/xhtml+xml"):
                galeradas.append({"url": enlace["url"], "formato": "html", "etiqueta": "Crossref"})
        if "journals.openedition.org" in url_pagina:
            # OpenEdition publica el texto completo en la propia página del artículo.
            galeradas.insert(0, {"url": url_pagina, "formato": "html", "etiqueta": "Página de OpenEdition"})
        if not galeradas:
            return {"estado": "sin-texto", "motivo": "solo-pdf"}
        errores = []
        for galerada in galeradas:
            try:
                return convertir_galerada(cliente, carpeta, archivo, galerada, registro, revista, numero,
                                          articulo, avisos, fecha)
            except saneado.NoConvertible as error:
                errores.append(f"{galerada['etiqueta']}: {error}")
            except Detenido as error:
                if error.tipo in ("pdf", "robots"):
                    errores.append(f"{galerada['etiqueta']}: {error.motivo}")
                    continue
                raise
        if errores and all("PDF" in e for e in errores):
            return {"estado": "sin-texto", "motivo": "solo-pdf", "detalle": errores}
        return {"estado": "excluido", "motivo": "no-convertible", "detalle": errores}
    except Detenido as error:
        if error.tipo in ("robots", "denegado"):
            return {"estado": "excluido", "motivo": error.tipo, "detalle": error.motivo, "dominio": error.dominio}
        motivo = {"limite": "limite-trafico", "red": "dominio-no-permitido", "tls": "certificado-tls"}.get(error.tipo, "servidor")
        return {"estado": "pendiente", "motivo": motivo, "detalle": error.motivo, "dominio": error.dominio}


def convertir_galerada(cliente, carpeta, archivo, galerada, registro, revista, numero, articulo, avisos, fecha):
    url, tipo, cuerpo = descargar_texto(cliente, galerada)
    if cuerpo is None and os.path.exists(os.path.join(carpeta, archivo)):
        return dict(registro.get("resultado") or {}, estado="disponible", comprobado=fecha)
    if cuerpo is None:
        cliente.cache.pop(url, None)
        url, tipo, cuerpo = descargar_texto(cliente, galerada)
    licencias_texto, declarado = [], None
    if galerada["formato"] == "xml" or tipo in ("application/xml", "text/xml") or cuerpo.lstrip()[:5] == b"<?xml":
        raiz = saneado.leer_jats(cuerpo)
        declarado = normalizar_idioma(raiz.get(saneado.XML_LANG))
        contenido, avisos_xml, licencias_texto = saneado.convertir_jats(raiz, declarado)
        avisos = list(dict.fromkeys(avisos + avisos_xml))
        formato, plataforma = "XML JATS", "JATS"
    else:
        nodo, plataforma, extra = contenedor_html(decodificar(cuerpo), url)
        if plataforma == "ojs-visor":
            # La vista de OJS muestra la galerada en un marco: se descarga su archivo.
            return convertir_galerada(cliente, carpeta, archivo, {"url": extra, "formato": "html",
                                      "etiqueta": galerada["etiqueta"]}, registro, revista, numero,
                                      articulo, avisos, fecha)
        declarado = extra
        contenido = saneado.convertir_html(nodo, declarado)
        formato = "HTML"
    motivo = licencias.contradice(registro["licencia"], licencias_texto, avisos)
    if motivo:
        return {"estado": "excluido", "motivo": motivo, "detalle": f"Licencia en Crossref: {registro['licencia']['url']}. "
                f"Licencias en el texto de la revista: {', '.join(licencias_texto) or 'ninguna'}."}
    idioma_base = (declarado or idioma_de(saneado.texto_plano(["p", {}] + contenido)[:4000])
                   or articulo.get("idioma_titulo") or "es")
    contenido = saneado.marcar_idiomas(contenido, idioma_base)
    contenido, vueltas = saneado.preparar(contenido)
    saneado.validar(contenido)
    indice = saneado.tabla_de_contenidos(contenido)
    figuras = saneado.contar(contenido, "figura")
    escribir_datos(carpeta, archivo, {
        "version": VERSION_TEXTOS, "recogido": fecha, "doi": articulo["doi"], "titulo": articulo["titulo"],
        "revista": revista["id"], "numero": numero["id"], "licencia": registro["licencia"],
        "fuente": {"url": url, "formato": formato, "plataforma": plataforma, "pagina": registro["pagina"]},
        "autores_cita": registro.get("autores_cita") or [],
        "avisos_derechos": avisos, "idioma_principal": idioma_base, "indice": indice, "vueltas": vueltas,
        "contenido": contenido,
    })
    return {"estado": "disponible", "archivo": archivo, "formato": formato, "figuras": figuras,
            "figuras_sin_descripcion": sum(1 for n in saneado._recorrer(contenido) if n[0] == "figura" and not n[1].get("alt")),
            "comprobado": fecha}
