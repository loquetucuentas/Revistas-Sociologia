#!/usr/bin/env python3
"""Empaqueta la aplicación en un único archivo HTML autocontenido.

Genera dist/revistas-prueba.html con el CSS, el JavaScript y todos los
JSON de la carpeta de datos dentro del propio archivo. Sirve para revisar
la aplicación con VoiceOver sin publicarla: se abre directamente, sin
servidor, y no pide nada a otros archivos ni a internet. Una política de
seguridad de contenido (CSP) en el propio archivo bloquea además cualquier
petición externa.

Si los datos son de prueba (marca es_prueba), se añade el aviso visible
de datos de prueba. En el pie se indican la fecha y hora de generación
de los datos y del paquete.

Con --artefacto se genera además dist/revistas-artefacto.html, la misma
página sin doctype, html, head ni body, para publicarla como artefacto
privado de Claude: el visor añade su propio esqueleto y su propia política
de seguridad, que también bloquea las peticiones externas.

Uso: python3 herramientas/empaquetar.py [--datos data] [--salida dist/revistas-prueba.html] [--artefacto]
Solo usa la biblioteca estándar.
"""

import argparse
import datetime
import glob
import html
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMITE_BYTES = 10 * 1024 * 1024

# Nada puede venir de fuera: solo estilos y scripts incrustados, e imágenes
# en data: (el icono). La conexión, las fuentes y los marcos quedan cerrados.
CSP = ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
       "img-src data:; font-src 'none'; connect-src 'none'; frame-src 'none'; "
       "base-uri 'none'; form-action 'none'")

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

AVISO_PRUEBA_HTML = '''
    <div class="aviso-prueba">
      <p class="contenedor"><strong>Datos de prueba.</strong> Las revistas, números y artículos que ves ahora son ficticios y sirven solo para probar la aplicación. No proceden de DOAJ ni de Crossref.</p>
    </div>
'''

# Contrastes: texto #3d2c00 sobre #fff4cc (12,9 a 1); en oscuro #fff3c4 sobre #3a2f05 (12,6 a 1).
AVISO_PRUEBA_CSS = '''
.aviso-prueba { background: #fff4cc; color: #3d2c00; border-top: 2px solid #8a6500; padding: 0.75rem 0; }
.aviso-prueba p { margin: 0; }
@media (prefers-color-scheme: dark) {
  .aviso-prueba { background: #3a2f05; color: #fff3c4; border-top-color: #e0b83a; }
}
@media (forced-colors: active) {
  .aviso-prueba { border-top: 2px solid CanvasText; }
}
'''


def leer(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return archivo.read()


def fecha_y_hora(iso):
    """Convierte una fecha ISO en «18 de octubre de 2026 a las 05:52 (hora UTC)»."""
    try:
        momento = datetime.datetime.fromisoformat(iso).astimezone(datetime.timezone.utc)
    except (TypeError, ValueError):
        return None
    return f"{momento.day} de {MESES[momento.month - 1]} de {momento.year} a las {momento:%H:%M} (hora UTC)"


def leer_datos(carpeta):
    """Devuelve {ruta relativa: contenido} con todos los JSON que usa la aplicación."""
    datos = {"revistas.json": json.loads(leer(os.path.join(carpeta, "revistas.json")))}
    for ruta in sorted(glob.glob(os.path.join(carpeta, "revistas", "*.json"))):
        datos["revistas/" + os.path.basename(ruta)] = json.loads(leer(ruta))
    # Solo se incluyen las revistas del listado; el resto no se puede abrir.
    archivos = {r.get("archivo") for r in datos["revistas.json"].get("revistas", [])}
    return {clave: valor for clave, valor in datos.items() if clave == "revistas.json" or clave in archivos}


def json_para_script(valor):
    """JSON seguro dentro de <script>: sin «<» que pueda cerrar la etiqueta."""
    texto = json.dumps(valor, ensure_ascii=False, separators=(",", ":"))
    return texto.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def sustituir(texto, viejo, nuevo):
    if viejo not in texto:
        raise SystemExit(f"No se encuentra en index.html el fragmento esperado: {viejo[:60]}")
    return texto.replace(viejo, nuevo, 1)


_TEMA_OSCURO = re.compile(r"@media \(prefers-color-scheme: dark\) \{\s*:root \{(.*?)\}\s*\}", re.S)


def tema_seguro(css):
    """Hace que el tema oscuro siga también una elección explícita del visor.

    Sin atributo data-theme manda el sistema; data-theme="light" o "dark"
    en la raíz, como pone el visor de artefactos, tiene prioridad.
    """
    bloque = _TEMA_OSCURO.search(css)
    if not bloque:
        raise SystemExit("No se encuentra el bloque del tema oscuro en estilos.css.")
    variables = bloque.group(1)
    nuevo = ('@media (prefers-color-scheme: dark) {\n  :root:not([data-theme="light"]) {' + variables + '}\n}\n'
             ':root[data-theme="dark"] {' + variables + '}')
    return css[:bloque.start()] + nuevo + css[bloque.end():]


def a_fragmento(pagina):
    """Quita doctype, html, head y body para el visor de artefactos.

    El visor añade su propio esqueleto, sin idioma, así que un script
    pequeño al principio declara lang="es" en la raíz.
    """
    pagina = re.sub(r"<!doctype html>\s*", "", pagina, flags=re.I)
    pagina = re.sub(r'<html lang="es">\s*', "", pagina)
    pagina = re.sub(r"\s*<meta charset=\"utf-8\">", "", pagina)
    pagina = re.sub(r"\s*<meta name=\"viewport\"[^>]*>", "", pagina)
    pagina = re.sub(r"\s*<meta http-equiv=\"Content-Security-Policy\"[^>]*>", "", pagina)
    pagina = re.sub(r"</?head>\s*|<body>\s*|\s*</body>|\s*</html>\s*", "\n", pagina)
    idioma = "<script>document.documentElement.setAttribute('lang', 'es');</script>\n"
    return idioma + pagina.strip() + "\n"


def empaquetar(carpeta_datos, generado_en=None):
    pagina = leer(os.path.join(RAIZ, "index.html"))
    css = leer(os.path.join(RAIZ, "assets", "estilos.css"))
    js = leer(os.path.join(RAIZ, "assets", "app.js"))
    datos = leer_datos(carpeta_datos)
    listado = datos["revistas.json"]
    es_prueba = bool(listado.get("es_prueba")) or any(d.get("es_prueba") for d in datos.values())
    generado_en = generado_en or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)

    css = tema_seguro(css)
    if es_prueba:
        css += AVISO_PRUEBA_CSS.replace("@media (prefers-color-scheme: dark) {\n  .aviso-prueba",
                                        "@media (prefers-color-scheme: dark) {\n  :root:not([data-theme=\"light\"]) .aviso-prueba")
        css += ':root[data-theme="dark"] .aviso-prueba { background: #3a2f05; color: #fff3c4; border-top-color: #e0b83a; }\n'
    pagina = sustituir(pagina, '<link rel="stylesheet" href="assets/estilos.css">',
                       f'<meta http-equiv="Content-Security-Policy" content="{CSP}">\n'
                       f'  <style>\n{css}\n  </style>')
    pagina = sustituir(pagina, '  <script src="assets/app.js" defer></script>\n', '')
    if es_prueba:
        pagina = sustituir(pagina, '  </header>', AVISO_PRUEBA_HTML.rstrip("\n") + '\n  </header>')

    texto_datos = fecha_y_hora(listado.get("generado")) or "fecha no indicada en los datos"
    origen = "datos de prueba ficticios" if es_prueba else "datos reales de DOAJ y Crossref"
    pie = (f'      <p>Versión de prueba privada en un solo archivo, para revisión. '
           f'Contiene {html.escape(origen)} generados el {html.escape(texto_datos)}. '
           f'Archivo creado el {html.escape(fecha_y_hora(generado_en.isoformat()))}.</p>\n')
    pagina = sustituir(pagina, '      <p id="pie-actualizacion"></p>\n', '      <p id="pie-actualizacion"></p>\n' + pie)

    # El JavaScript va al final del cuerpo: así el DOM ya existe, como con defer.
    js = js.replace("</script", "<\\/script")
    scripts = (f'  <script>window.DATOS_INCRUSTADOS = {json_para_script(datos)};</script>\n'
               f'  <script>\n{js}\n  </script>\n')
    pagina = sustituir(pagina, '</body>', scripts + '</body>')
    return pagina, es_prueba, len(datos) - 1


# Comprobación de que no queda ninguna referencia a recursos externos.

_ETIQUETA = re.compile(r"<(script|link|img|iframe|frame|embed|object|source|audio|video|track|picture|use|image|input)\b[^>]*>", re.I)
_ATRIBUTO_RECURSO = re.compile(r"\b(src|srcset|href|data|poster|background|xlink:href)\s*=\s*([\"'])(.*?)\2", re.I)


def problemas_autocontenido(pagina, exigir_csp=True):
    """Devuelve una lista de referencias a recursos fuera del archivo."""
    problemas = []
    for etiqueta in _ETIQUETA.finditer(pagina):
        for atributo in _ATRIBUTO_RECURSO.finditer(etiqueta.group(0)):
            valor = atributo.group(3).strip()
            if not valor.lower().startswith("data:"):
                problemas.append(f"<{etiqueta.group(1)}> con {atributo.group(1)}=\"{valor[:80]}\"")
    for bloque in re.findall(r"<style[^>]*>(.*?)</style>", pagina, re.S | re.I):
        for url in re.findall(r"url\(\s*['\"]?([^'\")]+)", bloque):
            if not url.strip().lower().startswith("data:"):
                problemas.append(f"CSS url({url[:80]})")
        if re.search(r"@import|@font-face", bloque, re.I):
            problemas.append("CSS con @import o @font-face")
    for atributo in re.findall(r"\sstyle\s*=\s*([\"'])(.*?)\1", pagina, re.S):
        if re.search(r"url\(\s*['\"]?(?!data:)", atributo[1], re.I):
            problemas.append("atributo style con url() externo")
    if exigir_csp and 'http-equiv="Content-Security-Policy"' not in pagina:
        problemas.append("falta la política de seguridad de contenido")
    return problemas


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datos", default=os.path.join(RAIZ, "data"))
    parser.add_argument("--salida", default=os.path.join(RAIZ, "dist", "revistas-prueba.html"))
    parser.add_argument("--artefacto", action="store_true",
                        help="genera también la variante para el visor de artefactos de Claude")
    argumentos = parser.parse_args()

    pagina, es_prueba, revistas = empaquetar(argumentos.datos)
    problemas = problemas_autocontenido(pagina)
    if problemas:
        print("El archivo haría peticiones fuera de sí mismo:", *problemas, sep="\n  ", file=sys.stderr)
        raise SystemExit(1)

    os.makedirs(os.path.dirname(os.path.abspath(argumentos.salida)), exist_ok=True)
    with open(argumentos.salida, "w", encoding="utf-8") as archivo:
        archivo.write(pagina)
    tamano = len(pagina.encode("utf-8"))
    print(f"Escrito {os.path.relpath(argumentos.salida, RAIZ)}: {tamano / 1024 / 1024:.2f} MB, "
          f"{revistas} revistas, {'datos de prueba' if es_prueba else 'datos reales'}. "
          "Sin referencias a recursos externos.")
    if argumentos.artefacto:
        fragmento = a_fragmento(pagina)
        problemas = problemas_autocontenido(fragmento, exigir_csp=False)
        if problemas:
            print("La variante de artefacto haría peticiones fuera de sí misma:", *problemas, sep="\n  ", file=sys.stderr)
            raise SystemExit(1)
        ruta = os.path.join(os.path.dirname(os.path.abspath(argumentos.salida)), "revistas-artefacto.html")
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write(fragmento)
        print(f"Escrito {os.path.relpath(ruta, RAIZ)} para el visor de artefactos.")
    if tamano > LIMITE_BYTES:
        print(f"Aviso: el archivo supera los 10 MB ({tamano / 1024 / 1024:.2f} MB). "
              "No se ha recortado ningún dato.", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
