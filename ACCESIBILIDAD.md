# Accesibilidad

Este documento recoge qué se ha comprobado de forma automática, qué se ha revisado manualmente en el código y qué queda pendiente de revisión manual con VoiceOver y con teclado. El objetivo es WCAG 2.2 nivel AA completo (requisito R2.1 de REQUISITOS.md).

Estado a 18 de octubre de 2026: la aplicación ya usa datos reales de DOAJ y Crossref (41 revistas, 123 números y 1.909 artículos) y se ha retirado el aviso de datos de prueba. Las pruebas de comportamiento pasan con los datos reales y con los de prueba. El análisis con axe, ejecutado en GitHub Actions, da 0 errores con los datos reales (ver 4.1). Falta la revisión manual con tecnologías de apoyo, que es imprescindible: las herramientas automáticas detectan aproximadamente un tercio de los problemas posibles.

## 1. Comprobaciones automáticas

Se ejecutan en cada envío al repositorio con el flujo `.github/workflows/pruebas.yml`, y en local con `npm test` y `npm run lighthouse`.

### 1.1. axe-core (archivo pruebas/axe.spec.js)

Reglas de WCAG 2.0, 2.1 y 2.2 en niveles A y AA, más las buenas prácticas de axe. Se analizan:

1. Las tres vistas: listado, ficha de revista e índice de número.
2. Los estados vacíos: revista sin números, número sin artículos y búsqueda sin resultados.
3. Los estados de carga y de error.
4. Las páginas de revista, número y dirección inexistentes.
5. Cada vista en tema claro, en tema oscuro y a 320 píxeles de ancho (equivalente a un zoom del 400 por ciento en una pantalla de 1280 píxeles).
6. El índice de un número con el texto al 200 por ciento.

Los resúmenes desplegables se abren antes del análisis para que axe revise también su contenido. Resultado con los datos de prueba el 17 de octubre: 0 errores en los 25 análisis.

Desde el 18 de octubre hay además un análisis con los datos reales (archivo pruebas/datos-reales.spec.js): el listado completo y, para cada una de las 41 revistas, su ficha y el índice de su número más reciente, con los resúmenes abiertos. Son 83 análisis más.

Aviso sobre el 18 de octubre: en el entorno de desarrollo en la nube no se pudo instalar axe-core, porque la configuración de red personalizada solo permite doaj.org y crossref.org y deja fuera el registro de npm. Por eso axe se ejecuta solo en GitHub Actions, en el flujo Pruebas, al subir los cambios. El resultado de esa ejecución se anota en la sección 4.

### 1.2. Pruebas de comportamiento (archivo pruebas/comportamiento.spec.js)

1. Idioma del documento declarado como es y presencia de header, nav, main y footer, con un único h1 por vista.
2. El enlace de salto es el primer elemento con foco, se ve al recibirlo y lleva el foco al encabezado principal sin cambiar la dirección.
3. Al cambiar de vista, el foco pasa al h1, el título del documento cambia y se anuncia un resumen en la región activa educada.
4. El botón atrás y el botón adelante del navegador funcionan.
5. Orden alfabético según las reglas del español (la Á junto a la A, la Ñ después de la N) e inversión del orden.
6. El buscador no distingue tildes ni mayúsculas, anuncia el número de resultados y la tecla Intro no recarga la página.
7. La búsqueda vacía explica qué hacer y ofrece un botón para borrarla, que devuelve el foco al campo.
8. Los enlaces externos se abren en una pestaña nueva y lo dicen en su texto visible.
9. Los títulos y resúmenes en inglés llevan lang="en" y los textos en español no llevan un lang propio.
10. Los resúmenes se despliegan con el teclado.
11. Los controles de tamaño de texto funcionan, se anuncian y se recuerdan al recargar.
12. Sin scroll horizontal a 320 píxeles de ancho, tanto con el texto normal como al 200 por ciento.
13. Todos los botones, campos, desplegables y enlaces que no están dentro de un párrafo miden al menos 44 por 44 píxeles.
14. Al recorrer la página con el tabulador, cada elemento enfocado tiene un contorno de al menos 2 píxeles y no queda tapado por otro elemento.
15. Un fallo de red muestra un error con instrucciones y el botón Reintentar recupera la vista.
16. Si los datos tardan, aparece un estado de carga con role="status".
17. Una dirección de número inexistente ofrece enlaces para salir.
18. Los enlaces del contenido están subrayados, así que no dependen solo del color.
19. La aplicación funciona abriendo index.html directamente, sin servidor.

Con los datos reales (pruebas/datos-reales.spec.js):

20. Los datos de la carpeta data no son de prueba: ninguna revista empieza por prueba- ni lleva la marca es_prueba.
21. El listado muestra todas las revistas del archivo de datos.
22. En cada revista y en su número más reciente, cada título y cada resumen lleva exactamente el atributo lang que indica el recolector: ninguno si está en español o si el idioma no está claro, y el código del idioma en otro caso.
23. Sin scroll horizontal a 320 píxeles en el índice de cada número, con títulos y DOI reales.

Resultado local el 18 de octubre: las 90 pruebas de comportamiento pasan, incluidas las de estados de carga, vacío y error. En ese entorno local axe se sustituyó por un módulo vacío, así que esas 90 pruebas no cuentan como análisis de axe.

### 1.3. Lighthouse (archivo lighthouserc.json)

Se analizan las tres vistas. La puntuación de accesibilidad debe ser 100, y si no lo es la prueba falla. Resultado actual: 100 en las tres vistas.

## 2. Revisión manual del código, criterio por criterio

En esta tabla, «Auto» significa que lo cubre una comprobación automática, «Código» que se ha revisado en el código y «Manual» que necesita tu revisión con VoiceOver o con teclado (sección 3).

| Criterio | Cómo se cumple | Verificación |
|---|---|---|
| 1.1.1 Contenido no textual | No hay imágenes de contenido. Las decoraciones (separador de las migas y triángulo del resumen) son formas dibujadas con bordes en CSS, sin caracteres, para que los lectores de pantalla no las lean. | Auto, Código |
| 1.3.1 Información y relaciones | Encabezados jerárquicos, listas, listas de definiciones para los metadatos, etiquetas asociadas a los campos y puntos de referencia. | Auto, Manual |
| 1.3.2 Secuencia con significado | El orden del DOM coincide con el visual. | Código, Manual |
| 1.3.4 Orientación | No se bloquea ninguna orientación. | Código |
| 1.3.5 Propósito de los campos | El buscador no pide datos personales, así que no se aplica autocomplete. | Código |
| 1.4.1 Uso del color | Enlaces subrayados, estados con texto, botones no disponibles con borde discontinuo y aria-disabled. | Auto, Código |
| 1.4.3 Contraste del texto | Colores elegidos con al menos 4,5 a 1 en los dos temas; los valores están comentados en estilos.css. | Auto |
| 1.4.4 Cambio de tamaño del texto | Todo va en rem; hay controles de hasta el 200 por ciento y se respeta el tamaño del navegador. | Auto |
| 1.4.5 Imágenes de texto | No hay. | Código |
| 1.4.10 Reflujo | Sin scroll horizontal a 320 píxeles. | Auto |
| 1.4.11 Contraste de componentes | Bordes y foco con al menos 3 a 1. | Código, Manual |
| 1.4.12 Espaciado del texto | No hay alturas fijas en contenedores de texto. | Código, Manual |
| 1.4.13 Contenido al pasar el ratón o con el foco | No hay tooltips ni contenido emergente. | Código |
| 2.1.1 Teclado y 2.1.2 Sin trampas | Solo se usan elementos nativos: enlaces, botones, campos y details. | Auto, Manual |
| 2.1.4 Atajos de una sola tecla | No hay. | Código |
| 2.2.1 y 2.2.2 Tiempo y movimiento | No hay límites de tiempo. La única animación es el indicador de carga, que se detiene con movimiento reducido. | Código |
| 2.3.1 Destellos | No hay. | Código |
| 2.4.1 Saltar bloques | Enlace de salto y puntos de referencia. | Auto |
| 2.4.2 Título de página | Cambia en cada vista. | Auto |
| 2.4.3 Orden del foco | Lógico; el foco va al h1 al cambiar de vista. | Auto, Manual |
| 2.4.4 Propósito de los enlaces | Los enlaces «Leer en la web de la revista» incluyen el título del artículo en texto oculto. | Código, Manual |
| 2.4.5 Múltiples vías | Listado con buscador, migas de pan y direcciones directas. | Código |
| 2.4.6 Encabezados y etiquetas | Descriptivos. | Manual |
| 2.4.7 Foco visible | Contorno de 3 píxeles con halo, también en colores forzados. | Auto |
| 2.4.11 Foco no tapado | No hay elementos fijos ni pegajosos. | Auto |
| 2.5.1 a 2.5.4 Puntero, cancelación, etiqueta en el nombre y movimiento | Solo hay pulsaciones simples sobre controles nativos; el nombre accesible empieza siempre por el texto visible. | Código |
| 2.5.7 Movimientos de arrastre | No hay. | Código |
| 2.5.8 Tamaño del objetivo | 44 por 44 píxeles. | Auto |
| 3.1.1 Idioma de la página | lang="es". | Auto |
| 3.1.2 Idioma de las partes | lang en títulos y resúmenes en otros idiomas. | Auto, Manual |
| 3.2.1 y 3.2.2 Al recibir el foco o al introducir datos | El buscador filtra la lista sin cambiar de vista ni mover el foco. | Código, Manual |
| 3.2.3 y 3.2.4 Navegación e identificación coherentes | La misma cabecera, migas y pie en todas las vistas; los enlaces externos siempre con el mismo aviso. | Código |
| 3.2.6 Ayuda coherente | No hay mecanismo de ayuda. | No aplica |
| 3.3.1 a 3.3.4 Errores y etiquetas | Etiqueta visible y ayuda en el buscador; los errores dicen qué ha pasado y qué hacer. No hay envío de datos. | Auto, Código |
| 3.3.7 y 3.3.8 Entrada redundante y autenticación | No hay formularios de varios pasos ni autenticación. | No aplica |
| 4.1.2 Nombre, función y valor | Elementos nativos; aria-disabled, aria-current y aria-describedby donde hace falta. | Auto |
| 4.1.3 Mensajes de estado | Región aria-live="polite" para cambios de vista, resultados de búsqueda y tamaño del texto; role="status" en la carga. | Auto, Manual |

### Decisiones de diseño

1. En la primera carga no se mueve el foco. Así el lector de pantalla empieza por el principio de la página, como en cualquier web, y puede usar el enlace de salto. El foco solo se mueve en los cambios de vista.
2. El anuncio de la región activa no repite el h1, que VoiceOver ya lee al recibir el foco. Añade información nueva, por ejemplo «Ficha de la revista cargada. 3 números disponibles».
3. El estado de carga solo aparece si los datos tardan más de 400 milisegundos. Así se evita que VoiceOver diga «Cargando» y justo después la vista nueva en cada navegación rápida.
4. Los resultados de búsqueda se anuncian 700 milisegundos después de dejar de escribir, para no interrumpir cada letra. Pulsar Intro los anuncia al momento.
5. Los botones de tamaño de texto que no se pueden usar en ese momento se marcan con aria-disabled en lugar de disabled. Así siguen siendo enfocables y, al pulsarlos, explican por qué no hacen nada.
6. El idioma solo se marca cuando la fuente lo declara o cuando el detector del recolector está seguro. Un lang equivocado hace que VoiceOver lea peor que si no se marca. Crossref no informa del idioma de los artículos de estas revistas, así que todo se decide con el detector. Con los datos reales se mejoró: ahora reconoce títulos cortos en portugués, francés, catalán, italiano, inglés y polaco por sus palabras propias y su ortografía (por ejemplo «ção», «ã» o «l·l»), que antes se quedaban sin marcar y VoiceOver los habría leído con voz española.
7. Los enlaces externos se abren en una pestaña nueva, como decidiste, y lo anuncian en su texto visible, no solo en un atributo: así lo saben también quienes ven la pantalla o usan control por voz.
8. Los resúmenes van en un desplegable details para que el índice sea más corto de recorrer. Su texto incluye el título del artículo en texto oculto para distinguirlos en el rotor de VoiceOver.
9. No hay cabecera fija: así el foco nunca queda tapado al hacer zoom.
10. Los nombres de revista son nombres propios, que WCAG 3.1.2 exime de marcar. Aun así, si el detector está seguro del idioma se marca, para que VoiceOver los pronuncie mejor. Con los datos actuales solo ocurre con Journal of the Academy, en inglés.
11. Los resúmenes que solo contienen un encabezado suelto, como «Resumen» o un guion, se descartan y la aplicación dice «Resumen no disponible en la fuente», en lugar de abrir un desplegable vacío.

## 3. Pendiente de revisión manual

### 3.1. VoiceOver en Mac (Safari)

1. Al pulsar el enlace de salto, VoiceOver lee el h1 de la vista.
2. Al entrar en una revista y en un número, VoiceOver lee el h1 nuevo y después el anuncio, sin cortes ni repeticiones molestas.
3. En el rotor, los encabezados, puntos de referencia y enlaces aparecen con nombres claros y sin duplicados confusos.
4. Al escribir en el buscador, el anuncio del número de resultados llega en un momento razonable y no interrumpe la escritura.
5. Al leer un título o un resumen en inglés, VoiceOver cambia a la voz inglesa y vuelve a la española después.
6. Los desplegables de resumen anuncian su estado: contraído o expandido.
7. Los botones de tamaño de texto anuncian que están atenuados o no disponibles cuando corresponde, y el cambio de tamaño se anuncia.
8. El estado de error y el botón Reintentar se entienden sin ver la pantalla. Para probarlo, desactiva la red con las herramientas de desarrollo de Safari.

### 3.2. VoiceOver en iPhone (Safari)

1. Los gestos de deslizar recorren la página en un orden lógico.
2. Tras tocar dos veces un enlace de revista o de número, el foco de VoiceOver va al h1 nuevo. Safari en iOS es el entorno donde más falla la gestión del foco en este tipo de aplicaciones, así que es la prueba más importante.
3. El rotor permite saltar por encabezados y enlaces.
4. Los enlaces externos abren una pestaña nueva, y al volver a la pestaña de la aplicación el foco sigue donde estaba.
5. Con el tamaño de texto del sistema al máximo (Tamaño del texto más grande) y los controles de la aplicación, no se corta ni se solapa nada.

### 3.3. Solo con teclado (Safari, Chrome y Firefox)

1. En Safari para Mac, activa en Ajustes, Avanzado, la opción de pulsar Tab para resaltar cada elemento.
2. Recorre las tres vistas con Tab y Mayúsculas más Tab: el foco siempre se ve y sigue el orden visual.
3. Despliega los resúmenes con Intro y con la barra espaciadora.
4. Cambia el orden con las flechas del desplegable.

### 3.4. Otras comprobaciones visuales

1. Zoom del navegador al 400 por ciento en una ventana de 1280 píxeles de ancho.
2. Modo de alto contraste de Windows (colores forzados) y Aumentar contraste en macOS e iOS.
3. Reducir movimiento en macOS e iOS: el indicador de carga no gira.
4. Espaciado de texto ampliado con un marcador como el de WCAG 1.4.12.

## 4. Comprobado con los datos reales y pendiente

### 4.1. Comprobado el 18 de octubre de 2026

1. Las 41 revistas, 123 números y 1.909 artículos proceden de DOAJ y Crossref. Todos los artículos enlazan a su DOI en doi.org. Se han eliminado las cinco revistas ficticias de la carpeta data y el aviso visible de datos de prueba.
2. Idiomas marcados en los títulos de artículo: 943 en español (sin lang propio), 421 en portugués, 210 en inglés, 28 en francés, 27 en polaco y 4 en catalán; 276 sin idioma claro, que heredan el español. En los 1.711 resúmenes: 893 en español, 406 en portugués, 347 en inglés, 29 en polaco, 16 en francés, 8 en catalán y 12 sin idioma claro.
3. Las pruebas de comportamiento, incluidos los estados de carga, vacío y error, pasan con los datos reales y con los de prueba.
4. Resultado de axe en GitHub Actions (flujo Pruebas, ejecución 39102437024, commit 52540f1): pasan las 90 pruebas, con 0 errores de axe tanto con los datos de prueba como con los datos reales de las 41 revistas. Lighthouse sigue dando 100 en accesibilidad en las tres vistas.

### 4.2. Pendiente de revisión manual con VoiceOver

1. Escuchar varios artículos en portugués, inglés, francés y polaco y confirmar que VoiceOver cambia de voz en el título y en el resumen, y que vuelve a la voz española después.
2. Revisar los títulos sin idioma claro. La mayoría están en español, pero quedan algunos portugueses muy cortos, como «Território Palimpsesto», que VoiceOver leerá con voz española. Si molestan, se puede añadir una corrección manual por artículo.
3. Revisar los resúmenes bilingües, en los que la fuente junta el texto en dos idiomas: no se marcan para no equivocar la voz en la mitad del texto.
4. Comprobar con VoiceOver que la lectura de los índices largos, de hasta 37 artículos, sigue siendo cómoda con el rotor de encabezados.
5. Escuchar las etiquetas de número poco habituales que vienen de Crossref, como «núm. sp26» o «Publicación continua», y decidir si se entienden.
6. Revisar en data/informe-no-resueltas.md las 9 revistas pendientes y la revista Cultura-Hombre-Sociedad, que se muestra con números de 2021 porque Crossref no tiene otros más recientes y su web no se pudo consultar.

## 5. Versión de prueba en un solo archivo (dist/revistas-prueba.html)

Generada el 18 de octubre de 2026 con herramientas/empaquetar.py para revisar la aplicación con VoiceOver sin publicarla. Contiene las 41 revistas con todos sus números, artículos y resúmenes, y los 133 textos completos, sin recortes. Ocupa 6,37 MB porque los textos completos van comprimidos con gzip dentro del archivo (sin comprimir ocupaba 11,53 MB); cada texto se descomprime solo al abrirlo, con el propio navegador y sin peticiones externas.

### 5.1. Comprobado

1. El archivo no contiene ninguna referencia a recursos externos: ni scripts, ni hojas de estilo, ni fuentes, ni imágenes. El único icono va incrustado. El script de empaquetado lo comprueba cada vez y falla si encuentra alguna, y hay pruebas unitarias que confirman que el comprobador las detecta.
2. Una política de seguridad de contenido incluida en el archivo bloquea cualquier petición a internet o a otros archivos.
3. Al recorrer las tres vistas con el archivo abierto directamente, el navegador no hace ninguna petición fuera de él ni registra avisos de esa política (pruebas/paquete.spec.js).
4. Se mantienen las rutas con almohadilla y el botón atrás, el foco en el h1 al cambiar de vista, el cambio de título, los anuncios de la región activa, los estados vacíos y de página no encontrada, y el estado de error con el botón Reintentar.
5. Los enlaces a las webs de las revistas y los artículos siguen funcionando, se abren en una pestaña nueva y lo dicen en su texto visible.
6. Con datos reales no aparece el aviso de datos de prueba; con datos de prueba sí. El pie indica la fecha y hora de generación de los datos y del archivo.
7. Al preparar estas pruebas se encontró y corrigió un fallo: si un archivo de datos llegaba con un formato incorrecto, Reintentar reutilizaba la copia dañada. Ahora Reintentar vacía la memoria de datos antes de volver a cargar.
8. Variante para el artefacto privado de Claude (dist/revistas-artefacto.html): es la misma página sin las etiquetas de documento, porque el visor de Claude pone las suyas. Ese visor no declara idioma, así que un script al principio pone lang="es" en la raíz. Las pruebas imitan el esqueleto del visor y comprueban el idioma, las rutas, el foco, los anuncios y axe.
9. Los colores siguen tanto la preferencia del sistema como el tema que elija el visor de Claude (atributo data-theme), en las dos combinaciones cruzadas.
10. Resultado de axe sobre el archivo en GitHub Actions (flujo Pruebas, ejecución 39106535115, commit 36dc2db): pasan las 147 pruebas, con 0 errores de axe en el archivo único con datos reales (listado, ficha y último número de las 41 revistas), con datos de prueba (estados vacíos, no encontrado, búsqueda sin resultados y error) y en la variante para el visor de artefactos, en tema claro y oscuro. Las pruebas de la versión con servidor siguen pasando y Lighthouse sigue dando 100.

### 5.2. Diferencias con la versión definitiva

1. El estado de carga sigue en el código, pero en esta versión no llega a verse: los datos están dentro del archivo y aparecen al instante. Para revisarlo con VoiceOver hay que usar la versión con servidor.
2. El error de conexión no puede producirse, porque no hay conexión. El estado de error solo aparece si los datos del archivo estuvieran dañados.
3. Los datos son una foto fija del momento en que se generó el archivo: no se actualizan cada semana. Para tener datos nuevos hay que volver a generar el archivo.
4. El archivo completo, de unos 3 MB, se carga de una vez. En un iPhone antiguo la primera apertura puede tardar uno o dos segundos más que la versión con servidor.
5. Si se abre como artefacto privado en claude.ai, la aplicación se muestra dentro de la página de Claude. Al empezar, el foco de VoiceOver puede quedar en los controles de Claude y no en el enlace de salto. Es una diferencia del visor, no de la aplicación.
6. Para leer los textos completos hace falta un navegador que sepa descomprimir: Safari 16.4 o posterior en iPhone y Mac, o una versión reciente de Chrome, Edge o Firefox. En un navegador más antiguo, la lectura muestra un mensaje que explica qué hacer y ofrece salir al índice; el resto de la aplicación funciona igual.
7. El tamaño de texto elegido puede no recordarse entre visitas si el navegador o el visor no permiten el almacenamiento local del archivo. La aplicación sigue funcionando sin él.

### 5.3. Pendiente de revisión manual con VoiceOver en esta versión

1. Comprobar en el iPhone que, tras abrir el archivo, el gesto de deslizar empieza por el enlace de salto y recorre la cabecera, las migas, el contenido y el pie.
2. Repetir en esta versión las pruebas de la sección 3.2, sobre todo que el foco vaya al h1 nuevo tras tocar dos veces un enlace de revista o de número.
3. Comprobar que al volver de un enlace externo a la pestaña del archivo se conserva la vista y el foco.
4. Abrir varios textos completos largos en el iPhone y comprobar que la descompresión no produce una espera molesta ni un anuncio confuso.

## 6. Vista de lectura del texto completo

Estado a 18 de octubre de 2026: la vista de lectura está probada con un artículo ficticio de pruebas/datos y con los 133 textos reales recogidos (118 de galeradas HTML y 15 de XML JATS), de 9 revistas. El detalle de incluidos y excluidos está en data/informe-texto-completo.md.

### 6.1. Comprobado de forma automática (pruebas/lectura.spec.js)

1. En el índice del número, cada artículo dice con texto si se puede leer en la aplicación («Lectura completa disponible en esta aplicación») o no («Texto completo solo en la web de la revista»). El enlace «Leer el artículo completo» incluye el título en texto oculto.
2. Al entrar en la lectura hay un único h1, el título del artículo, que recibe el foco; cambian el título del documento y las migas, y se anuncian las secciones, la licencia y las figuras sin descripción.
3. Antes del texto aparecen la autoría, la revista, el DOI, la licencia con su nombre completo y el enlace a su texto legal, la cita completa en estilo APA 7, la nota de que solo se han modificado el formato y la presentación, los avisos de derechos del original y el enlace «Ver y citar en la web de la revista». Al final se repiten la cita, el botón «Copiar la cita» y ese enlace.
4. La tabla de contenidos y los enlaces a notas y referencias mueven el foco sin cambiar de vista, y cada nota tiene un enlace «Volver al texto».
5. Las figuras no muestran la imagen: muestran la descripción de la revista o, si falta, un aviso visible, siempre con enlace al original. Las tablas conservan su leyenda y sus cabeceras, y las anchas se desplazan dentro de un marco que se puede recorrer con el teclado.
6. Los párrafos en otro idioma llevan su atributo lang.
7. El botón «Copiar la cita» copia la cita exacta y lo anuncia; si el navegador no deja copiar, selecciona la cita y explica cómo copiarla.
8. Al volver con el botón atrás, el índice recupera su posición, el foco va al enlace del artículo leído y se anuncia «Has vuelto al índice del número, en el artículo que estabas leyendo». Es una excepción razonada a la regla de llevar el foco al h1, aprobada por el responsable del proyecto.
9. El tema de colores (automático, claro, oscuro y alto contraste) se elige en la cabecera, se anuncia y se recuerda. El alto contraste es blanco sobre negro, con enlaces amarillos (19,6 a 1) y foco cian.
10. Sin scroll horizontal a 320 y a 1280 píxeles con el texto al 200 por ciento; la línea de lectura no pasa de unos 75 caracteres y el interlineado es de 1,75.
11. axe en la vista de lectura con el tema automático claro y oscuro, a 320 píxeles, con el texto al 200 por ciento y con los temas claro, oscuro y alto contraste elegidos en la aplicación; también en el índice con cada tema y en la página de un artículo sin texto completo.
12. En el archivo único, la lectura funciona sin ninguna petición externa.
13. Con los datos reales, cada texto completo que se recoja se abrirá en las pruebas para comprobar el h1, la licencia, el idioma, la ausencia de imágenes y scripts, el reflujo y axe (pruebas/datos-reales.spec.js).

Resultado de axe en GitHub Actions (flujo Pruebas, ejecución 39117520310, commit 32f9cb8): pasan las 170 pruebas, con 0 errores de axe en todas las vistas, incluida la de lectura. La ejecución anterior encontró dos problemas que se corrigieron: las notas se pintaban como regiones complementarias (aside) dentro de otra región, y a 320 píxeles con el texto al 200 por ciento la indicación «Lectura completa disponible» y la última miga provocaban scroll horizontal con la fuente DejaVu Sans. Ahora hay una prueba de reflujo con esa fuente.

### 6.2. Comprobado con los textos reales

1. Cada uno de los 133 textos se abre en las pruebas: un único h1 con el título, la licencia en la atribución, el atributo lang del texto según su idioma (111 en español, 14 en inglés, 7 en portugués y 1 en francés), ninguna imagen, script ni marco, y sin scroll horizontal a 320 píxeles.
2. El recolector comprobó que el texto convertido es idéntico al original en todos ellos; 23 artículos se excluyeron por no superar esa comprobación o por contener fórmulas u otros elementos que no se pueden reproducir con fidelidad.
3. Los textos tienen 665 figuras, de las que 480 no traen descripción de la revista: todas muestran el aviso visible y el enlace al original.
4. axe sin errores en los 133 textos, tras corregir lo que encontró con los textos reales: llamadas a nota y enlaces de vuelta menores de 24 por 24 píxeles (ahora tienen ese tamaño mínimo), celdas de cabecera vacías en la esquina de algunas tablas (ahora se muestran como celdas normales), y enlaces dentro de otros enlaces, que aparecían cuando una nota enlazaba de vuelta a la llamada o cuando una figura del original estaba dentro de un enlace (ahora el interior se muestra como texto). Ninguna corrección cambia el texto del artículo. Hay pruebas que lo comprueban en cada texto real.
5. 76 textos no tienen encabezados en el original (son documentos de procesador de texto exportados con párrafos en negrita), así que no tienen tabla de contenidos. No se han inventado encabezados para no modificar el texto.

### 6.3. Pendiente de revisión manual con VoiceOver

1. Recorrer con el rotor los encabezados de un artículo largo y comprobar que la jerarquía se entiende.
2. Activar una llamada a nota, escuchar la nota y volver con «Volver al texto» en Mac y en iPhone; confirmar que VoiceOver sigue el foco.
3. Escuchar el bloque de atribución y la cita, y probar «Copiar la cita» en Safari para iPhone, donde el portapapeles puede pedir permiso.
4. Comprobar que el aviso de figura sin descripción se entiende sin ver la pantalla.
5. Recorrer una tabla ancha con los gestos de tabla de VoiceOver.
6. Volver con el botón atrás desde la lectura en iPhone y confirmar que el foco queda en el enlace del artículo leído.
7. Revisar con los textos reales que el cambio de voz en párrafos en otro idioma es correcto, sobre todo en los 14 textos en inglés y los 7 en portugués.
8. Recorrer alguno de los 76 textos sin encabezados para valorar si se puede leer cómodamente sin tabla de contenidos.
9. Escuchar varias figuras sin descripción para comprobar que el aviso no resulta repetitivo en los textos con muchas figuras.
