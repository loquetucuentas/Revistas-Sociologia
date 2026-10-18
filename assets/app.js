/*
  Explorador de revistas de sociología en acceso abierto.
  Aplicación de una sola página sin dependencias externas.

  Rutas (con almohadilla, para que el botón atrás funcione):
    #/                                  listado de revistas
    #/revista/<id>                      ficha de una revista
    #/revista/<id>/numero/<numero>      índice de un número

  En cada cambio de vista: se pinta el contenido, se actualiza el título
  del documento, el foco pasa al encabezado de primer nivel y se anuncia
  un resumen de la vista en una región activa educada.
*/
(function () {
  'use strict';

  var NOMBRE_APP = 'Revistas de sociología en acceso abierto';
  var RETRASO_CARGA = 400;      // ms antes de mostrar el estado de carga
  var RETRASO_ANUNCIO = 700;    // ms de pausa al escribir antes de anunciar resultados
  var TAMANOS = [100, 125, 150, 175, 200];
  var CLAVE_TAMANO = 'revistas-sociologia:tamano-texto';
  var AVISO_EXTERNO = '(sitio externo, se abre en una pestaña nueva)';

  var colador = new Intl.Collator('es', { sensitivity: 'base', numeric: true });
  var estado = {
    busqueda: '',
    orden: 'asc',
    cache: {},
    peticion: 0,
    primeraVista: true,
    temporizadorAnuncio: null
  };

  var principal = document.getElementById('contenido');
  var regionAnuncios = document.getElementById('anuncios');
  var migas = document.getElementById('migas');

  /* Utilidades del DOM */

  // Crea un elemento. Los textos se insertan siempre como texto, nunca como HTML.
  function el(etiqueta, atributos) {
    var nodo = document.createElement(etiqueta);
    var nombre;
    for (nombre in atributos || {}) {
      var valor = atributos[nombre];
      if (valor === null || valor === undefined || valor === false) continue;
      if (nombre.indexOf('on') === 0) nodo.addEventListener(nombre.slice(2).toLowerCase(), valor);
      else if (nombre === 'texto') nodo.textContent = valor;
      else nodo.setAttribute(nombre === 'clase' ? 'class' : nombre, valor === true ? '' : valor);
    }
    for (var i = 2; i < arguments.length; i++) anadir(nodo, arguments[i]);
    return nodo;
  }

  function anadir(nodo, hijo) {
    if (hijo === null || hijo === undefined || hijo === false) return;
    if (Array.isArray(hijo)) { hijo.forEach(function (h) { anadir(nodo, h); }); return; }
    nodo.appendChild(typeof hijo === 'string' || typeof hijo === 'number' ? document.createTextNode(String(hijo)) : hijo);
  }

  // Marca el idioma de un texto si no es español, para que VoiceOver cambie de voz.
  function conIdioma(nodo, codigo) {
    if (codigo && /^[a-z]{2,3}(-[a-z0-9]+)*$/i.test(codigo) && codigo.toLowerCase() !== 'es') {
      nodo.setAttribute('lang', codigo);
    }
    return nodo;
  }

  // Nombre de una revista con su idioma marcado, para usarlo dentro de otros textos.
  function nombreRevista(revista) {
    return conIdioma(el('span', null, revista.titulo), revista.idioma_titulo);
  }

  function urlSegura(url) {
    return typeof url === 'string' && /^https?:\/\//i.test(url) ? url : null;
  }

  function normalizar(texto) {
    return String(texto || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }

  function plural(n, singular, varios) {
    return n + ' ' + (n === 1 ? singular : varios);
  }

  function ruta() {
    return '#/' + Array.prototype.map.call(arguments, encodeURIComponent).join('/');
  }

  // Enlace a un sitio externo: se abre en una pestaña nueva y lo avisa con texto visible.
  function enlaceExterno(url, texto, oculto, idiomaOculto) {
    var segura = urlSegura(url);
    if (!segura) return null;
    return el('a', { href: segura, target: '_blank', rel: 'noopener', clase: 'enlace-externo' },
      el('span', null, texto),
      oculto ? el('span', { clase: 'solo-lector' }, ': ', conIdioma(el('span', null, oculto), idiomaOculto)) : null,
      ' ',
      el('span', { clase: 'enlace-externo__aviso' }, AVISO_EXTERNO));
  }

  function anunciar(texto) {
    // Se vacía primero para que se anuncie aunque el texto se repita.
    regionAnuncios.textContent = '';
    window.setTimeout(function () { regionAnuncios.textContent = texto; }, 120);
  }

  var formatoFecha = {
    dia: new Intl.DateTimeFormat('es', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }),
    mes: new Intl.DateTimeFormat('es', { month: 'long', year: 'numeric', timeZone: 'UTC' })
  };

  function fechaLegible(texto) {
    var partes = /^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?/.exec(texto || '');
    if (!partes) return null;
    var fecha = new Date(Date.UTC(+partes[1], (+partes[2] || 1) - 1, +partes[3] || 1));
    if (partes[3]) return formatoFecha.dia.format(fecha);
    if (partes[2]) return formatoFecha.mes.format(fecha);
    return partes[1];
  }

  function nombreDe(tipo, codigo) {
    if (!codigo) return null;
    try {
      var nombre = new Intl.DisplayNames(['es'], { type: tipo }).of(tipo === 'region' ? codigo.toUpperCase() : codigo);
      return nombre ? nombre.charAt(0).toUpperCase() + nombre.slice(1) : codigo;
    } catch (e) {
      return codigo;
    }
  }

  /* Datos */

  function ErrorDatos(tipo, detalle) {
    this.tipo = tipo;          // 'no-encontrado', 'red' o 'datos'
    this.detalle = detalle;
  }

  // Abierta con doble clic (file:), el navegador no permite fetch de archivos
  // locales; en ese caso se cargan las copias .js que genera el recolector.
  function cargarScript(archivo) {
    return new Promise(function (resolver, rechazar) {
      var almacen = window.DATOS_REVISTAS || {};
      if (almacen[archivo]) { resolver(almacen[archivo]); return; }
      var script = document.createElement('script');
      script.src = 'data/' + archivo.replace(/\.json$/, '.js');
      script.onload = function () {
        script.remove();
        var datos = (window.DATOS_REVISTAS || {})[archivo];
        if (datos) resolver(datos);
        else rechazar(new ErrorDatos('datos', 'El archivo de datos está vacío o dañado.'));
      };
      script.onerror = function () {
        script.remove();
        rechazar(new ErrorDatos('red', 'No se ha podido leer el archivo de datos.'));
      };
      document.head.appendChild(script);
    });
  }

  function cargarDatos(archivo) {
    if (estado.cache[archivo]) return estado.cache[archivo];
    var promesa;
    if (location.protocol === 'file:') {
      promesa = cargarScript(archivo);
    } else {
      promesa = fetch('data/' + archivo, { cache: 'no-cache' }).then(function (respuesta) {
        if (respuesta.status === 404) throw new ErrorDatos('no-encontrado', 'El archivo de datos no existe.');
        if (!respuesta.ok) throw new ErrorDatos('red', 'El servidor ha respondido con el código ' + respuesta.status + '.');
        return respuesta.json().catch(function () {
          throw new ErrorDatos('datos', 'El archivo de datos está dañado.');
        });
      }, function () {
        throw new ErrorDatos('red', 'No hay conexión con el servidor.');
      });
    }
    estado.cache[archivo] = promesa;
    // Si falla, se olvida para que «Reintentar» vuelva a pedirlo.
    promesa.catch(function () { delete estado.cache[archivo]; });
    return promesa;
  }

  function cargarListado() {
    return cargarDatos('revistas.json').then(function (datos) {
      if (!datos || !Array.isArray(datos.revistas)) throw new ErrorDatos('datos', 'El listado de revistas no tiene el formato esperado.');
      actualizarPie(datos.generado);
      return datos;
    });
  }

  // El identificador de la dirección solo se usa para buscar en el listado;
  // nunca se construye una ruta de archivo con él directamente.
  function cargarRevista(id) {
    return cargarListado().then(function (listado) {
      var ficha = listado.revistas.find(function (r) { return r.id === id; });
      if (!ficha || !ficha.archivo) throw new ErrorDatos('no-encontrado', 'revista');
      return cargarDatos(ficha.archivo).then(function (datos) {
        if (!datos || !datos.revista || !Array.isArray(datos.numeros)) {
          throw new ErrorDatos('datos', 'Los datos de la revista no tienen el formato esperado.');
        }
        return datos;
      });
    });
  }

  function actualizarPie(generado) {
    var fecha = fechaLegible(generado);
    document.getElementById('pie-actualizacion').textContent =
      fecha ? 'Datos actualizados el ' + fecha + '. Se actualizan automáticamente cada semana.' : '';
  }

  /* Enrutador */

  function leerRuta() {
    var hash = location.hash.replace(/^#/, '');
    if (hash.charAt(0) !== '/' || hash === '/') return { vista: 'listado' };
    var partes = hash.slice(1).replace(/\/$/, '').split('/').map(function (p) {
      try { return decodeURIComponent(p); } catch (e) { return p; }
    });
    if (partes[0] === 'revista' && partes.length === 2) return { vista: 'revista', id: partes[1] };
    if (partes[0] === 'revista' && partes.length === 4 && partes[2] === 'numero') {
      return { vista: 'numero', id: partes[1], numero: partes[3] };
    }
    return { vista: 'no-encontrada' };
  }

  function construir(destino) {
    if (destino.vista === 'listado') return cargarListado().then(vistaListado);
    if (destino.vista === 'revista') return cargarRevista(destino.id).then(vistaRevista);
    if (destino.vista === 'numero') {
      return cargarRevista(destino.id).then(function (datos) {
        var numero = datos.numeros.find(function (n) { return n.id === destino.numero; });
        if (!numero) throw new ErrorDatos('no-encontrado', 'numero', datos);
        return vistaNumero(datos, numero);
      });
    }
    return Promise.resolve(vistaNoEncontrada());
  }

  function mostrar() {
    var destino = leerRuta();
    var peticion = ++estado.peticion;
    // Solo se muestra «Cargando» si los datos tardan; así no hay parpadeos.
    var temporizador = window.setTimeout(function () {
      if (peticion === estado.peticion) pintar(vistaCargando(destino));
    }, RETRASO_CARGA);

    construir(destino).catch(function (error) {
      return vistaError(destino, error);
    }).then(function (vista) {
      window.clearTimeout(temporizador);
      if (peticion === estado.peticion) pintar(vista);
    });
  }

  function pintar(vista) {
    principal.replaceChildren(vista.contenido);
    document.title = vista.titulo ? vista.titulo + ' · ' + NOMBRE_APP : NOMBRE_APP;
    pintarMigas(vista.migas || []);
    if (vista.alPintar) vista.alPintar();

    // En la primera carga no se mueve el foco: el lector empieza por el
    // principio de la página y puede usar el enlace de salto.
    if (estado.primeraVista && !vista.esCarga) {
      estado.primeraVista = false;
      return;
    }
    var titulo = principal.querySelector('h1');
    window.scrollTo(0, 0);
    if (titulo) titulo.focus({ preventScroll: true });
    if (vista.anuncio) anunciar(vista.anuncio);
  }

  function pintarMigas(lista) {
    var elementos = [{ texto: 'Inicio', href: '#/' }].concat(lista);
    migas.replaceChildren.apply(migas, elementos.map(function (miga, i) {
      var ultima = i === elementos.length - 1;
      return el('li', null, ultima
        ? el('span', { 'aria-current': 'page' }, conIdioma(el('span', null, miga.texto), miga.idioma))
        : el('a', { href: miga.href }, conIdioma(el('span', null, miga.texto), miga.idioma)));
    }));
  }

  function encabezado(texto, idioma) {
    return conIdioma(el('h1', { tabindex: '-1' }, texto), idioma);
  }

  /* Vistas */

  function vistaCargando(destino) {
    var que = { listado: 'el listado de revistas', revista: 'la ficha de la revista', numero: 'el índice del número' }[destino.vista] || 'los datos';
    return {
      titulo: 'Cargando',
      esCarga: true,
      anuncio: 'Cargando ' + que + '.',
      contenido: el('div', null,
        encabezado('Cargando…'),
        el('p', { clase: 'estado cargando', role: 'status' }, 'Cargando ' + que + '. Espera un momento.'))
    };
  }

  function vistaListado(datos) {
    var revistas = datos.revistas.slice();
    var contenedor = el('div');
    var recuento = el('p', { clase: 'recuento', id: 'recuento' });
    var lista = el('ul', { clase: 'lista', id: 'lista-revistas' });
    var vacio = el('div', { clase: 'estado', hidden: true });
    var campo = el('input', {
      type: 'search', id: 'busqueda', name: 'busqueda', autocomplete: 'off', spellcheck: 'false',
      'aria-describedby': 'busqueda-ayuda', value: estado.busqueda
    });
    campo.value = estado.busqueda;
    var borrar = el('button', { type: 'button', clase: 'boton boton--secundario', onClick: function () {
      if (!campo.value) { anunciar('El buscador ya está vacío.'); campo.focus(); return; }
      campo.value = '';
      actualizar('inmediato');
      campo.focus();
    } }, 'Borrar', el('span', { clase: 'solo-lector' }, ' la búsqueda'));
    var selector = el('select', { id: 'orden', name: 'orden', onChange: function () {
      estado.orden = selector.value;
      actualizar();
      anunciar(selector.value === 'asc' ? 'Revistas ordenadas de la A a la Z.' : 'Revistas ordenadas de la Z a la A.');
    } },
      el('option', { value: 'asc' }, 'Alfabético, de la A a la Z'),
      el('option', { value: 'desc' }, 'Alfabético, de la Z a la A'));
    selector.value = estado.orden;

    function tarjeta(revista) {
      var datosRevista = el('dl', { clase: 'metadatos' });
      [['Editorial', revista.editorial], ['País', nombreDe('region', revista.pais)], ['Último número', revista.ultimo_numero]]
        .forEach(function (par) { if (par[1]) anadir(datosRevista, [el('dt', null, par[0]), el('dd', null, par[1])]); });
      return el('li', { clase: 'tarjeta' },
        el('h3', { clase: 'tarjeta__titulo' }, el('a', { href: ruta('revista', revista.id) }, nombreRevista(revista))),
        datosRevista);
    }

    function textoRecuento(visibles) {
      if (!estado.busqueda) return 'Se muestran las ' + plural(revistas.length, 'revista', 'revistas') + '.';
      return 'Se muestran ' + visibles + ' de ' + plural(revistas.length, 'revista', 'revistas') +
        ' para la búsqueda «' + estado.busqueda + '».';
    }

    // modo: 'inmediato' anuncia ya el recuento, 'diferido' espera a que se deje
    // de escribir, y sin modo no se anuncia nada.
    function actualizar(modo) {
      estado.busqueda = campo.value.trim();
      borrar.setAttribute('aria-disabled', estado.busqueda ? 'false' : 'true');
      var consulta = normalizar(estado.busqueda);
      var filtradas = revistas.filter(function (r) {
        return !consulta || normalizar(r.titulo + ' ' + (r.titulo_alternativo || '')).indexOf(consulta) !== -1;
      }).sort(function (a, b) {
        return estado.orden === 'desc' ? colador.compare(b.titulo, a.titulo) : colador.compare(a.titulo, b.titulo);
      });
      lista.replaceChildren.apply(lista, filtradas.map(tarjeta));
      lista.hidden = filtradas.length === 0;
      recuento.textContent = textoRecuento(filtradas.length);

      vacio.hidden = filtradas.length > 0;
      if (!filtradas.length) {
        vacio.replaceChildren(
          el('p', { clase: 'estado__titulo' }, el('strong', null, 'Ninguna revista coincide con «' + estado.busqueda + '».')),
          el('p', null, 'Prueba con una palabra más corta o comprueba cómo está escrita. Recuerda que solo se busca en el nombre de la revista.'),
          el('button', { type: 'button', clase: 'boton', onClick: function () {
            campo.value = '';
            actualizar('inmediato');
            campo.focus();
          } }, 'Borrar la búsqueda y ver todas las revistas'));
      }

      window.clearTimeout(estado.temporizadorAnuncio);
      var mensaje = filtradas.length ? recuento.textContent : 'Ninguna revista coincide con la búsqueda.';
      if (modo === 'inmediato') anunciar(mensaje);
      else if (modo === 'diferido') {
        estado.temporizadorAnuncio = window.setTimeout(function () { anunciar(mensaje); }, RETRASO_ANUNCIO);
      }
    }

    campo.addEventListener('input', function () { actualizar('diferido'); });

    if (!revistas.length) {
      anadir(contenedor, [
        encabezado('Revistas de sociología en español'),
        el('div', { clase: 'estado' },
          el('p', { clase: 'estado__titulo' }, el('strong', null, 'Todavía no hay revistas disponibles.')),
          el('p', null, 'Los datos se actualizan automáticamente cada semana. Vuelve a intentarlo más tarde.'))
      ]);
      return { titulo: 'Listado de revistas', anuncio: 'Listado de revistas cargado. No hay revistas disponibles.', contenido: contenedor };
    }

    anadir(contenedor, [
      encabezado('Revistas de sociología en español'),
      el('p', { clase: 'texto-ancho' },
        plural(revistas.length, 'revista de acceso abierto publicada', 'revistas de acceso abierto publicadas') +
        ' en español. Elige una para ver sus tres números más recientes y el índice de artículos de cada número.'),
      el('form', { clase: 'buscador', role: 'search', 'aria-label': 'Buscar revistas', onSubmit: function (evento) {
        // Intro no recarga la página: confirma el número de resultados.
        evento.preventDefault();
        actualizar('inmediato');
      } },
        el('div', { clase: 'buscador__fila' },
          el('div', { clase: 'campo' },
            el('label', { for: 'busqueda' }, 'Buscar por nombre de revista'),
            el('p', { clase: 'campo__ayuda', id: 'busqueda-ayuda' },
              'Los resultados se actualizan mientras escribes. No importan las tildes ni las mayúsculas.'),
            el('div', { clase: 'campo__control' }, campo, borrar)),
          el('div', { clase: 'campo campo--estrecho' },
            el('label', { for: 'orden' }, 'Orden'),
            el('div', { clase: 'campo__control' }, selector)))),
      el('h2', null, 'Lista de revistas'),
      recuento,
      vacio,
      lista
    ]);
    actualizar();

    return {
      titulo: 'Listado de revistas',
      anuncio: 'Listado de revistas cargado. ' + recuento.textContent,
      contenido: contenedor
    };
  }

  function listaLicencias(licencias) {
    var enlaces = (licencias || []).map(function (l) {
      return enlaceExterno(l.url, l.nombre) || el('span', null, l.nombre);
    });
    if (!enlaces.length) return null;
    var resultado = [];
    enlaces.forEach(function (e, i) { if (i) resultado.push(', '); resultado.push(e); });
    return resultado;
  }

  function vistaRevista(datos) {
    var revista = datos.revista;
    var numeros = datos.numeros;
    var ficha = el('dl', { clase: 'metadatos' });
    [
      ['Editorial', revista.editorial],
      ['País', nombreDe('region', revista.pais)],
      ['ISSN impreso', revista.issn_impreso],
      ['ISSN electrónico', revista.issn_electronico],
      ['Idiomas', (revista.idiomas || []).map(function (c) { return nombreDe('language', c); }).join(', ')],
      ['Materias', (revista.materias || []).join('; ')],
      ['Palabras clave', (revista.palabras_clave || []).join('; ')],
      ['Licencia', listaLicencias(revista.licencias)]
    ].forEach(function (par) {
      if (par[1] && par[1].length) anadir(ficha, [el('dt', null, par[0]), el('dd', null, par[1])]);
    });

    var enlaces = el('p', { clase: 'acciones' },
      enlaceExterno(revista.url, 'Visitar la web de la revista'),
      enlaceExterno(revista.url_doaj, 'Ver la ficha en DOAJ'));

    var bloqueNumeros;
    if (numeros.length) {
      bloqueNumeros = [
        el('p', { clase: 'texto-ancho' }, numeros.length === 1
          ? 'Solo hay un número disponible en las fuentes consultadas.'
          : 'Los ' + numeros.length + ' últimos números disponibles, del más reciente al más antiguo.'),
        el('ol', { clase: 'lista' }, numeros.map(function (numero) {
          var cantidad = (numero.articulos || []).length;
          var fecha = fechaLegible(numero.fecha);
          return el('li', { clase: 'tarjeta' },
            el('h3', { clase: 'tarjeta__titulo' }, el('a', { href: ruta('revista', revista.id, 'numero', numero.id) }, numero.etiqueta)),
            el('p', null, plural(cantidad, 'artículo', 'artículos') + (fecha ? '. Publicado en ' + fecha + '.' : '.')));
        }))
      ];
    } else {
      bloqueNumeros = el('div', { clase: 'estado' },
        el('p', { clase: 'estado__titulo' }, el('strong', null, 'No hay números disponibles.')),
        el('p', null, 'Las fuentes consultadas no tienen todavía números de esta revista. Puedes consultar sus publicaciones directamente en su web.'),
        el('p', null, enlaceExterno(revista.url, 'Visitar la web de la revista')));
    }

    var fuentes = 'Fuente de la ficha: ' + (revista.fuente_ficha || 'DOAJ') + '.';
    if (numeros.length) fuentes += ' Fuente de los números: ' + (numeros[0].fuente || revista.fuente_numeros) + '.';

    return {
      titulo: revista.titulo,
      migas: [{ texto: revista.titulo, idioma: revista.idioma_titulo, href: ruta('revista', revista.id) }],
      anuncio: 'Ficha de la revista cargada. ' + (numeros.length ? plural(numeros.length, 'número disponible', 'números disponibles') + '.' : 'No hay números disponibles.'),
      contenido: el('div', null,
        encabezado(revista.titulo, revista.idioma_titulo),
        revista.titulo_alternativo ? el('p', { clase: 'texto-suave' }, 'También conocida como: ',
          conIdioma(el('span', null, revista.titulo_alternativo), revista.idioma_titulo_alternativo)) : null,
        el('h2', null, 'Sobre la revista'),
        revista.descripcion ? el('p', { clase: 'texto-ancho' }, revista.descripcion) : null,
        ficha,
        enlaces,
        el('h2', null, 'Números más recientes'),
        bloqueNumeros,
        el('p', { clase: 'texto-suave' }, fuentes))
    };
  }

  function tarjetaArticulo(articulo, revista, numero) {
    var autores = (articulo.autores || []).map(function (a) { return a.nombre; }).filter(Boolean);
    var titulo = conIdioma(el('h3', { clase: 'tarjeta__titulo' }), articulo.idioma_titulo);
    titulo.textContent = articulo.titulo;

    var publicado = ['Publicado en ', nombreRevista(revista), ', ' + numero.etiqueta +
      (articulo.paginas ? ', páginas ' + articulo.paginas : '') + '.'];

    var resumen;
    if (articulo.resumen) {
      resumen = el('details', null,
        el('summary', null, 'Resumen', el('span', { clase: 'solo-lector' }, ' del artículo: ',
          conIdioma(el('span', null, articulo.titulo), articulo.idioma_titulo))),
        conIdioma(el('p', { clase: 'articulo__resumen' }, articulo.resumen), articulo.idioma_resumen));
    } else {
      resumen = el('p', { clase: 'texto-suave' }, 'Resumen no disponible en la fuente.');
    }

    var detalles = el('dl', { clase: 'metadatos' },
      el('dt', null, 'Licencia'),
      el('dd', null, articulo.licencia
        ? (enlaceExterno(articulo.licencia.url, articulo.licencia.nombre) || articulo.licencia.nombre)
        : 'No indicada en la fuente. Consulta las condiciones en la web de la revista.'),
      articulo.doi ? [el('dt', null, 'DOI'), el('dd', { clase: 'doi' }, articulo.doi)] : null);

    return el('li', { clase: 'tarjeta articulo' },
      el('article', null,
        titulo,
        el('p', { clase: 'articulo__autores' }, autores.length ? 'Autoría: ' + autores.join(', ') + '.' : 'Autoría no indicada en la fuente.'),
        el('p', { clase: 'texto-suave' }, publicado),
        resumen,
        detalles,
        el('p', null, enlaceExterno(articulo.url, 'Leer en la web de la revista', articulo.titulo, articulo.idioma_titulo))));
  }

  function vistaNumero(datos, numero) {
    var revista = datos.revista;
    var articulos = numero.articulos || [];
    var fecha = fechaLegible(numero.fecha);
    var contenido = el('div', null,
      encabezado([nombreRevista(revista), ': ' + numero.etiqueta]),
      el('p', { clase: 'texto-ancho' },
        plural(articulos.length, 'artículo', 'artículos') + '.' +
        (fecha ? ' Publicado en ' + fecha + '.' : '') +
        (revista.editorial ? ' Edita: ' + revista.editorial + '.' : '')),
      el('p', { clase: 'texto-ancho' },
        'Esta aplicación muestra solo el índice. Cada enlace «Leer en la web de la revista» abre el artículo original en una pestaña nueva, fuera de esta aplicación.'));

    if (articulos.length) {
      anadir(contenido, [
        el('h2', null, 'Artículos'),
        el('ol', { clase: 'lista' }, articulos.map(function (a) { return tarjetaArticulo(a, revista, numero); }))
      ]);
    } else {
      anadir(contenido, el('div', { clase: 'estado' },
        el('p', { clase: 'estado__titulo' }, el('strong', null, 'Este número no tiene artículos registrados.')),
        el('p', null, 'La fuente consultada no incluye artículos para este número. Puedes buscarlo en la web de la revista.'),
        el('p', null, enlaceExterno(revista.url, 'Visitar la web de la revista'))));
    }
    anadir(contenido, el('p', { clase: 'texto-suave' }, 'Fuente de los datos: ' + (numero.fuente || 'Crossref') + '.'));

    return {
      titulo: numero.etiqueta + ' · ' + revista.titulo,
      migas: [
        { texto: revista.titulo, idioma: revista.idioma_titulo, href: ruta('revista', revista.id) },
        { texto: numero.etiqueta, href: ruta('revista', revista.id, 'numero', numero.id) }
      ],
      anuncio: 'Índice del número cargado. ' + (articulos.length ? plural(articulos.length, 'artículo', 'artículos') + '.' : 'No tiene artículos registrados.'),
      contenido: contenido
    };
  }

  function volverAlListado() {
    return el('a', { href: '#/', clase: 'boton boton--secundario' }, 'Volver al listado de revistas');
  }

  function vistaNoEncontrada() {
    return {
      titulo: 'Página no encontrada',
      anuncio: 'Página no encontrada.',
      contenido: el('div', null,
        encabezado('Página no encontrada'),
        el('div', { clase: 'estado' },
          el('p', null, 'La dirección que has abierto no corresponde a ninguna página de esta aplicación. Puede que esté incompleta o mal escrita.'),
          el('p', { clase: 'acciones' }, volverAlListado())))
    };
  }

  function vistaError(destino, error) {
    if (!(error instanceof ErrorDatos)) {
      error = new ErrorDatos('datos', 'Se ha producido un error inesperado al preparar la página.');
      if (window.console) window.console.error(error);
    }
    if (error.tipo === 'no-encontrado' && (error.detalle === 'revista' || error.detalle === 'numero')) {
      var esNumero = error.detalle === 'numero';
      var titulo = esNumero ? 'No hemos encontrado este número' : 'No hemos encontrado esta revista';
      var acciones = el('p', { clase: 'acciones' });
      if (esNumero) anadir(acciones, el('a', { href: ruta('revista', destino.id), clase: 'boton' }, 'Ver los números disponibles de la revista'));
      anadir(acciones, volverAlListado());
      return {
        titulo: titulo,
        anuncio: titulo + '.',
        contenido: el('div', null,
          encabezado(titulo),
          el('div', { clase: 'estado' },
            el('p', null, esNumero
              ? 'Este número no figura entre los tres más recientes de la revista. Puede que la dirección esté mal escrita o que el número sea antiguo y ya no se muestre.'
              : 'No hay ninguna revista con esta dirección. Puede que la dirección esté mal escrita o que la revista ya no figure en el listado.'),
            acciones))
      };
    }

    var reintentar = el('button', { type: 'button', clase: 'boton', onClick: mostrar }, 'Reintentar');
    return {
      titulo: 'Error al cargar los datos',
      anuncio: 'Error: no se han podido cargar los datos.',
      contenido: el('div', null,
        encabezado('No se han podido cargar los datos'),
        el('div', { clase: 'estado estado--error' },
          el('p', null, el('strong', null, 'Qué ha pasado: '), error.detalle || 'Error desconocido.'),
          el('p', null, el('strong', null, 'Qué puedes hacer: '),
            error.tipo === 'red'
              ? 'comprueba tu conexión a internet y pulsa «Reintentar». Si el problema continúa, vuelve a intentarlo más tarde.'
              : 'pulsa «Reintentar». Si el problema continúa, los datos pueden estar actualizándose; vuelve a intentarlo dentro de unos minutos.'),
          el('p', { clase: 'acciones' }, reintentar, destino.vista !== 'listado' ? volverAlListado() : null)))
    };
  }

  /* Tamaño del texto */

  function leerTamano() {
    try {
      var guardado = parseInt(window.localStorage.getItem(CLAVE_TAMANO), 10);
      return TAMANOS.indexOf(guardado) !== -1 ? guardado : 100;
    } catch (e) {
      return 100;
    }
  }

  function aplicarTamano(tamano) {
    document.documentElement.style.fontSize = tamano === 100 ? '' : tamano + '%';
    document.getElementById('texto-tamano-valor').textContent = tamano + ' %';
    document.querySelector('[data-tamano="reducir"]').setAttribute('aria-disabled', String(tamano === TAMANOS[0]));
    document.querySelector('[data-tamano="aumentar"]').setAttribute('aria-disabled', String(tamano === TAMANOS[TAMANOS.length - 1]));
    document.querySelector('[data-tamano="normal"]').setAttribute('aria-disabled', String(tamano === 100));
    try { window.localStorage.setItem(CLAVE_TAMANO, String(tamano)); } catch (e) { /* sin almacenamiento */ }
  }

  function iniciarTamano() {
    var actual = leerTamano();
    aplicarTamano(actual);
    document.querySelectorAll('[data-tamano]').forEach(function (boton) {
      boton.addEventListener('click', function () {
        var accion = boton.getAttribute('data-tamano');
        var posicion = TAMANOS.indexOf(actual);
        var nuevo = accion === 'normal' ? 100 : TAMANOS[posicion + (accion === 'aumentar' ? 1 : -1)];
        if (nuevo === undefined || nuevo === actual) {
          anunciar(accion === 'aumentar' ? 'El texto ya está en el tamaño máximo, ' + actual + ' %.'
            : accion === 'reducir' ? 'El texto ya está en su tamaño original, 100 %.' : 'El texto ya está en su tamaño original.');
          return;
        }
        actual = nuevo;
        aplicarTamano(actual);
        anunciar('Tamaño del texto: ' + actual + ' %.');
      });
    });
  }

  /* Inicio */

  function iniciar() {
    iniciarTamano();

    // El enlace de salto mueve el foco sin cambiar la dirección, para no
    // romper la ruta actual ni el historial.
    document.getElementById('enlace-salto').addEventListener('click', function (evento) {
      evento.preventDefault();
      var destino = principal.querySelector('h1') || principal;
      if (destino.getAttribute('tabindex') === null) destino.setAttribute('tabindex', '-1');
      destino.focus();
    });

    document.querySelectorAll('a.externo').forEach(function (enlace) {
      enlace.setAttribute('target', '_blank');
      enlace.setAttribute('rel', 'noopener');
      anadir(enlace, el('span', { clase: 'enlace-externo__aviso' }, ' ' + AVISO_EXTERNO));
    });

    window.addEventListener('hashchange', mostrar);
    mostrar();
  }

  iniciar();
}());
