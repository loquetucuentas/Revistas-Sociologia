# Accesibilidad

Este documento recoge qué se ha comprobado de forma automática, qué se ha revisado manualmente en el código y qué queda pendiente de revisión manual con VoiceOver y con teclado. El objetivo es WCAG 2.2 nivel AA completo (requisito R2.1 de REQUISITOS.md).

Estado a 17 de octubre de 2026: todas las comprobaciones automáticas pasan con los datos de prueba. Falta la revisión manual con tecnologías de apoyo, que es imprescindible: las herramientas automáticas detectan aproximadamente un tercio de los problemas posibles.

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

Los resúmenes desplegables se abren antes del análisis para que axe revise también su contenido. Resultado: 0 errores en los 25 análisis.

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
6. El idioma solo se marca cuando la fuente lo declara o cuando el detector del recolector está seguro. Un lang equivocado hace que VoiceOver lea peor que si no se marca.
7. Los enlaces externos se abren en una pestaña nueva, como decidiste, y lo anuncian en su texto visible, no solo en un atributo: así lo saben también quienes ven la pantalla o usan control por voz.
8. Los resúmenes van en un desplegable details para que el índice sea más corto de recorrer. Su texto incluye el título del artículo en texto oculto para distinguirlos en el rotor de VoiceOver.
9. No hay cabecera fija: así el foco nunca queda tapado al hacer zoom.

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

## 4. Pendiente cuando haya datos reales

1. Volver a pasar las pruebas automáticas y la revisión con VoiceOver con los datos reales: títulos muy largos, resúmenes extensos y caracteres especiales.
2. Revisar si el detector de idioma marca bien los textos reales. En particular los resúmenes bilingües, que no se marcan, y los textos en catalán, gallego o portugués.
3. Revisar en data/informe-no-resueltas.md las revistas que no se han podido resolver.
