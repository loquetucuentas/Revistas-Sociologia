"""Pruebas del comprobador de herramientas/empaquetar.py: debe detectar
cualquier referencia a recursos fuera del archivo."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "herramientas"))

import empaquetar  # noqa: E402

CSP = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'">'


class PruebasAutocontenido(unittest.TestCase):
    def test_acepta_recursos_incrustados_y_enlaces(self):
        pagina = (CSP + '<link rel="icon" href="data:image/svg+xml,x"><style>a{color:red}</style>'
                  '<a href="https://doaj.org/">DOAJ</a><script>var a = 1;</script>')
        self.assertEqual(empaquetar.problemas_autocontenido(pagina), [])

    def test_detecta_recursos_externos(self):
        casos = [
            '<script src="app.js"></script>',
            '<link rel="stylesheet" href="https://fonts.example/x.css">',
            '<img src="foto.png" alt="">',
            '<style>body{background:url(fondo.png)}</style>',
            '<style>@import "otra.css";</style>',
            '<style>@font-face{font-family:x;src:url(data:font/woff2,x)}</style>',
            '<p style="background:url(https://example.org/a.png)">x</p>',
        ]
        for caso in casos:
            with self.subTest(caso=caso):
                self.assertNotEqual(empaquetar.problemas_autocontenido(CSP + caso), [])

    def test_exige_la_politica_de_seguridad(self):
        self.assertIn("falta la política de seguridad de contenido", empaquetar.problemas_autocontenido("<p>x</p>"))

    def test_json_no_puede_cerrar_el_script(self):
        self.assertNotIn("</", empaquetar.json_para_script({"t": "</script><b>"}))
