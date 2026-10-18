# Requisitos del proyecto: Explorador de revistas de sociología en acceso abierto

Este documento recoge los requisitos acordados para el proyecto y sirve como referencia durante todo el desarrollo. Cada requisito tiene un identificador para poder citarlo en commits, pruebas y en ACCESIBILIDAD.md.

## 1. Objetivo y alcance

R1.1. Aplicación web de una sola página para explorar revistas de sociología de acceso abierto publicadas en español.

R1.2. Un archivo HTML con CSS y JavaScript propios, sin frameworks ni dependencias externas en tiempo de ejecución. Debe abrirse en cualquier navegador sin instalar nada y comportarse como una aplicación.

R1.3. Interfaz en español. El documento declara `lang="es"`.

R1.4. En esta primera versión solo se incluyen revistas en español.

R1.5. La estructura de datos queda preparada para añadir más adelante un filtro por idioma y revistas en inglés (cada revista, número y artículo registra su idioma o idiomas).

R1.6. Se muestra el texto completo dentro de la aplicación solo para los artículos que cumplen los requisitos de la sección 9. Los demás conservan su ficha, su resumen y el enlace al original. (Hasta el 18 de octubre de 2026 no se mostraba ningún texto completo.)

## 2. Accesibilidad (requisito innegociable)

R2.1. Cumplimiento completo de WCAG 2.2 nivel AA.

R2.2. Diseño conforme a los siete principios del diseño universal: uso equitativo, flexibilidad en el uso, uso simple e intuitivo, información perceptible, tolerancia al error, bajo esfuerzo físico, y tamaño y espacio apropiados.

R2.3. Prioridad: experiencia con lector de pantalla. Se probará con VoiceOver en iPhone y Mac, y solo con teclado.

Requisitos concretos:

R2.4. Enlace de salto al contenido principal.

R2.5. Estructura de encabezados lógica, con un único encabezado de primer nivel por vista.

R2.6. Puntos de referencia semánticos: `header`, `nav`, `main` y `footer`.

R2.7. Foco siempre visible y nunca oculto por otros elementos (WCAG 2.4.7, 2.4.11).

R2.8. Áreas de pulsación de al menos 24 por 24 píxeles, preferiblemente 44 por 44.

R2.9. Contraste mínimo de 4,5 a 1 en texto y de 3 a 1 en componentes de interfaz y estados de foco.

R2.10. Reflujo correcto a 400 por ciento de zoom (equivalente a 320 píxeles CSS de ancho) sin scroll horizontal.

R2.11. Respeto de las preferencias del sistema: movimiento reducido, tema claro u oscuro y contraste alto (incluido el modo de colores forzados).

R2.12. Controles para aumentar el tamaño del texto, cuya elección se recuerda entre visitas.

R2.13. Nada depende solo del color.

R2.14. Texto real, nunca imágenes de texto.

R2.15. Mensajes de error claros y con instrucciones para resolverlos.

R2.16. Todo título o resumen en un idioma distinto al de la interfaz se marca con el atributo `lang` correspondiente para que VoiceOver cambie de voz.

## 3. Comportamiento de aplicación de una sola página accesible

R3.1. Rutas con almohadilla en la dirección para que el botón atrás del navegador funcione y cada vista tenga una dirección propia que se pueda compartir.

R3.2. Al cambiar de vista: mover el foco al encabezado principal de la nueva vista, actualizar el título del documento y anunciar el cambio en una región activa educada (`aria-live="polite"`).

R3.3. Vista 1, listado de revistas: buscador por nombre y orden alfabético.

R3.4. Vista 2, ficha de revista: descripción, enlace a su web y los tres números más recientes.

R3.5. Vista 3, número: índice de artículos con título, autores, resumen cuando exista, licencia y enlace claro a la web original del artículo, que se abre con aviso de que sale de la aplicación. Decisión aprobada: el enlace se abre en una pestaña nueva y lo indica en su texto visible.

R3.6. Cada vista tiene estados de carga, vacío y error accesibles.

## 4. Datos

R4.1. El navegador del usuario no consulta directamente a las revistas (restricciones CORS). Lee archivos JSON estáticos de la carpeta `data` del repositorio.

R4.2. Un script recolector (Python o Node) genera los JSON: uno con el listado de revistas y uno por revista con sus tres últimos números y los artículos de cada uno.

R4.3. Fuentes:
R4.3.1. Listado de revistas: API de DOAJ, filtrando por materia (sociología) y por idioma (español).
R4.3.2. Números y artículos: API de Crossref, consultando por ISSN.
R4.3.3. Revistas OJS sin buena cobertura en Crossref: protocolo OAI-PMH desde el script.

R4.4. No se inventa ninguna revista, número ni artículo. Todo dato procede de esas fuentes.

R4.5. Las revistas que no se puedan resolver se registran en un informe aparte para revisión humana.

R4.6. Se respetan las licencias, se cita siempre a la revista y se enlaza al original.

R4.7. Decisiones aprobadas: el recolector se escribe en Python con la biblioteca estándar, y la primera recolección se limita a 50 revistas para revisar los resultados antes de ampliar.

## 5. Entorno

R5.1. Comprobar al inicio si el entorno de la nube tiene acceso de red a DOAJ y Crossref.

R5.2. Si no lo tiene, informar claramente y explicar qué ajuste hay que hacer en la configuración del entorno.

R5.3. Mientras tanto, desarrollar la interfaz con datos de ejemplo claramente marcados como de prueba, tanto en los archivos como en la propia interfaz.

## 6. Automatización y publicación

R6.1. Flujo de GitHub Actions que ejecuta el recolector una vez por semana y actualiza los JSON.

R6.2. Repositorio preparado para publicarse con GitHub Pages desde la rama principal.

## 7. Pruebas y documentación

R7.1. Comprobaciones automáticas de accesibilidad con axe y, si es posible, Lighthouse.

R7.2. Archivo ACCESIBILIDAD.md con lo que se ha comprobado y lo que queda pendiente de revisión manual con VoiceOver y teclado.

R7.3. Cada decisión importante de diseño se explica brevemente y en lenguaje claro.

R7.4. Las respuestas al responsable del proyecto se escriben en texto plano, sin símbolos de formato, porque usa lector de pantalla.

## 8. Proceso

R8.1. Antes de ejecutar nada, se presenta un plan y se espera aprobación.

## 9. Lectura del texto completo

R9.1. Licencia, comprobada por artículo y nunca por revista, a partir de los metadatos de Crossref y de la propia página del artículo. Solo se admiten CC BY, CC BY-SA, CC BY-NC y CC BY-NC-SA, declaradas de forma explícita para la versión publicada. Se excluyen las licencias ND, los artículos sin licencia, las licencias ambiguas o contradictorias, las que empiezan en una fecha futura y los artículos con todos los derechos reservados. Ante cualquier duda, no se muestra el texto.

R9.2. Origen del texto: solo versiones HTML o XML JATS publicadas por la revista. Nunca se extrae texto de un PDF. Un artículo con licencia válida que solo tiene PDF se trata como artículo sin texto completo.

R9.3. Recolección respetuosa: User-Agent con el nombre del proyecto y la dirección de contacto, respeto de robots.txt, al menos dos segundos entre peticiones a un mismo servidor, sin repetir descargas de lo que no ha cambiado y parada ante errores de limitación de tráfico. No se intenta evitar ningún bloqueo.

R9.4. Saneado y fidelidad: HTML propio sin scripts, estilos, marcos ni recursos externos. No se modifica ni se resume el texto; solo se reestructura la presentación. Se conservan títulos y su jerarquía, párrafos, listas, tablas con cabeceras, notas y referencias con enlaces de ida y vuelta, citas y avisos de derechos. Las figuras no muestran la imagen (decisión aprobada, opción A): muestran el texto alternativo de la revista o, si falta, un aviso visible, con enlace al original. Se marca con lang todo fragmento en otro idioma.

R9.5. Atribución: antes del texto, la cita completa en estilo APA 7 (decisión aprobada), autoría, revista, DOI, licencia con su nombre completo y enlace a su texto legal, y la nota de que solo se han modificado el formato y la presentación. Al final, la cita repetida con un botón para copiarla. En ambos extremos, el enlace «Ver y citar en la web de la revista», con aviso de salida.

R9.6. Interfaz: cuarta vista de lectura accesible desde el índice del número solo para los artículos que cumplen los criterios, indicados con texto. Un único h1 (el título), tabla de contenidos, línea de unos 65 caracteres, interlineado amplio, tamaño de texto, temas claro, oscuro y de alto contraste, reflujo al 400 por ciento, foco al entrar, título del documento y anuncio. Al volver con el botón atrás, el índice recupera la posición y el foco va al enlace del artículo leído (decisión aprobada).

R9.7. Datos: un archivo por texto en data/textos, cargado solo al abrirlo. Informe aparte de los artículos excluidos y del motivo.
