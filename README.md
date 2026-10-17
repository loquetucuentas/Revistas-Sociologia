# Revistas de sociología en acceso abierto

Aplicación web de una sola página para explorar revistas de sociología de acceso abierto publicadas en español: listado con buscador, ficha de cada revista con sus tres números más recientes e índice de artículos de cada número, con enlace a la publicación original.

La accesibilidad es un requisito innegociable: WCAG 2.2 nivel AA y los siete principios del diseño universal. Consulta REQUISITOS.md para los requisitos y ACCESIBILIDAD.md para lo que se ha comprobado y lo que queda pendiente.

## Estado actual: datos de prueba

Los datos de la carpeta data son ficticios mientras no se ejecute el recolector con acceso a internet. La aplicación lo indica con un aviso visible en la parte superior. Los datos reales llegarán en la primera ejecución del flujo «Recolectar datos de revistas» en GitHub Actions.

## Cómo usarla

Opción 1: abre index.html con doble clic en cualquier navegador. No hace falta instalar nada.

Opción 2: publícala con GitHub Pages (ver más abajo) y entra en la dirección que te dé GitHub.

## Estructura

1. index.html, assets/estilos.css y assets/app.js: la aplicación, sin dependencias externas.
2. data: los datos que lee la aplicación. revistas.json es el listado y data/revistas contiene un archivo por revista. Cada JSON tiene una copia .js con el mismo contenido para que la aplicación funcione al abrirla desde el disco. data/informe-no-resueltas.md recoge las revistas que no se han podido resolver.
3. recolector: el script en Python que genera los datos. Solo usa la biblioteca estándar.
4. pruebas: pruebas automáticas con Playwright, axe y Lighthouse, con sus propios datos de prueba.
5. .github/workflows: la recolección semanal y las pruebas.

## Recolector

```
python3 recolector/recolectar.py --limite 50
```

1. DOAJ: revistas con materia de sociología (clasificación LCC HM) y con español entre sus idiomas.
2. Crossref: por ISSN, los artículos más recientes, agrupados por volumen y número; se guardan los tres últimos números.
3. OAI-PMH: si Crossref no tiene datos o los más recientes tienen más de dos años, se busca el punto OAI de OJS en la web de la revista.
4. Las revistas sin datos van a data/informe-no-resueltas.md con el motivo. No se inventa ningún dato.
5. Los datos nuevos solo sustituyen a los anteriores si la recolección termina bien.

Opcionalmente, define la variable de repositorio CONTACTO_EMAIL (Settings, Secrets and variables, Actions, Variables) para identificarte ante Crossref, como recomienda su política de uso.

Para regenerar los datos ficticios: `python3 recolector/datos_prueba.py`.

## Publicación con GitHub Pages

1. Fusiona esta rama en main.
2. En GitHub, ve a Settings, Pages.
3. En Source elige «Deploy from a branch», rama main y carpeta raíz (/), y guarda.
4. El archivo .nojekyll hace que GitHub sirva los archivos tal cual.

El flujo de recolección se ejecuta los lunes a las 04:17 UTC y también se puede lanzar a mano desde la pestaña Actions, indicando el límite de revistas.

## Pruebas

```
npm install
npm test               # axe y comportamiento accesible con Playwright
npm run lighthouse     # Lighthouse (puntuación de accesibilidad mínima: 100)
python3 -m unittest discover -s recolector/pruebas
```

## Licencias y citas

Los metadatos proceden de DOAJ, Crossref y los archivos OAI-PMH de cada revista. Cada artículo pertenece a su revista y se distribuye con la licencia que se indica en su ficha. La aplicación no muestra textos completos: enlaza siempre al original.
