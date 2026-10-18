"""Pruebas del texto completo: licencias, saneado de HTML y JATS y fidelidad.

Los textos de estas pruebas son ficticios y escritos a mano; nunca llegan a data/.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import licencias  # noqa: E402
import saneado  # noqa: E402
import textos  # noqa: E402

HOY = datetime.date(2026, 10, 18)


def lic(url, version="vor", inicio=None):
    datos = {"URL": url, "content-version": version}
    if inicio:
        datos["start"] = {"date-parts": [list(inicio)]}
    return datos


class PruebasLicencias(unittest.TestCase):
    def test_admite_las_cuatro_licencias(self):
        for codigo, nombre in (("by", "Atribución"), ("by-sa", "Atribución-CompartirIgual"),
                               ("by-nc", "Atribución-NoComercial"),
                               ("by-nc-sa", "Atribución-NoComercial-CompartirIgual")):
            apta, ficha, motivo = licencias.clasificar([lic(f"https://creativecommons.org/licenses/{codigo}/4.0/")], HOY)
            self.assertTrue(apta, codigo)
            self.assertEqual(motivo, "admitida")
            self.assertEqual(ficha["nombre_completo"], f"Creative Commons {nombre} 4.0 Internacional")
            self.assertEqual(ficha["url_legal"], f"https://creativecommons.org/licenses/{codigo}/4.0/legalcode.es")

    def test_excluye_nd_sin_licencia_y_otras(self):
        casos = {
            "nd": [lic("http://creativecommons.org/licenses/by-nc-nd/4.0")],
            "sin-licencia": [],
            "no-cc": [lic("https://www.elsevier.com/tdm/userlicense/1.0/")],
            "solo-otra-version": [lic("https://creativecommons.org/licenses/by/4.0/", "am")],
            "varias-licencias": [lic("https://creativecommons.org/licenses/by/4.0/"),
                                 lic("https://creativecommons.org/licenses/by-nc/4.0/")],
            "embargo": [lic("https://creativecommons.org/licenses/by/4.0/", inicio=(2027, 1, 1))],
        }
        for motivo, lista in casos.items():
            with self.subTest(motivo=motivo):
                apta, ficha, obtenido = licencias.clasificar(lista, HOY)
                self.assertFalse(apta)
                self.assertIsNone(ficha)
                self.assertEqual(obtenido, motivo)

    def test_url_cc_ambigua_no_se_admite(self):
        self.assertIsNone(licencias.leer_licencia_cc("https://creativecommons.org/licenses/by/"))
        self.assertIsNone(licencias.leer_licencia_cc("https://creativecommons.org/licenses/by/4.0/es/extra"))
        self.assertIsNone(licencias.leer_licencia_cc("https://creativecommons.org/licenses/by-xx/4.0/"))

    def test_jurisdiccion(self):
        apta, ficha, _ = licencias.clasificar([lic("http://creativecommons.org/licenses/by-nc-sa/3.0/es/")], HOY)
        self.assertTrue(apta)
        self.assertEqual(ficha["nombre_completo"], "Creative Commons Atribución-NoComercial-CompartirIgual 3.0 España")

    def test_contradicciones_en_la_pagina(self):
        _, ficha, _ = licencias.clasificar([lic("https://creativecommons.org/licenses/by/4.0/")], HOY)
        self.assertIsNone(licencias.contradice(ficha, ["https://creativecommons.org/licenses/by/4.0/deed.es"]))
        self.assertEqual(licencias.contradice(ficha, ["https://creativecommons.org/licenses/by-nd/4.0/"]),
                         "licencia-pagina-distinta")
        self.assertEqual(licencias.contradice(ficha, [], ["© 2025 Universidad. Todos los derechos reservados."]),
                         "derechos-reservados")


GALERADA = """<html lang="es"><head><title>x</title><style>p{color:red}</style><script>alert(1)</script></head>
<body><h1>Título del artículo</h1><p class="x" style="color:red">Primer párrafo con una nota<a href="#_ftn1" name="_ftnref1">[1]</a>.</p>
<h2>Método</h2><p>Segundo <b>párrafo</b> <span lang="en">with English words</span>.</p>
<table><caption>Tabla 1</caption><tr><th scope="col">Año</th><th scope="col">Casos</th></tr><tr><td>2020</td><td>5</td></tr></table>
<p><img src="https://revista.ejemplo.org/fig1.png" alt="Gráfico de barras con los casos por año"></p>
<p><img src="fig2.png"></p>
<form><input value="no es texto"><button>Enviar</button></form>
<p>Enlace <a href="javascript:alert(1)">peligroso</a> y <a href="https://doi.org/10.1/x">externo</a>.</p>
<div><p><a href="#_ftnref1" name="_ftn1">[1]</a> Texto de la nota.</p></div></body></html>"""


class PruebasSaneadoHTML(unittest.TestCase):
    def convertir(self, texto=GALERADA):
        raiz = saneado.leer_html(texto)
        cuerpo = saneado.buscar(raiz, lambda n: n[0] == "body")
        arbol = saneado.convertir_html(cuerpo, "es")
        arbol, vueltas = saneado.preparar(arbol)
        return saneado.validar(arbol), vueltas

    def test_conserva_el_texto_y_quita_lo_que_no_es_contenido(self):
        arbol, _ = self.convertir()
        texto = "".join(saneado.texto_plano(n) for n in arbol)
        self.assertIn("Primer párrafo con una nota[1].", texto)
        self.assertIn("Texto de la nota.", texto)
        self.assertNotIn("alert", str(arbol))
        self.assertNotIn("no es texto", texto)
        self.assertNotIn("style", str(arbol))

    def test_jerarquia_de_encabezados_desplazada(self):
        arbol, _ = self.convertir()
        etiquetas = [n[0] for n in saneado._recorrer(arbol) if n[0].startswith("h")]
        self.assertEqual(etiquetas, ["h2", "h3"])

    def test_tablas_figuras_idiomas_y_enlaces(self):
        arbol, _ = self.convertir()
        nodos = list(saneado._recorrer(arbol))
        self.assertTrue(any(n[0] == "th" and n[1].get("scope") == "col" for n in nodos))
        figuras = [n for n in nodos if n[0] == "figura"]
        self.assertEqual(figuras[0][1], {"alt": "Gráfico de barras con los casos por año"})
        self.assertEqual(figuras[1][1], {})  # sin descripción: no se inventa
        self.assertTrue(any(n[0] == "span" and n[1].get("lang") == "en" for n in nodos))
        hrefs = [n[1].get("href") for n in nodos if n[0] == "a"]
        self.assertIn("https://doi.org/10.1/x", hrefs)
        self.assertNotIn("javascript:alert(1)", hrefs)

    def test_notas_de_ida_y_vuelta(self):
        arbol, vueltas = self.convertir()
        nodos = list(saneado._recorrer(arbol))
        llamada = next(n for n in nodos if n[1].get("href") == "#t-_ftn1")
        nota = next(n for n in nodos if n[1].get("href") == "#t-_ftnref1")
        self.assertEqual(llamada[1]["id"], "t-_ftnref1")
        self.assertEqual(nota[1]["id"], "t-_ftn1")
        self.assertEqual(vueltas, {})  # el original ya enlaza de vuelta

    def test_no_anida_vueltas_en_llamadas(self):
        # Una nota que enlaza de vuelta a la llamada no convierte la llamada en nota.
        texto = ('<html><body><p>Texto<a href="#fn1" id="fnref1"><sup>1</sup></a>.</p>'
                 '<ol><li id="fn1"><p>Nota. <a href="#fnref1">volver</a></p></li></ol></body></html>')
        arbol, vueltas = self.convertir(texto)
        self.assertEqual(vueltas, {})

    def test_rechaza_lo_que_no_puede_reproducir(self):
        for elemento in ("<math><mi>x</mi></math>", '<iframe src="https://video"></iframe>', "<video></video>"):
            with self.subTest(elemento=elemento), self.assertRaises(saneado.NoConvertible):
                self.convertir(f"<html><body><p>Texto</p>{elemento}</body></html>")

    def test_fidelidad(self):
        with self.assertRaises(saneado.NoConvertible):
            saneado.comprobar_fidelidad("Texto original completo", [["p", {}, "Texto original"]])
        saneado.comprobar_fidelidad("Texto   original", [["p", {}, "Texto original"]])


JATS = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN" "JATS-journalpublishing1.dtd">
<article xmlns:xlink="http://www.w3.org/1999/xlink" xml:lang="es" article-type="research-article">
<front><article-meta><permissions><copyright-statement>© 2025 Autora Ficticia</copyright-statement>
<license license-type="open-access" xlink:href="https://creativecommons.org/licenses/by/4.0/"><license-p>Este artículo se publica con licencia CC BY 4.0.</license-p></license>
</permissions></article-meta></front>
<body><sec id="s1"><title>Introducción</title><p>Texto con cita <xref ref-type="bibr" rid="B1">(Pérez, 2020)</xref> y nota<xref ref-type="fn" rid="fn1">1</xref>.</p>
<p xml:lang="en">An English paragraph.</p>
<list list-type="bullet"><list-item><p>Uno</p></list-item><list-item><p>Dos</p></list-item></list>
<fig id="f1"><label>Figura 1</label><caption><p>Evolución</p></caption><graphic xlink:href="f1.png"><alt-text>Línea ascendente</alt-text></graphic></fig>
<sec id="s1-1"><title>Subapartado</title><p>Más texto.</p></sec></sec></body>
<back><fn-group><fn id="fn1"><p>Nota primera.</p></fn></fn-group>
<ref-list><title>Referencias</title><ref id="B1"><mixed-citation>Pérez, A. (2020). <italic>Libro</italic>. Editorial.</mixed-citation></ref></ref-list></back>
</article>"""


class PruebasSaneadoJATS(unittest.TestCase):
    def test_convierte_jats(self):
        raiz = saneado.leer_jats(JATS.encode())
        arbol, avisos, urls = saneado.convertir_jats(raiz, "es")
        arbol, vueltas = saneado.preparar(arbol)
        saneado.validar(arbol)
        nodos = list(saneado._recorrer(arbol))
        self.assertEqual([n[0] for n in nodos if n[0].startswith("h")], ["h2", "h3", "h2"])
        self.assertIn("© 2025 Autora Ficticia", avisos)
        self.assertEqual(urls, ["https://creativecommons.org/licenses/by/4.0/"])
        self.assertTrue(any(n[0] == "p" and n[1].get("lang") == "en" for n in nodos))
        self.assertTrue(any(n[0] == "figura" and n[1].get("alt") == "Línea ascendente" for n in nodos))
        self.assertTrue(any(n[0] == "a" and n[1].get("href") == "#t-B1" for n in nodos))
        # Las notas y referencias reciben un enlace de vuelta a su primera llamada.
        self.assertEqual(set(vueltas), {"t-B1", "t-fn1"})
        indice = saneado.tabla_de_contenidos(arbol)
        self.assertEqual([e["texto"] for e in indice], ["Introducción", "Subapartado", "Referencias"])

    def test_rechaza_formulas_y_entidades(self):
        with self.assertRaises(saneado.NoConvertible):
            raiz = saneado.leer_jats(JATS.replace("<p>Más texto.</p>", "<p><inline-formula>x</inline-formula></p>").encode())
            saneado.convertir_jats(raiz, "es")
        with self.assertRaises(saneado.NoConvertible):
            saneado.leer_jats(b'<!DOCTYPE a [<!ENTITY x "y">]><article>&x;</article>')


class PruebasPaginaArticulo(unittest.TestCase):
    PAGINA = """<html><head><meta name="DC.Rights" content="Copyright (c) 2025 Autora">
    <link rel="license" href="https://creativecommons.org/licenses/by-nc-sa/4.0/"></head><body>
    <ul><li><a class="obj_galley_link pdf" href="/index.php/r/article/view/10/20">PDF</a></li>
    <li><a class="obj_galley_link file" href="/index.php/r/article/view/10/21">HTML</a></li>
    <li><a class="obj_galley_link file" href="/index.php/r/article/view/10/22">XML</a></li></ul>
    <div class="item copyright"><p>Esta obra está bajo una licencia <a rel="license" href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a>.</p></div>
    </body></html>"""

    def test_galeradas_sin_pdf_y_xml_primero(self):
        galeradas, urls, avisos = textos.leer_pagina(self.PAGINA, "https://revista.ejemplo.org/index.php/r/article/view/10")
        self.assertEqual([g["formato"] for g in galeradas], ["xml", "html"])
        self.assertTrue(all("/view/10/20" not in g["url"] for g in galeradas))
        self.assertIn("https://creativecommons.org/licenses/by-nc-sa/4.0/", urls)
        self.assertIn("Copyright (c) 2025 Autora", avisos)

    def test_estructura_desconocida_no_se_usa(self):
        with self.assertRaises(saneado.NoConvertible):
            textos.contenedor_html("<html><body><p>Texto</p></body></html>", "https://revista.ejemplo.org/articulo/1")


if __name__ == "__main__":
    unittest.main()
