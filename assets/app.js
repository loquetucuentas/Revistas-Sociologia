/*
  Explorador de revistas de sociología en acceso abierto.
  Aplicación de una sola página sin dependencias externas.

  Rutas (con almohadilla, para que el botón atrás funcione):
    #/                                  listado de revistas
    #/revista/<id>                      ficha de una revista
    #/revista/<id>/numero/<numero>      índice de un número
    #/revista/<id>/numero/<numero>/articulo/<clave>
                                        lectura del texto completo de un artículo

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
  var CLAVE_TEMA = 'revistas-sociologia:tema';
  var TEMAS = { '': 'automático, según el sistema', claro: 'claro', oscuro: 'oscuro', contraste: 'alto contraste' };
  var AVISO_EXTERNO = '(sitio externo, se abre en una pestaña nueva)';

  var colador = new Intl.Collator('es', { sensitivity: 'base', numeric: true });
  var estado = {
    busqueda: '',
    orden: 'asc',
    cache: {},
    peticion: 0,
    primeraVista: true,
    temporizadorAnuncio: null,
    // Al ir del índice de un número a la lectura de un artículo se guarda
    // la posición, para recuperarla al volver con el botón atrás.
    retorno: null
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
    if (window.DATOS_INCRUSTADOS) {
      // Versión de un solo archivo (dist/revistas-prueba.html): los datos
      // vienen dentro de la página y no se pide nada fuera de ella.
      promesa = new Promise(function (resolver, rechazar) {
        var datos = window.DATOS_INCRUSTADOS[archivo];
        if (datos) resolver(datos);
        else rechazar(new ErrorDatos('no-encontrado', 'El archivo de datos no está incluido en esta versión.'));
      });
    } else if (location.protocol === 'file:') {
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
    if (partes[0] === 'revista' && partes.length === 6 && partes[2] === 'numero' && partes[4] === 'articulo') {
      return { vista: 'lectura', id: partes[1], numero: partes[3], articulo: partes[5] };
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
    if (destino.vista === 'lectura') {
      return cargarRevista(destino.id).then(function (datos) {
        var numero = datos.numeros.find(function (n) { return n.id === destino.numero; });
        if (!numero) throw new ErrorDatos('no-encontrado', 'numero', datos);
        var articulo = (numero.articulos || []).find(function (a) { return claveArticulo(a) === destino.articulo; });
        if (!articulo || !articulo.texto_completo) throw new ErrorDatos('no-encontrado', 'articulo', datos);
        return cargarDatos(articulo.texto_completo).then(function (texto) {
          if (!texto || !Array.isArray(texto.contenido) || !texto.licencia ||
              String(texto.doi).toLowerCase() !== String(articulo.doi).toLowerCase()) {
            throw new ErrorDatos('datos', 'El texto del artículo no tiene el formato esperado.');
          }
          return vistaLectura(datos, numero, articulo, texto);
        });
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
    // Al volver de la lectura, el índice recupera su posición y el foco va al
    // enlace del artículo que se estaba leyendo (vista.foco).
    var destinoFoco = vista.foco || principal.querySelector('h1');
    window.scrollTo(0, vista.posicion || 0);
    if (destinoFoco) destinoFoco.focus({ preventScroll: true });
    if (vista.foco && !vista.posicion) vista.foco.scrollIntoView({ block: 'center' });
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

    // Se dice con texto, no solo con un icono, si el artículo se puede leer aquí.
    var lectura;
    if (articulo.texto_completo) {
      var destino = ruta('revista', revista.id, 'numero', numero.id, 'articulo', claveArticulo(articulo));
      lectura = [
        el('p', { clase: 'lectura-disponible' }, 'Lectura completa disponible en esta aplicación.'),
        el('p', null, el('a', { href: destino, id: 'leer-' + claveArticulo(articulo), clase: 'boton', onClick: function () {
          estado.retorno = { ruta: location.hash, posicion: window.scrollY, articulo: claveArticulo(articulo) };
        } }, 'Leer el artículo completo', el('span', { clase: 'solo-lector' }, ': ',
          conIdioma(el('span', null, articulo.titulo), articulo.idioma_titulo))))
      ];
    } else {
      lectura = el('p', { clase: 'lectura-externa' }, 'Texto completo solo en la web de la revista.');
    }

    return el('li', { clase: 'tarjeta articulo' },
      el('article', null,
        titulo,
        el('p', { clase: 'articulo__autores' }, autores.length ? 'Autoría: ' + autores.join(', ') + '.' : 'Autoría no indicada en la fuente.'),
        el('p', { clase: 'texto-suave' }, publicado),
        lectura,
        resumen,
        detalles,
        el('p', null, enlaceExterno(articulo.url, 'Leer en la web de la revista', articulo.titulo, articulo.idioma_titulo))));
  }

  // Clave del artículo en la dirección: el nombre de su archivo de texto, o el DOI.
  function claveArticulo(articulo) {
    var archivo = articulo.texto_completo || '';
    var nombre = archivo.replace(/^textos\//, '').replace(/\.json$/, '');
    return nombre || String(articulo.doi || articulo.id || '');
  }

  /* Vista de lectura */

  var ETIQUETAS_TEXTO = {
    section: 1, h2: 1, h3: 1, h4: 1, h5: 1, h6: 1, p: 1, ul: 1, ol: 1, li: 1, blockquote: 1, table: 1,
    caption: 1, thead: 1, tbody: 1, tfoot: 1, tr: 1, th: 1, td: 1, figure: 1, figcaption: 1, dl: 1, dt: 1,
    dd: 1, aside: 1, pre: 1, em: 1, strong: 1, i: 1, b: 1, u: 1, sub: 1, sup: 1, br: 1, a: 1, q: 1,
    cite: 1, small: 1, span: 1, code: 1, abbr: 1, s: 1, mark: 1
  };
  var ATRIBUTOS_TEXTO = { lang: 1, id: 1, colspan: 1, rowspan: 1, scope: 1, start: 1, title: 1 };

  // Construye el texto del artículo a partir del árbol saneado por el recolector.
  // Solo se admiten las etiquetas y atributos de la lista blanca, y el texto
  // se inserta siempre como texto: nunca se interpreta como HTML.
  function construirTexto(nodos, contexto) {
    var fragmento = document.createDocumentFragment();
    (nodos || []).forEach(function (nodo) {
      var hijo = construirNodo(nodo, contexto);
      if (hijo) fragmento.appendChild(hijo);
    });
    return fragmento;
  }

  function construirNodo(nodo, contexto) {
    if (typeof nodo === 'string') return document.createTextNode(nodo);
    if (!Array.isArray(nodo) || typeof nodo[0] !== 'string') return null;
    var etiqueta = nodo[0];
    var atributos = nodo[1] && typeof nodo[1] === 'object' ? nodo[1] : {};
    var hijos = nodo.slice(2);
    if (etiqueta === 'figura') return figuraSustituida(atributos, contexto);
    if (!ETIQUETAS_TEXTO[etiqueta]) return construirTexto(hijos, contexto);
    var elemento;
    if (etiqueta === 'a') {
      var href = String(atributos.href || '');
      if (contexto.enEnlace) {
        // Un enlace dentro de otro (algunas galeradas lo traen así) no se
        // puede activar por separado: el interior se muestra como texto.
        elemento = el('span');
      } else if (/^#t-[A-Za-z0-9_-]+$/.test(href)) {
        elemento = el('a', { href: href, clase: 'enlace-interno' });
      } else if (urlSegura(href)) {
        elemento = el('a', { href: href, target: '_blank', rel: 'noopener' });
        elemento.appendChild(construirDentroDeEnlace(hijos, contexto));
        anadir(elemento, el('span', { clase: 'enlace-externo__aviso' }, ' ' + AVISO_EXTERNO));
        copiarAtributos(elemento, atributos);
        return elemento;
      } else {
        elemento = el('span');
      }
    } else if (etiqueta === 'th' && !textoDe(hijos).trim()) {
      // Una cabecera de tabla vacía (la esquina de muchas tablas) no encabeza
      // nada: se muestra como celda normal para no anunciar una cabecera vacía.
      elemento = document.createElement('td');
    } else if (etiqueta === 'aside') {
      // Notas y recuadros del original: no son regiones de la página, así que
      // no se usa aside, que crearía un punto de referencia dentro de otro.
      elemento = el('div', { clase: 'recuadro' });
    } else {
      elemento = document.createElement(etiqueta);
    }
    copiarAtributos(elemento, atributos);
    elemento.appendChild(elemento.tagName === 'A' ? construirDentroDeEnlace(hijos, contexto) : construirTexto(hijos, contexto));
    if (etiqueta === 'table') {
      // Las tablas anchas se desplazan dentro de su propio marco, que se puede
      // recorrer con el teclado, y nunca ensanchan la página.
      var leyenda = elemento.querySelector('caption');
      var marco = el('div', { clase: 'tabla-desplazable', role: 'region', tabindex: '0' });
      if (leyenda) {
        if (!leyenda.id) leyenda.id = 'leyenda-' + (++contexto.tablas);
        marco.setAttribute('aria-labelledby', leyenda.id);
      } else {
        marco.setAttribute('aria-label', 'Tabla ' + (++contexto.tablas) + ' del artículo');
      }
      marco.appendChild(elemento);
      return marco;
    }
    return elemento;
  }

  function textoDe(nodos) {
    return (nodos || []).map(function (n) {
      return typeof n === 'string' ? n : Array.isArray(n) ? textoDe(n.slice(2)) : '';
    }).join('');
  }

  function construirDentroDeEnlace(hijos, contexto) {
    var anterior = contexto.enEnlace;
    contexto.enEnlace = true;
    var fragmento = construirTexto(hijos, contexto);
    contexto.enEnlace = anterior;
    return fragmento;
  }

  function copiarAtributos(elemento, atributos) {
    Object.keys(atributos).forEach(function (clave) {
      if (!ATRIBUTOS_TEXTO[clave] || typeof atributos[clave] !== 'string') return;
      if (clave === 'id' && !/^t-[A-Za-z0-9_-]+$/.test(atributos.id)) return;
      if (clave === 'lang' && !/^[a-z]{2,3}(-[a-z0-9]+)*$/i.test(atributos.lang)) return;
      if (clave === 'scope' && elemento.tagName !== 'TH') return;
      elemento.setAttribute(clave, atributos[clave]);
    });
  }

  // Las imágenes de la revista no se muestran: en su lugar va su descripción,
  // o un aviso si la revista no la ofrece, y un enlace para verla en el original.
  function figuraSustituida(atributos, contexto) {
    var alt = typeof atributos.alt === 'string' ? atributos.alt.trim() : '';
    // Dentro de un enlace del original no se añade otro enlace: se dice con texto.
    var enlace = contexto.enEnlace ? 'Puedes verla en la web de la revista.'
      : enlaceExterno(contexto.articulo.url, 'Ver la figura en la web de la revista');
    if (alt) {
      return el('span', { clase: 'figura-sustituida' },
        el('strong', null, 'Imagen de la revista. '), 'Descripción de la revista: ', alt, ' ', enlace);
    }
    contexto.sinDescripcion++;
    return el('span', { clase: 'figura-sustituida figura-sustituida--sin-descripcion' },
      el('strong', null, 'Aviso: esta figura no dispone de descripción en la revista.'),
      ' Para verla, consulta el original. ', enlace);
  }

  // Cita en el estilo APA 7, adaptado al español («y» antes del último autor).
  function iniciales(nombre) {
    return String(nombre || '').split(/\s+/).filter(Boolean).map(function (parte) {
      return parte.split('-').map(function (p) { return p.charAt(0).toUpperCase() + '.'; }).join('-');
    }).join(' ');
  }

  function autoresCita(texto, articulo) {
    var lista = (texto.autores_cita && texto.autores_cita.length ? texto.autores_cita : (articulo.autores || []))
      .map(function (a) {
        if (a.apellidos) return a.apellidos + (a.nombre_pila ? ', ' + iniciales(a.nombre_pila) : '');
        return a.nombre || '';
      }).filter(Boolean);
    if (lista.length === 0) return '';
    if (lista.length === 1) return lista[0];
    return lista.slice(0, -1).join(', ') + ' y ' + lista[lista.length - 1];
  }

  // Devuelve el texto de la cita y una función que crea sus nodos: cada
  // bloque de cita necesita los suyos, porque un nodo solo puede estar en un sitio.
  function cita(texto, articulo, revista, numero) {
    var autores = autoresCita(texto, articulo);
    var paginas = articulo.paginas ? String(articulo.paginas).replace(/-/g, '–') : '';
    var partes = [];
    if (autores) partes.push([autores + (/\.$/.test(autores) ? ' ' : '. ')]);
    partes.push(['(' + (numero.anio || 's. f.') + '). ']);
    partes.push([articulo.titulo, 'titulo']);
    partes.push([/[.?!]$/.test(articulo.titulo) ? ' ' : '. ']);
    partes.push([revista.titulo, 'cursiva']);
    if (numero.volumen) { partes.push([', ']); partes.push([numero.volumen, 'cursiva']); }
    if (numero.numero) partes.push(['(' + numero.numero + ')']);
    if (paginas) partes.push([', ' + paginas]);
    partes.push(['. https://doi.org/' + articulo.doi]);
    return {
      texto: partes.map(function (p) { return p[0]; }).join(''),
      construir: function () {
        return partes.map(function (p) {
          if (p[1] === 'cursiva') return el('i', null, p[0]);
          if (p[1] === 'titulo') return conIdioma(el('span', null, p[0]), articulo.idioma_titulo);
          return p[0];
        });
      }
    };
  }

  function bloqueCita(datosCita, idCita) {
    var parrafo = el('p', { clase: 'cita', id: idCita });
    anadir(parrafo, datosCita.construir());
    return parrafo;
  }

  function copiarCita(textoCita, idCita) {
    function seleccionar() {
      var nodo = document.getElementById(idCita);
      var rango = document.createRange();
      rango.selectNodeContents(nodo);
      var seleccion = window.getSelection();
      seleccion.removeAllRanges();
      seleccion.addRange(rango);
      anunciar('No se ha podido copiar automáticamente. La cita ha quedado seleccionada: cópiala con el menú del sistema o con Comando más C.');
    }
    if (!navigator.clipboard || !navigator.clipboard.writeText) { seleccionar(); return; }
    navigator.clipboard.writeText(textoCita).then(function () {
      anunciar('Cita copiada.');
      var aviso = document.getElementById(idCita + '-copiada');
      if (aviso) aviso.textContent = 'Cita copiada.';
    }, seleccionar);
  }

  function indiceDelArticulo(entradas) {
    if (!entradas || !entradas.length) return null;
    var raiz = el('ol');
    var pila = [{ nivel: 1, lista: raiz }];
    entradas.forEach(function (entrada) {
      if (!/^t-[A-Za-z0-9_-]+$/.test(entrada.id)) return;
      while (pila.length > 1 && pila[pila.length - 1].nivel >= entrada.nivel) pila.pop();
      var elemento = el('li', null, conIdioma(el('a', { href: '#' + entrada.id, clase: 'enlace-interno' }, entrada.texto), entrada.lang));
      pila[pila.length - 1].lista.appendChild(elemento);
      var sublista = el('ol');
      elemento.appendChild(sublista);
      pila.push({ nivel: entrada.nivel, lista: sublista });
    });
    // Se quitan las sublistas vacías.
    raiz.querySelectorAll('ol').forEach(function (lista) { if (!lista.children.length) lista.remove(); });
    return el('nav', { clase: 'indice-articulo', 'aria-labelledby': 'indice-articulo-titulo' },
      el('h2', { id: 'indice-articulo-titulo' }, 'Contenido del artículo'), raiz);
  }

  function vistaLectura(datos, numero, articulo, texto) {
    var revista = datos.revista;
    var licencia = texto.licencia;
    var autores = (articulo.autores || []).map(function (a) { return a.nombre; }).filter(Boolean);
    var datosCita = cita(texto, articulo, revista, numero);
    var contexto = { articulo: articulo, tablas: 0, sinDescripcion: 0 };
    var fecha = fechaLegible(texto.recogido);
    var original = function () {
      return el('p', null, enlaceExterno(articulo.url, 'Ver y citar en la web de la revista'));
    };

    var cuerpo = el('div', { clase: 'texto-articulo' });
    conIdioma(cuerpo, texto.idioma_principal);
    cuerpo.appendChild(construirTexto(texto.contenido, contexto));
    // Enlaces de vuelta desde notas y referencias que no lo traen en el original.
    Object.keys(texto.vueltas || {}).forEach(function (destino) {
      var llamada = texto.vueltas[destino];
      var nota = /^t-[A-Za-z0-9_-]+$/.test(destino) ? cuerpo.querySelector('#' + CSS.escape(destino)) : null;
      if (!nota || !/^t-[A-Za-z0-9_-]+$/.test(llamada) || !cuerpo.querySelector('#' + CSS.escape(llamada))) return;
      // Nunca un enlace dentro de otro enlace.
      if (nota.closest('a')) return;
      anadir(nota, [' ', el('a', { href: '#' + llamada, clase: 'enlace-interno volver-nota', lang: 'es' }, 'Volver al texto')]);
    });

    var avisos = (texto.avisos_derechos || []).filter(Boolean);
    var atribucion = el('section', { clase: 'atribucion', 'aria-labelledby': 'atribucion-titulo' },
      el('h2', { id: 'atribucion-titulo' }, 'Cita, autoría y licencia'),
      el('dl', { clase: 'metadatos' },
        el('dt', null, 'Autoría'), el('dd', null, autores.length ? autores.join(', ') : 'No indicada en la fuente.'),
        el('dt', null, 'Revista'), el('dd', null, nombreRevista(revista), ', ' + numero.etiqueta +
          (articulo.paginas ? ', páginas ' + articulo.paginas : '') + '.'),
        el('dt', null, 'DOI'), el('dd', { clase: 'doi' }, articulo.doi),
        el('dt', null, 'Licencia'), el('dd', null, licencia.nombre_completo, ' (' + licencia.nombre + '). ',
          enlaceExterno(licencia.url_legal, 'Texto legal de la licencia'))),
      el('h3', null, 'Cita completa'),
      bloqueCita(datosCita, 'cita-inicial'),
      el('p', null, 'Este artículo se muestra con la licencia ' + licencia.nombre_completo +
        '. Solo se han modificado el formato y la presentación; el texto es el publicado por la revista.'),
      avisos.length ? [el('h3', null, 'Avisos de derechos del original'),
        el('ul', { clase: 'avisos-derechos' }, avisos.map(function (a) { return el('li', null, a); }))] : null,
      el('p', { clase: 'texto-suave' }, 'Texto obtenido de la versión ' + (texto.fuente && texto.fuente.formato || 'HTML') +
        ' que publica la revista' + (fecha ? ', consultada el ' + fecha : '') + '.'),
      original());

    var indice = indiceDelArticulo(texto.indice);
    var idCita = 'cita-final-texto';
    var final = el('section', { clase: 'cita-final', 'aria-labelledby': 'cita-final-titulo' },
      el('h2', { id: 'cita-final-titulo' }, 'Cómo citar este artículo'),
      bloqueCita(datosCita, idCita),
      el('p', { clase: 'acciones' },
        el('button', { type: 'button', clase: 'boton', onClick: function () { copiarCita(datosCita.texto, idCita); } }, 'Copiar la cita'),
        el('span', { clase: 'copiado', id: idCita + '-copiada' })),
      el('p', null, 'Licencia: ' + licencia.nombre_completo + '. ', enlaceExterno(licencia.url_legal, 'Texto legal de la licencia')),
      original(),
      el('p', null, el('a', { href: ruta('revista', revista.id, 'numero', numero.id), clase: 'boton boton--secundario' }, 'Volver al índice del número')));

    var secciones = (texto.indice || []).filter(function (e) { return e.nivel === 2; }).length;
    return {
      titulo: articulo.titulo,
      migas: [
        { texto: revista.titulo, idioma: revista.idioma_titulo, href: ruta('revista', revista.id) },
        { texto: numero.etiqueta, href: ruta('revista', revista.id, 'numero', numero.id) },
        { texto: articulo.titulo, idioma: articulo.idioma_titulo, href: location.hash }
      ],
      anuncio: 'Artículo cargado para su lectura. ' + (secciones ? plural(secciones, 'sección', 'secciones') + '. ' : '') +
        'Licencia ' + licencia.nombre + '.' + (contexto.sinDescripcion ? ' ' + plural(contexto.sinDescripcion, 'figura no tiene', 'figuras no tienen') + ' descripción en la revista.' : ''),
      contenido: el('article', { clase: 'lectura-vista' },
        encabezado(articulo.titulo, articulo.idioma_titulo),
        atribucion,
        indice,
        cuerpo,
        final)
    };
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

    // Si se vuelve de leer un artículo de este número, se recupera la posición
    // y el foco va al enlace de ese artículo.
    var retorno = estado.retorno && estado.retorno.ruta === location.hash ? estado.retorno : null;
    estado.retorno = null;
    var legibles = articulos.filter(function (a) { return a.texto_completo; }).length;
    var vuelta = retorno ? contenido.querySelector('#' + CSS.escape('leer-' + retorno.articulo)) : null;

    return {
      foco: vuelta,
      posicion: vuelta ? retorno.posicion : 0,
      titulo: numero.etiqueta + ' · ' + revista.titulo,
      migas: [
        { texto: revista.titulo, idioma: revista.idioma_titulo, href: ruta('revista', revista.id) },
        { texto: numero.etiqueta, href: ruta('revista', revista.id, 'numero', numero.id) }
      ],
      anuncio: vuelta ? 'Has vuelto al índice del número, en el artículo que estabas leyendo.'
        : 'Índice del número cargado. ' + (articulos.length ? plural(articulos.length, 'artículo', 'artículos') + '.' : 'No tiene artículos registrados.') +
          (legibles ? ' ' + (legibles === 1 ? 'Uno se puede leer completo en esta aplicación.' : legibles + ' se pueden leer completos en esta aplicación.') : ''),
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
    if (error.tipo === 'no-encontrado' && error.detalle === 'articulo') {
      return {
        titulo: 'Este artículo no se puede leer en la aplicación',
        anuncio: 'Este artículo no se puede leer en la aplicación.',
        contenido: el('div', null,
          encabezado('Este artículo no se puede leer en la aplicación'),
          el('div', { clase: 'estado' },
            el('p', null, 'No hay texto completo de este artículo en la aplicación. Solo se incluyen los artículos cuya licencia lo permite y de los que la revista publica una versión en HTML o XML. Puedes consultarlo en el índice del número, que enlaza al original.'),
            el('p', { clase: 'acciones' },
              el('a', { href: ruta('revista', destino.id, 'numero', destino.numero), clase: 'boton' }, 'Ir al índice del número'),
              volverAlListado())))
      };
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

    // Se vacía la memoria de datos: un archivo que llegó con formato incorrecto
    // también se vuelve a pedir, no solo los que fallaron por la red.
    var reintentar = el('button', { type: 'button', clase: 'boton', onClick: function () {
      estado.cache = {};
      mostrar();
    } }, 'Reintentar');
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

  /* Tema de colores */

  function iniciarTema() {
    var selector = document.getElementById('tema');
    var guardado = '';
    try { guardado = window.localStorage.getItem(CLAVE_TEMA) || ''; } catch (e) { /* sin almacenamiento */ }
    if (!Object.prototype.hasOwnProperty.call(TEMAS, guardado)) guardado = '';
    function aplicar(tema) {
      if (tema) document.documentElement.setAttribute('data-tema', tema);
      else document.documentElement.removeAttribute('data-tema');
    }
    aplicar(guardado);
    selector.value = guardado;
    selector.addEventListener('change', function () {
      aplicar(selector.value);
      try { window.localStorage.setItem(CLAVE_TEMA, selector.value); } catch (e) { /* sin almacenamiento */ }
      anunciar('Tema de colores: ' + TEMAS[selector.value] + '.');
    });
  }

  // Los enlaces a notas, referencias y secciones del artículo mueven el foco
  // sin cambiar la dirección, para no salir de la vista de lectura.
  function seguirEnlaceInterno(evento) {
    var enlace = evento.target.closest && evento.target.closest('a[href^="#t-"]');
    if (!enlace || evento.defaultPrevented || evento.button > 0 || evento.metaKey || evento.ctrlKey || evento.shiftKey) return;
    var destino = document.getElementById(enlace.getAttribute('href').slice(1));
    if (!destino) return;
    evento.preventDefault();
    if (destino.getAttribute('tabindex') === null && !/^(A|BUTTON|INPUT|SELECT|TEXTAREA)$/.test(destino.tagName)) {
      destino.setAttribute('tabindex', '-1');
    }
    destino.focus({ preventScroll: true });
    destino.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }

  /* Inicio */

  function iniciar() {
    iniciarTamano();
    iniciarTema();
    principal.addEventListener('click', seguirEnlaceInterno);

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

    window.addEventListener('hashchange', function () {
      // Un ancla del texto (#t-...) abierta desde fuera no es una vista.
      if (/^#t-/.test(location.hash)) return;
      mostrar();
    });
    mostrar();
  }

  iniciar();
}());
