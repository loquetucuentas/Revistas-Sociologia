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


def numeros(revista, cantidad):
    lista = []
    for indice in range(cantidad):
        volumen, numero, anio = 12 - indice // 2, 2 - indice % 2, 2026 - indice // 2
        articulos = [] if (revista == "prueba-0003" and indice == 1) else \
            [articulo(revista, indice, p) for p in range(1, 5)]
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
