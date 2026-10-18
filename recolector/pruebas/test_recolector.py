"""Pruebas del recolector con respuestas de ejemplo construidas a mano.

Los datos de estas pruebas son ficticios y solo comprueban el tratamiento
de los formatos de DOAJ, Crossref y OAI-PMH; nunca llegan a data/.
"""

import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import comun  # noqa: E402
import crossref  # noqa: E402
import doaj  # noqa: E402
import oai  # noqa: E402


class PruebasComun(unittest.TestCase):
    def test_limpiar_resumen_jats(self):
        texto = "<jats:title>Resumen</jats:title><jats:p>Texto con &amp; entidades.</jats:p>"
        self.assertEqual(comun.limpiar_resumen(texto), "Texto con & entidades.")

    def test_licencias_creative_commons(self):
        self.assertEqual(comun.normalizar_licencia("https://creativecommons.org/licenses/by-nc-sa/4.0/")["nombre"],
                         "CC BY-NC-SA 4.0")
        self.assertEqual(comun.normalizar_licencia(None, "CC BY")["nombre"], "CC BY")
        self.assertEqual(comun.normalizar_licencia("http://creativecommons.org/publicdomain/zero/1.0/")["nombre"],
                         "CC0 1.0")
        self.assertIsNone(comun.normalizar_licencia(None, None))

    def test_url_segura_rechaza_otros_esquemas(self):
        self.assertIsNone(comun.url_segura("javascript:alert(1)"))
        self.assertEqual(comun.url_segura(" https://ejemplo.org "), "https://ejemplo.org")

    def test_detectar_idioma(self):
        self.assertEqual(comun.detectar_idioma(
            "The social networks of the neighbourhood and the trust between residents in the city"), "en")
        self.assertEqual(comun.detectar_idioma(
            "Las redes sociales del barrio y la confianza entre los vecinos de la ciudad"), "es")
        self.assertIsNone(comun.detectar_idioma("Sociología urbana"))

    def test_detectar_idioma_en_titulos_cortos(self):
        self.assertEqual(comun.detectar_idioma("Arquitetura de terra em perspectiva"), "pt")
        self.assertEqual(comun.detectar_idioma("MENTORAT ET PRATIQUES EN CLASSE : PERCEPTIONS DE STAGIAIRES"), "fr")
        self.assertEqual(comun.detectar_idioma("Pedagogika zdrowia i szkolna edukacja zdrowotna wobec wyzwań"), "pl")
        self.assertEqual(comun.detectar_idioma("El feminicidio como expresión extrema de la desigualdad"), "es")
        # Si no hay rasgos claros, no se marca: la página ya está en español.
        self.assertIsNone(comun.detectar_idioma("Algunos usos del meme en internet"))

    def test_limpiar_resumen_descarta_encabezados_sueltos(self):
        self.assertEqual(comun.limpiar_resumen("<jats:p>Resumen</jats:p>"), "")
        self.assertEqual(comun.limpiar_resumen("-"), "")

    def test_bloqueo_de_red_no_se_reintenta(self):
        llamadas = []

        def rechazar(*argumentos, **opciones):
            llamadas.append(1)
            raise comun.urllib.error.URLError(OSError("Tunnel connection failed: 403 Forbidden"))

        original = comun.urllib.request.urlopen
        comun.urllib.request.urlopen = rechazar
        try:
            with self.assertRaises(comun.ErrorRed) as contexto:
                comun.obtener("https://revista.ejemplo.org/oai", intentos=3)
        finally:
            comun.urllib.request.urlopen = original
        self.assertTrue(contexto.exception.bloqueado)
        self.assertEqual(contexto.exception.dominio, "revista.ejemplo.org")
        self.assertEqual(len(llamadas), 1)

    def test_idioma_declarado_tiene_prioridad(self):
        self.assertEqual(comun.idioma_de("Texto cualquiera", "eng"), "en")

    def test_escribir_datos_crea_json_y_copia_js(self):
        with tempfile.TemporaryDirectory() as carpeta:
            comun.escribir_datos(carpeta, "revistas/x.json", {"a": "ñ"})
            with open(os.path.join(carpeta, "revistas/x.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"a": "ñ"})
            with open(os.path.join(carpeta, "revistas/x.js"), encoding="utf-8") as f:
                self.assertIn('["revistas/x.json"] = {', f.read())


class PruebasDoaj(unittest.TestCase):
    REGISTRO = {"bibjson": {
        "title": "Revista Ficticia", "eissn": "0000-0001", "language": ["ES", "EN"],
        "subject": [{"scheme": "LCC", "term": "Sociology (General)", "code": "HM1-1281"}],
        "publisher": {"name": "Editorial", "country": "ES"}, "ref": {"journal": "https://ejemplo.org/revista"},
        "license": [{"type": "CC BY", "url": "https://creativecommons.org/licenses/by/4.0/"}]}}

    def test_convertir(self):
        ficha = doaj.convertir(self.REGISTRO)
        self.assertEqual(ficha["id"], "0000-0001")
        self.assertEqual(ficha["idiomas"], ["es", "en"])
        self.assertEqual(ficha["licencias"][0]["nombre"], "CC BY 4.0")
        self.assertTrue(doaj.es_de_sociologia(self.REGISTRO["bibjson"]))

    def test_filtra_materia(self):
        self.assertFalse(doaj.es_de_sociologia({"subject": [{"term": "Medicine", "code": "R"}]}))


def obra(doi, volumen, numero, anio, mes=1, titulo="Título del artículo"):
    return {"DOI": doi, "title": [titulo], "volume": volumen, "issue": numero,
            "published": {"date-parts": [[anio, mes]]}, "author": [{"given": "Ana", "family": "Pérez"}],
            "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/", "content-version": "vor"}]}


class PruebasCrossref(unittest.TestCase):
    def test_agrupa_y_ordena_los_tres_ultimos_numeros(self):
        obras = [obra("10.1/a", "10", "1", 2024), obra("10.1/b", "10", "2", 2024, 7),
                 obra("10.1/c", "11", "1", 2025), obra("10.1/d", "9", "2", 2023),
                 obra("10.1/e", "11", "1", 2025)]
        numeros = crossref.agrupar(obras)
        self.assertEqual([n["etiqueta"] for n in numeros],
                         ["Vol. 11, núm. 1 (2025)", "Vol. 10, núm. 2 (2024)", "Vol. 10, núm. 1 (2024)"])
        self.assertEqual(len(numeros[0]["articulos"]), 2)
        articulo = numeros[0]["articulos"][0]
        self.assertEqual(articulo["url"], "https://doi.org/10.1/c")
        self.assertEqual(articulo["autores"][0]["nombre"], "Ana Pérez")
        self.assertEqual(articulo["licencia"]["nombre"], "CC BY 4.0")

    def test_publicacion_continua(self):
        numeros = crossref.agrupar([obra("10.1/x", None, None, 2025)])
        self.assertEqual(numeros[0]["etiqueta"], "Publicación continua (2025)")

    def test_descarta_obras_sin_titulo(self):
        self.assertEqual(crossref.agrupar([{"DOI": "10.1/z", "title": []}]), [])


OAI_XML = """<?xml version="1.0"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords>
<record><header><identifier>oai:ejemplo:1</identifier></header><metadata>
<oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title xml:lang="en-US">Title in English</dc:title>
<dc:title xml:lang="es-ES">Título en español</dc:title>
<dc:creator>Pérez, Ana</dc:creator>
<dc:description xml:lang="es-ES">Resumen del artículo.</dc:description>
<dc:date>2025-06-30</dc:date>
<dc:type>info:eu-repo/semantics/article</dc:type>
<dc:identifier>https://ejemplo.org/index.php/rev/article/view/1</dc:identifier>
<dc:identifier>10.1234/rev.1</dc:identifier>
<dc:source xml:lang="es-ES">Revista Ficticia; Vol. 7 Núm. 2 (2025); 10-20</dc:source>
<dc:rights>https://creativecommons.org/licenses/by/4.0</dc:rights>
</oai_dc:dc></metadata></record>
<record><header status="deleted"><identifier>oai:ejemplo:2</identifier></header></record>
</ListRecords></OAI-PMH>"""


class PruebasOai(unittest.TestCase):
    def test_candidatos_ojs(self):
        self.assertEqual(oai.candidatos("https://ejemplo.org/index.php/rev/index")[0],
                         "https://ejemplo.org/index.php/rev/oai")

    def test_leer_fuente(self):
        self.assertEqual(oai.leer_fuente("Revista; Vol. 7 Núm. 2 (2025); 10-20"), ("7", "2", 2025))
        self.assertEqual(oai.leer_fuente("Revista; Vol 12 No 1 (2024)"), ("12", "1", 2024))
        self.assertEqual(oai.leer_fuente("Revista; Núm. 45 (2023)"), (None, "45", 2023))

    def test_registro_a_articulo(self):
        raiz = ET.fromstring(OAI_XML)
        registros = [oai.registro_a_articulo(r) for r in raiz.iter("{http://www.openarchives.org/OAI/2.0/}record")]
        self.assertIsNone(registros[1])
        datos = registros[0]
        self.assertEqual((datos["volumen"], datos["numero"], datos["anio"]), ("7", "2", 2025))
        articulo = datos["articulo"]
        self.assertEqual(articulo["titulo"], "Título en español")
        self.assertEqual(articulo["doi"], "10.1234/rev.1")
        self.assertEqual(articulo["url"], "https://ejemplo.org/index.php/rev/article/view/1")
        self.assertEqual(articulo["licencia"]["nombre"], "CC BY 4.0")
        numeros = oai.agrupar(registros)
        self.assertEqual(numeros[0]["etiqueta"], "Vol. 7, núm. 2 (2025)")


if __name__ == "__main__":
    unittest.main()
