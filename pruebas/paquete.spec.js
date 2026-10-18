// Comprobaciones del archivo único dist/revistas-prueba.html que genera
// herramientas/empaquetar.py: que no pide nada fuera de sí mismo, que pasa
// axe y que conserva rutas, foco, anuncios, enlaces externos y los estados
// vacío y de error. Se generan dos paquetes nuevos en test-results: uno con
// los datos reales de data y otro con los datos de prueba de pruebas/datos.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { pathToFileURL } = require('url');
const { test, expect } = require('@playwright/test');
const { analizarConAxe, esperarVista } = require('./utilidades');

const RAIZ = path.join(__dirname, '..');
const CARPETA = path.join(RAIZ, 'test-results', 'paquete');
const REAL = path.join(CARPETA, 'revistas-real.html');
const PRUEBA = path.join(CARPETA, 'revistas-prueba-datos.html');
const ARTEFACTO = path.join(CARPETA, 'revistas-artefacto-simulado.html');
const listado = JSON.parse(fs.readFileSync(path.join(RAIZ, 'data', 'revistas.json'), 'utf8'));

function empaquetar(datos, salida, ...extra) {
  execFileSync('python3', [path.join(RAIZ, 'herramientas', 'empaquetar.py'), '--datos', datos, '--salida', salida, ...extra]);
}

// Imita el esqueleto que añade el visor de artefactos de Claude: sin idioma
// en la raíz y con su pequeño reajuste de estilos.
function simularVisor(fragmento, salida, tema) {
  const raiz = tema ? `<html data-theme="${tema}">` : '<html>';
  fs.writeFileSync(salida, `<!doctype html>${raiz}<head><meta charset="utf-8">` +
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">' +
    '<style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style>' +
    `</head><body>${fs.readFileSync(fragmento, 'utf8')}</body></html>`);
}

test.beforeAll(() => {
  fs.mkdirSync(CARPETA, { recursive: true });
  empaquetar(path.join(RAIZ, 'data'), REAL, '--artefacto');
  empaquetar(path.join(RAIZ, 'pruebas', 'datos'), PRUEBA);
  simularVisor(path.join(CARPETA, 'revistas-artefacto.html'), ARTEFACTO);
});

const url = (archivo, ruta = '#/') => pathToFileURL(archivo).href + ruta;

// Registra toda petición que no sea el propio archivo y todo aviso de la CSP.
function vigilarPeticiones(page, archivo) {
  const propio = pathToFileURL(archivo).href;
  const externas = [];
  page.on('request', (peticion) => {
    if (peticion.url().split('#')[0] !== propio) externas.push(peticion.url());
  });
  page.on('console', (mensaje) => {
    if (/Content Security Policy/i.test(mensaje.text())) externas.push('CSP: ' + mensaje.text());
  });
  return externas;
}

test('el paquete real no pide nada fuera del archivo al recorrer las tres vistas', async ({ page }) => {
  const externas = vigilarPeticiones(page, REAL);
  const ficha = listado.revistas[0];
  const datos = JSON.parse(fs.readFileSync(path.join(RAIZ, 'data', ficha.archivo), 'utf8'));
  await page.goto(url(REAL));
  await esperarVista(page, 'Revistas de sociología en español');
  await page.getByRole('link', { name: ficha.titulo, exact: true }).click();
  await expect(page.locator('h1')).toHaveText(ficha.titulo);
  await page.getByRole('link', { name: datos.numeros[0].etiqueta }).first().click();
  await expect(page.locator('h1')).toContainText(datos.numeros[0].etiqueta);
  await page.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; }));
  expect(externas).toEqual([]);
});

test('el paquete real no muestra el aviso de prueba e indica la fecha de los datos', async ({ page }) => {
  await page.goto(url(REAL));
  await esperarVista(page, 'Revistas de sociología en español');
  await expect(page.locator('.aviso-prueba')).toHaveCount(0);
  await expect(page.locator('footer')).toContainText(/datos reales de DOAJ y Crossref generados el \d+ de \w+ de \d{4} a las \d\d:\d\d \(hora UTC\)/);
  await expect(page.locator('.tarjeta')).toHaveCount(listado.revistas.length);
});

test('axe sin errores en el listado del paquete real', async ({ page }) => {
  await page.goto(url(REAL));
  await esperarVista(page, 'Revistas de sociología en español');
  expect(await analizarConAxe(page)).toEqual([]);
});

for (const ficha of listado.revistas) {
  test(`paquete real, axe en ficha y último número: ${ficha.titulo} (${ficha.id})`, async ({ page }) => {
    const datos = JSON.parse(fs.readFileSync(path.join(RAIZ, 'data', ficha.archivo), 'utf8'));
    await page.goto(url(REAL, `#/revista/${encodeURIComponent(ficha.id)}`));
    await expect(page.locator('h1')).toHaveText(ficha.titulo);
    expect(await analizarConAxe(page)).toEqual([]);
    const numero = datos.numeros[0];
    await page.goto(url(REAL, `#/revista/${encodeURIComponent(ficha.id)}/numero/${encodeURIComponent(numero.id)}`));
    await expect(page.locator('h1')).toContainText(numero.etiqueta);
    await page.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; }));
    expect(await analizarConAxe(page)).toEqual([]);
  });
}

test.describe('paquete con datos de prueba', () => {
  test('muestra el aviso visible de datos de prueba', async ({ page }) => {
    await page.goto(url(PRUEBA));
    await esperarVista(page, 'Revistas de sociología en español');
    await expect(page.getByText('Datos de prueba.')).toBeVisible();
    await expect(page.locator('footer')).toContainText('datos de prueba ficticios');
  });

  test('cambio de vista: foco en el h1, título, anuncio y botón atrás', async ({ page }) => {
    await page.goto(url(PRUEBA));
    await esperarVista(page, 'Revistas de sociología');
    await page.getByRole('link', { name: 'Revista de Prueba de Estudios Sociales' }).click();
    const h1 = page.locator('h1');
    await expect(h1).toHaveText('Revista de Prueba de Estudios Sociales');
    await expect(h1).toBeFocused();
    await expect(page).toHaveTitle('Revista de Prueba de Estudios Sociales · Revistas de sociología en acceso abierto');
    await expect(page.locator('#anuncios')).toHaveText('Ficha de la revista cargada. 3 números disponibles.');
    await page.getByRole('link', { name: 'Vol. 12, núm. 2 (2026)' }).click();
    await expect(h1).toBeFocused();
    await expect(page.locator('#anuncios')).toHaveText('Índice del número cargado. 4 artículos. Uno se puede leer completo en esta aplicación.');
    await page.goBack();
    await expect(h1).toHaveText('Revista de Prueba de Estudios Sociales');
    await expect(h1).toBeFocused();
  });

  test('la vista de lectura funciona dentro del archivo único, sin peticiones externas', async ({ page }) => {
    const externas = vigilarPeticiones(page, PRUEBA);
    await page.goto(url(PRUEBA, '#/revista/prueba-0001/numero/v12-n2-2026'));
    await esperarVista(page, 'Vol. 12, núm. 2');
    await page.getByRole('link', { name: /^Leer el artículo completo/ }).click();
    await expect(page.locator('h1')).toContainText('Artículo de prueba 1');
    await expect(page.locator('h1')).toBeFocused();
    await expect(page.getByRole('navigation', { name: 'Contenido del artículo' })).toBeVisible();
    await page.locator('a[href="#t-nota-1"]').click();
    await expect(page.locator('#t-nota-1')).toBeFocused();
    expect(await analizarConAxe(page)).toEqual([]);
    await page.goBack();
    await expect(page.locator('#leer-prueba-0001-v12-n2-1')).toBeFocused();
    expect(externas).toEqual([]);
  });

  test('los enlaces externos avisan de que salen de la aplicación', async ({ page }) => {
    await page.goto(url(PRUEBA, '#/revista/prueba-0001/numero/v12-n2-2026'));
    await esperarVista(page, 'Vol. 12, núm. 2');
    const enlaces = page.locator('a[target="_blank"]');
    expect(await enlaces.count()).toBeGreaterThan(0);
    for (const enlace of await enlaces.all()) {
      await expect(enlace).toContainText('sitio externo, se abre en una pestaña nueva');
      await expect(enlace).toHaveAttribute('href', /^https:\/\//);
    }
  });

  const VACIOS = [
    { nombre: 'revista sin números', ruta: '#/revista/prueba-0005', texto: 'Las fuentes consultadas no tienen todavía números de esta revista' },
    { nombre: 'número sin artículos', ruta: '#/revista/prueba-0003/numero/v12-n1-2026', texto: 'Este número no tiene artículos registrados.' },
    { nombre: 'revista inexistente', ruta: '#/revista/no-existe', texto: 'No hemos encontrado esta revista' },
    { nombre: 'página inexistente', ruta: '#/otra/cosa', texto: 'Página no encontrada' },
  ];
  for (const vacio of VACIOS) {
    test(`estado vacío o no encontrado con axe: ${vacio.nombre}`, async ({ page }) => {
      await page.goto(url(PRUEBA, vacio.ruta));
      await expect(page.getByText(vacio.texto).first()).toBeVisible();
      expect(await analizarConAxe(page)).toEqual([]);
    });
  }

  test('búsqueda sin resultados con axe', async ({ page }) => {
    await page.goto(url(PRUEBA));
    await esperarVista(page, 'Revistas de sociología');
    await page.getByLabel('Buscar por nombre de revista').fill('zzzz');
    await expect(page.getByText('Ninguna revista coincide con «zzzz».')).toBeVisible();
    expect(await analizarConAxe(page)).toEqual([]);
  });

  test('estado de error con datos dañados, axe y Reintentar', async ({ page }) => {
    await page.goto(url(PRUEBA));
    await esperarVista(page, 'Revistas de sociología');
    // Se daña en memoria la revista para provocar el error y se guarda el original.
    await page.evaluate(() => {
      window.copiaRevista = window.DATOS_INCRUSTADOS['revistas/prueba-0002.json'];
      window.DATOS_INCRUSTADOS['revistas/prueba-0002.json'] = { dañado: true };
    });
    await page.getByRole('link', { name: 'Cuadernos de Ejemplo de Sociología Urbana' }).click();
    await esperarVista(page, 'No se han podido cargar los datos');
    await expect(page.locator('h1')).toBeFocused();
    expect(await analizarConAxe(page)).toEqual([]);
    await page.evaluate(() => { window.DATOS_INCRUSTADOS['revistas/prueba-0002.json'] = window.copiaRevista; });
    await page.getByRole('button', { name: /Reintentar/ }).click();
    await expect(page.locator('h1')).toHaveText('Cuadernos de Ejemplo de Sociología Urbana');
  });
});

test.describe('variante para el visor de artefactos', () => {
  test('declara el idioma español aunque el esqueleto no lo haga', async ({ page }) => {
    await page.goto(url(ARTEFACTO));
    await esperarVista(page, 'Revistas de sociología en español');
    await expect(page.locator('html')).toHaveAttribute('lang', 'es');
    await expect(page.locator('h1')).toHaveCount(1);
    expect(await analizarConAxe(page)).toEqual([]);
  });

  test('conserva rutas, foco y anuncios dentro del esqueleto', async ({ page }) => {
    const ficha = listado.revistas[0];
    await page.goto(url(ARTEFACTO));
    await esperarVista(page, 'Revistas de sociología en español');
    await page.getByRole('link', { name: ficha.titulo, exact: true }).click();
    await expect(page.locator('h1')).toHaveText(ficha.titulo);
    await expect(page.locator('h1')).toBeFocused();
    await expect(page.locator('#anuncios')).toContainText('Ficha de la revista cargada.');
    expect(await analizarConAxe(page)).toEqual([]);
  });

  for (const caso of [
    { tema: 'dark', sistema: 'light', fondo: 'rgb(18, 20, 23)' },
    { tema: 'light', sistema: 'dark', fondo: 'rgb(255, 255, 255)' },
  ]) {
    test(`sigue el tema elegido en el visor (${caso.tema}) aunque el sistema esté en ${caso.sistema}`, async ({ browser }) => {
      const archivo = path.join(CARPETA, `revistas-artefacto-${caso.tema}.html`);
      simularVisor(path.join(CARPETA, 'revistas-artefacto.html'), archivo, caso.tema);
      const contexto = await browser.newContext({ colorScheme: caso.sistema });
      const page = await contexto.newPage();
      await page.goto(url(archivo));
      await esperarVista(page, 'Revistas de sociología en español');
      expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe(caso.fondo);
      expect(await analizarConAxe(page)).toEqual([]);
      await contexto.close();
    });
  }
});
