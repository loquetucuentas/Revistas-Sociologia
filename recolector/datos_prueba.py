#!/usr/bin/env python3
"""Genera los datos de PRUEBA que usan las pruebas automáticas.

Todas las revistas, números y artículos son ficticios, llevan la marca
es_prueba y enlazan a example.org, un dominio reservado para ejemplos.
Se escriben solo en pruebas/datos: la carpeta data de la aplicación
contiene datos reales y el script se niega a sobrescribirla.

Uso: python3 recolector/datos_prueba.py [--salida carpeta]
"""

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comun import VERSION_DATOS, escribir_datos, sin_tildes  # noqa: E402

FECHA = "2026-10-17T00:00:00+00:00"
CC_BY = {"nombre": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/"}
CC_BY_NC_SA = {"nombre": "CC BY-NC-SA 4.0", "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/"}

REVISTAS = [
    ("prueba-0001", "Revista de Prueba de Estudios Sociales", "Asociación Ficticia de Sociología", 3),
    ("prueba-0002", "Cuadernos de Ejemplo de Sociología Urbana", "Universidad de Ejemplo", 3),
    ("prueba-0003", "Ánfora de Prueba: Sociología y Cultura", "Editorial de Ejemplo", 2),
    ("prueba-0004", "Ñandú, revista de prueba", "Instituto Imaginario", 3),
    ("prueba-0005", "Revista de Prueba sin Números", "Fundación de Ejemplo", 0),
]

TEMAS = [
    "desigualdad territorial", "trabajo de cuidados", "movilidad residencial", "participación juvenil",
    "redes vecinales", "consumo cultural", "migraciones recientes", "uso del tiempo",
]


def articulo(revista, numero, posicion):
    tema = TEMAS[(posicion + numero) % len(TEMAS)]
    identificador = f"10.0000/{revista}.{numero}.{posicion}"
    datos = {
        "id": identificador,
        "titulo": f"Artículo de prueba {posicion}: una aproximación ficticia al estudio de {tema}",
        "idioma_titulo": None,
        "autores": [{"nombre": f"Persona Autora de Prueba {posicion}", "orcid": None},
                    {"nombre": "Otra Persona Ficticia", "orcid": None}],
        "resumen": (f"Texto de prueba. Este resumen no corresponde a ningún artículo real. Sirve para comprobar "
                    f"cómo se presenta un resumen sobre {tema} en la interfaz, con una longitud parecida a la "
                    "de un resumen académico habitual y varias frases seguidas."),
        "idioma_resumen": None,
        "licencia": CC_BY if posicion % 2 else CC_BY_NC_SA,
        "url": f"https://example.org/{revista}/articulo/{numero}-{posicion}",
        "doi": identificador,
        "paginas": f"{posicion * 20 - 19}-{posicion * 20}",
        "fuente": "Datos de prueba",
    }
    if posicion == 2:
        datos.update({
            "titulo": "Test article: a fictitious study of neighbourhood networks and social trust",
            "idioma_titulo": "en",
            "resumen": ("Test data. This abstract does not belong to any real article. It is written in English "
                        "to check that the interface marks its language so that screen readers switch voice."),
            "idioma_resumen": "en",
        })
    if posicion == 3:
        datos.update({"resumen": None, "licencia": None})
    return datos


LICENCIA_TEXTO = {
    "codigo": "by", "nombre": "CC BY 4.0", "nombre_completo": "Creative Commons Atribución 4.0 Internacional",
    "url": "https://creativecommons.org/licenses/by/4.0/",
    "url_legal": "https://creativecommons.org/licenses/by/4.0/legalcode.es",
}


def texto_de_prueba(articulo):
    """Texto completo ficticio, con todos los elementos que la vista de lectura debe saber mostrar."""
    nota = lambda n: ["sup", {}, ["a", {"href": f"#t-nota-{n}", "id": f"t-llamada-nota-{n}-1"}, str(n)]]
    contenido = [
        ["section", {"id": "t-s1"},
         ["h2", {"id": "t-s1-titulo"}, "Introducción"],
         ["p", {}, "Texto de prueba. Este artículo no existe: sirve para comprobar la vista de lectura. "
                   "Incluye una llamada a nota", nota(1), " y una cita a la bibliografía (",
          ["a", {"href": "#t-ref-1", "id": "t-llamada-ref-1-1"}, "Autora Ficticia, 2020"], ")."],
         ["p", {"lang": "en"}, "This paragraph is written in English to check that screen readers switch voice."],
         ["blockquote", {}, ["p", {}, "Una cita textual larga de prueba, con su propio formato."]],
         ["h3", {"id": "t-s1-1"}, "Objetivos"],
         ["ul", {}, ["li", {}, "Primer objetivo de prueba."], ["li", {}, "Segundo objetivo de prueba", nota(2), "."]]],
        ["section", {"id": "t-s2"},
         ["h2", {"id": "t-s2-titulo"}, "Resultados"],
         ["figure", {"id": "t-tabla-1"},
          ["table", {},
           ["caption", {}, "Tabla 1. Casos ficticios por año y territorio"],
           ["thead", {}, ["tr", {}] + [["th", {"scope": "col"}, c] for c in
                                        ("Año", "Territorio norte", "Territorio sur", "Territorio este",
                                         "Territorio oeste", "Territorio central", "Total")]],
           ["tbody", {}] + [["tr", {}, ["th", {"scope": "row"}, str(a)]] + [["td", {}, str(a % 7 + i)] for i in range(6)]
                            for a in (2021, 2022, 2023)]]],
         ["figure", {"id": "t-figura-1"},
          ["figcaption", {}, "Figura 1. Evolución ficticia de los casos"],
          ["figura", {"alt": "Gráfico de líneas que sube de 5 casos en 2021 a 9 en 2023."}]],
         ["figure", {"id": "t-figura-2"},
          ["figcaption", {}, "Figura 2. Mapa ficticio sin descripción"],
          ["figura", {}]],
         ["p", {}, "Más información en ", ["a", {"href": "https://example.org/proyecto"}, "la web ficticia del proyecto"], "."]],
        ["section", {"id": "t-notas"},
         ["h2", {"id": "t-notas-titulo"}, "Notas"],
         ["aside", {"id": "t-nota-1", "rol": "fn"}, ["p", {}, "1. Primera nota de prueba."]],
         ["aside", {"id": "t-nota-2", "rol": "fn"}, ["p", {}, "2. Segunda nota de prueba."]]],
        ["section", {"id": "t-referencias"},
         ["h2", {"id": "t-referencias-titulo"}, "Referencias"],
         ["p", {"id": "t-ref-1", "rol": "ref"}, "Autora Ficticia, A. (2020). ", ["i", {}, "Libro de prueba"], ". Editorial de Ejemplo."]],
    ]
    return {
        "version": 1, "recogido": FECHA, "doi": articulo["doi"], "titulo": articulo["titulo"], "es_prueba": True,
        "licencia": LICENCIA_TEXTO,
        "fuente": {"url": articulo["url"], "formato": "HTML", "plataforma": "datos de prueba", "pagina": articulo["url"]},
        "autores_cita": [{"apellidos": "Autora de Prueba", "nombre_pila": "Persona", "nombre": None},
                         {"apellidos": "Ficticia", "nombre_pila": "Otra Persona", "nombre": None}],
        "avisos_derechos": ["Copyright (c) 2026 Persona Autora de Prueba. Aviso de derechos ficticio."],
        "idioma_principal": "es",
        "indice": [{"id": "t-s1-titulo", "nivel": 2, "texto": "Introducción", "lang": None},
                   {"id": "t-s1-1", "nivel": 3, "texto": "Objetivos", "lang": None},
                   {"id": "t-s2-titulo", "nivel": 2, "texto": "Resultados", "lang": None},
                   {"id": "t-notas-titulo", "nivel": 2, "texto": "Notas", "lang": None},
                   {"id": "t-referencias-titulo", "nivel": 2, "texto": "Referencias", "lang": None}],
        "vueltas": {"t-nota-1": "t-llamada-nota-1-1", "t-nota-2": "t-llamada-nota-2-1", "t-ref-1": "t-llamada-ref-1-1"},
        "contenido": contenido,
    }


def numeros(revista, cantidad):
    lista = []
    for indice in range(cantidad):
        volumen, numero, anio = 12 - indice // 2, 2 - indice % 2, 2026 - indice // 2
        articulos = [] if (revista == "prueba-0003" and indice == 1) else \
            [articulo(revista, indice, p) for p in range(1, 5)]
        if revista == "prueba-0001" and indice == 0:
            # Un artículo con texto completo ficticio para probar la vista de lectura.
            articulos[0]["texto_completo"] = f"textos/{revista}-v{volumen}-n{numero}-1.json"
        lista.append({
            "id": f"v{volumen}-n{numero}-{anio}",
            "volumen": str(volumen), "numero": str(numero), "anio": anio,
            "fecha": f"{anio}-{'06' if numero == 1 else '12'}",
            "etiqueta": f"Vol. {volumen}, núm. {numero} ({anio})",
            "fuente": "Datos de prueba",
            "articulos": articulos,
        })
    return lista


def main():
    parser = argparse.ArgumentParser()
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument("--salida", default=os.path.join(raiz, "pruebas", "datos"))
    carpeta = parser.parse_args().salida
    if os.path.abspath(carpeta) == os.path.join(raiz, "data"):
        raise SystemExit("La carpeta data tiene datos reales; los datos de prueba van en pruebas/datos.")
    if os.path.isdir(carpeta):
        shutil.rmtree(carpeta)
    fichas = []
    for identificador, titulo, editorial, cantidad in REVISTAS:
        lista = numeros(identificador, cantidad)
        for numero in lista:
            for art in numero["articulos"]:
                if art.get("texto_completo"):
                    escribir_datos(carpeta, art["texto_completo"], texto_de_prueba(art))
        ficha = {
            "id": identificador,
            "titulo": titulo,
            "titulo_alternativo": None,
            "idiomas": ["es"],
            "issn_impreso": None,
            "issn_electronico": None,
            "editorial": editorial,
            "pais": "ES",
            "materias": ["Sociología (datos de prueba)"],
            "palabras_clave": ["datos de prueba", "sociología"],
            "licencias": [CC_BY],
            "url": f"https://example.org/{identificador}/",
            "url_doaj": None,
            "descripcion": ("Revista ficticia creada solo para probar la interfaz. Ninguno de sus datos "
                            "procede de DOAJ ni de Crossref."),
            "fuente_ficha": "Datos de prueba",
            "archivo": f"revistas/{identificador}.json",
            "ultimo_numero": lista[0]["etiqueta"] if lista else None,
            "fuente_numeros": "Datos de prueba",
        }
        escribir_datos(carpeta, ficha["archivo"], {
            "version": VERSION_DATOS, "generado": FECHA, "es_prueba": True, "revista": ficha, "numeros": lista})
        fichas.append(ficha)
    fichas.sort(key=lambda r: sin_tildes(r["titulo"]))
    escribir_datos(carpeta, "revistas.json", {
        "version": VERSION_DATOS, "generado": FECHA, "es_prueba": True,
        "fuentes": ["Datos de prueba"], "idiomas_incluidos": ["es"], "total": len(fichas), "revistas": fichas})
    print(f"Datos de prueba escritos en {os.path.normpath(carpeta)}")


if __name__ == "__main__":
    main()
