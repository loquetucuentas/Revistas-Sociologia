// Vista de lectura del texto completo, con el artículo ficticio de
// pruebas/datos: atribución, tabla de contenidos, notas de ida y vuelta,
// figuras sin imagen, tablas, idiomas, copiar la cita, temas, reflujo,
// vuelta al índice con la posición y axe.
const { test, expect } = require('@playwright/test');
const { usarDatosDePrueba, analizarConAxe, esperarVista } = require('./utilidades');

const INDICE = '/#/revista/prueba-0001/numero/v12-n2-2026';
const LECTURA = INDICE + '/articulo/prueba-0001-v12-n2-1';
const TITULO = 'Artículo de prueba 1: una aproximación ficticia al estudio de trabajo de cuidados';
const CITA = 'Autora de Prueba, P. y Ficticia, O. P. (2026). ' + TITULO +
  '. Revista de Prueba de Estudios Sociales, 12(2), 1–20. https://doi.org/10.0000/prueba-0001.0.1';

test.beforeEach(async ({ page }) => {
  await usarDatosDePrueba(page);
});

async function abrirLectura(page) {
  await page.goto(INDICE);
  await esperarVista(page, 'Vol. 12, núm. 2');
  await page.getByRole('link', { name: /^Leer el artículo completo\s*:\s*Artículo de prueba 1/ }).click();
  await expect(page.locator('h1')).toHaveText(TITULO);
}

test('el índice dice con texto qué artículos se leen aquí y cuáles en la revista', async ({ page }) => {
  await page.goto(INDICE);
  await esperarVista(page, 'Vol. 12, núm. 2');
  const tarjetas = page.locator('li.articulo');
  await expect(tarjetas.nth(0)).toContainText('Lectura completa disponible en esta aplicación.');
  for (const i of [1, 2, 3]) {
    await expect(tarjetas.nth(i)).toContainText('Texto completo solo en la web de la revista.');
    await expect(tarjetas.nth(i).getByRole('link', { name: /Leer el artículo completo/ })).toHaveCount(0);
  }
});

test('al entrar: un único h1 con el foco, título del documento, migas y anuncio', async ({ page }) => {
  await abrirLectura(page);
  await expect(page.locator('h1')).toHaveCount(1);
  await expect(page.locator('h1')).toBeFocused();
  await expect(page).toHaveTitle(TITULO + ' · Revistas de sociología en acceso abierto');
  await expect(page.locator('nav [aria-current="page"]')).toHaveText(TITULO);
  await expect(page.locator('#anuncios')).toHaveText(
    'Artículo cargado para su lectura. 4 secciones. Licencia CC BY 4.0. 1 figura no tiene descripción en la revista.');
});

test('la atribución completa va antes del texto y se repite la cita al final', async ({ page }) => {
  await abrirLectura(page);
  const atribucion = page.locator('section.atribucion');
  await expect(atribucion).toContainText('Persona Autora de Prueba 1, Otra Persona Ficticia');
  await expect(atribucion).toContainText('Revista de Prueba de Estudios Sociales, Vol. 12, núm. 2 (2026), páginas 1-20.');
  await expect(atribucion).toContainText('10.0000/prueba-0001.0.1');
  await expect(atribucion).toContainText('Creative Commons Atribución 4.0 Internacional (CC BY 4.0)');
  await expect(atribucion.locator('#cita-inicial')).toHaveText(CITA);
  await expect(atribucion).toContainText('Solo se han modificado el formato y la presentación');
  await expect(atribucion).toContainText('Copyright (c) 2026 Persona Autora de Prueba.');
  const legal = atribucion.getByRole('link', { name: /Texto legal de la licencia/ });
  await expect(legal).toHaveAttribute('href', 'https://creativecommons.org/licenses/by/4.0/legalcode.es');
  await expect(legal).toContainText('sitio externo, se abre en una pestaña nueva');
  // La atribución precede al texto en el orden del documento.
  const orden = await page.evaluate(() => {
    const a = document.querySelector('section.atribucion');
    const t = document.querySelector('.texto-articulo');
    return Boolean(a.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING);
  });
  expect(orden).toBe(true);
  await expect(page.locator('#cita-final-texto')).toHaveText(CITA);
  const original = page.getByRole('link', { name: /^Ver y citar en la web de la revista/ });
  await expect(original).toHaveCount(2);
  for (const enlace of await original.all()) {
    await expect(enlace).toHaveAttribute('href', 'https://example.org/prueba-0001/articulo/0-1');
    await expect(enlace).toHaveAttribute('target', '_blank');
    await expect(enlace).toContainText('sitio externo, se abre en una pestaña nueva');
  }
});

test('la tabla de contenidos lleva a cada sección sin cambiar de vista', async ({ page }) => {
  await abrirLectura(page);
  const indice = page.getByRole('navigation', { name: 'Contenido del artículo' });
  await expect(indice.getByRole('link')).toHaveText(['Introducción', 'Objetivos', 'Resultados', 'Notas', 'Referencias']);
  const url = page.url();
  await indice.getByRole('link', { name: 'Resultados' }).click();
  await expect(page.locator('#t-s2-titulo')).toBeFocused();
  expect(page.url()).toBe(url);
  await expect(page.locator('h1')).toHaveText(TITULO);
});

test('las notas y referencias se recorren de ida y vuelta', async ({ page }) => {
  await abrirLectura(page);
  await page.locator('a[href="#t-nota-1"]').click();
  await expect(page.locator('#t-nota-1')).toBeFocused();
  await page.locator('#t-nota-1').getByRole('link', { name: 'Volver al texto' }).click();
  await expect(page.locator('#t-llamada-nota-1-1')).toBeFocused();
  await page.locator('a[href="#t-ref-1"]').click();
  await expect(page.locator('#t-ref-1')).toBeFocused();
  await page.locator('#t-ref-1').getByRole('link', { name: 'Volver al texto' }).click();
  await expect(page.locator('#t-llamada-ref-1-1')).toBeFocused();
  expect(new URL(page.url()).hash).toBe('#' + LECTURA.slice(2));
});

test('figuras, tablas, idiomas y enlaces del texto', async ({ page }) => {
  await abrirLectura(page);
  const texto = page.locator('.texto-articulo');
  await expect(texto.locator('img')).toHaveCount(0);
  await expect(texto).toContainText('Descripción de la revista: Gráfico de líneas que sube de 5 casos en 2021 a 9 en 2023.');
  await expect(texto.locator('.figura-sustituida--sin-descripcion')).toContainText('Aviso: esta figura no dispone de descripción en la revista.');
  await expect(texto.getByRole('link', { name: /Ver la figura en la web de la revista/ })).toHaveCount(2);
  const tabla = texto.getByRole('region', { name: 'Tabla 1. Casos ficticios por año y territorio' });
  await expect(tabla).toHaveAttribute('tabindex', '0');
  await expect(tabla.locator('th[scope="col"]')).toHaveCount(7);
  await expect(tabla.locator('th[scope="row"]')).toHaveCount(3);
  await expect(texto.locator('p[lang="en"]')).toHaveText('This paragraph is written in English to check that screen readers switch voice.');
  await expect(texto.locator('blockquote')).toHaveCount(1);
  const externo = texto.getByRole('link', { name: /la web ficticia del proyecto/ });
  await expect(externo).toHaveAttribute('target', '_blank');
  await expect(externo).toContainText('sitio externo, se abre en una pestaña nueva');
  await expect(texto.locator('script, style, iframe')).toHaveCount(0);
});

test('el botón copia la cita y lo anuncia', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await abrirLectura(page);
  await page.getByRole('button', { name: 'Copiar la cita' }).click();
  await expect(page.locator('#anuncios')).toHaveText('Cita copiada.');
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(CITA);
});

test('el botón atrás vuelve al índice con la posición y el foco en el artículo leído', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 500 });
  await page.goto(INDICE);
  await esperarVista(page, 'Vol. 12, núm. 2');
  const leer = page.getByRole('link', { name: /^Leer el artículo completo\s*:\s*Artículo de prueba 1/ });
  await leer.scrollIntoViewIfNeeded();
  const posicion = await page.evaluate(() => window.scrollY);
  await leer.click();
  await expect(page.locator('h1')).toHaveText(TITULO);
  await page.goBack();
  await expect(page.locator('h1')).toContainText('Vol. 12, núm. 2');
  await expect(page.locator('#leer-prueba-0001-v12-n2-1')).toBeFocused();
  expect(Math.abs(await page.evaluate(() => window.scrollY) - posicion)).toBeLessThan(5);
  await expect(page.locator('#anuncios')).toHaveText('Has vuelto al índice del número, en el artículo que estabas leyendo.');
});

test('un artículo sin texto completo explica por qué y ofrece salida', async ({ page }) => {
  await page.goto(INDICE + '/articulo/10.0000%2Fprueba-0001.0.2');
  await esperarVista(page, 'Este artículo no se puede leer en la aplicación');
  await expect(page.getByRole('link', { name: 'Ir al índice del número' })).toBeVisible();
  expect(await analizarConAxe(page)).toEqual([]);
});

test('el tema de colores se elige, se anuncia y se recuerda', async ({ page }) => {
  await abrirLectura(page);
  await page.getByLabel('Tema de colores').selectOption('contraste');
  await expect(page.locator('html')).toHaveAttribute('data-tema', 'contraste');
  await expect(page.locator('#anuncios')).toHaveText('Tema de colores: alto contraste.');
  expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(0, 0, 0)');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-tema', 'contraste');
  await page.getByLabel('Tema de colores').selectOption('');
  await expect(page.locator('html')).not.toHaveAttribute('data-tema', /.+/);
});

for (const ancho of [320, 1280]) {
  test(`sin scroll horizontal en la lectura a ${ancho} píxeles con el texto al 200 por ciento`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: 800 });
    await abrirLectura(page);
    for (let i = 0; i < 4; i++) await page.getByRole('button', { name: /Aumentar/ }).click();
    await expect(page.locator('#texto-tamano-valor')).toHaveText('200 %');
    const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(desborde).toBeLessThanOrEqual(0);
  });
}

test('la línea de lectura no supera unos 75 caracteres', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await abrirLectura(page);
  const caracteres = await page.evaluate(() => {
    const p = document.querySelector('.texto-articulo p');
    const tamano = parseFloat(getComputedStyle(p).fontSize);
    return p.getBoundingClientRect().width / (tamano * 0.5);
  });
  expect(caracteres).toBeLessThanOrEqual(75);
  const interlineado = await page.evaluate(() => {
    const p = document.querySelector('.texto-articulo p');
    return parseFloat(getComputedStyle(p).lineHeight) / parseFloat(getComputedStyle(p).fontSize);
  });
  expect(interlineado).toBeGreaterThanOrEqual(1.5);
});

const CONDICIONES = [
  { nombre: 'tema automático claro', opciones: { colorScheme: 'light' } },
  { nombre: 'tema automático oscuro', opciones: { colorScheme: 'dark' } },
  { nombre: '320 píxeles de ancho', opciones: { viewport: { width: 320, height: 640 } } },
];
for (const condicion of CONDICIONES) {
  test.describe(condicion.nombre, () => {
    test.use(condicion.opciones);
    test(`axe sin errores en la vista de lectura (${condicion.nombre})`, async ({ page }) => {
      await page.goto(LECTURA);
      await expect(page.locator('h1')).toHaveText(TITULO);
      expect(await analizarConAxe(page)).toEqual([]);
    });
  });
}

for (const tema of ['claro', 'oscuro', 'contraste']) {
  test(`axe sin errores en la lectura y el índice con el tema ${tema}`, async ({ page }) => {
    await page.goto(LECTURA);
    await expect(page.locator('h1')).toHaveText(TITULO);
    await page.getByLabel('Tema de colores').selectOption(tema);
    expect(await analizarConAxe(page)).toEqual([]);
    await page.goto(INDICE);
    await esperarVista(page, 'Vol. 12, núm. 2');
    expect(await analizarConAxe(page)).toEqual([]);
  });
}

test('axe sin errores en la lectura con el texto al 200 por ciento', async ({ page }) => {
  await page.goto(LECTURA);
  await expect(page.locator('h1')).toHaveText(TITULO);
  for (let i = 0; i < 4; i++) await page.getByRole('button', { name: /Aumentar/ }).click();
  expect(await analizarConAxe(page)).toEqual([]);
});
