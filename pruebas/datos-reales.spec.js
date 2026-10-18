// Comprobaciones con los datos reales de la carpeta data, que cambian cada
// semana: axe en el listado, en la ficha de cada revista y en el índice de
// su número más reciente, y atributo lang de títulos y resúmenes.
const fs = require('fs');
const path = require('path');
const { test, expect } = require('@playwright/test');
const { analizarConAxe, esperarVista } = require('./utilidades');

const DATOS = path.join(__dirname, '..', 'data');
const listado = JSON.parse(fs.readFileSync(path.join(DATOS, 'revistas.json'), 'utf8'));

function leerRevista(ficha) {
  return JSON.parse(fs.readFileSync(path.join(DATOS, ficha.archivo), 'utf8'));
}

// Idioma que debe tener un texto en la página: ninguno propio si es español
// o si el recolector no lo ha podido determinar (hereda lang="es").
function langEsperado(codigo) {
  return codigo && codigo !== 'es' ? codigo : null;
}

test('los datos de la aplicación son reales, no de prueba', () => {
  expect(listado.es_prueba).toBe(false);
  expect(listado.revistas.length).toBeGreaterThan(0);
  for (const ficha of listado.revistas) {
    expect(ficha.id).not.toMatch(/^prueba-/);
    expect(leerRevista(ficha).es_prueba).toBe(false);
  }
});

test('axe sin errores en el listado con datos reales', async ({ page }) => {
  await page.goto('/#/');
  await esperarVista(page, 'Revistas de sociología en español');
  await expect(page.locator('.tarjeta')).toHaveCount(listado.revistas.length);
  expect(await analizarConAxe(page)).toEqual([]);
});

for (const ficha of listado.revistas) {
  test(`datos reales: ${ficha.titulo} (${ficha.id})`, async ({ page }) => {
    const datos = leerRevista(ficha);
    await page.goto(`/#/revista/${encodeURIComponent(ficha.id)}`);
    await expect(page.locator('h1')).toHaveText(ficha.titulo);
    const langRevista = langEsperado(ficha.idioma_titulo);
    if (langRevista) await expect(page.locator('h1')).toHaveAttribute('lang', langRevista);
    else await expect(page.locator('h1')).not.toHaveAttribute('lang', /.+/);
    expect(await analizarConAxe(page)).toEqual([]);

    const numero = datos.numeros[0];
    await page.goto(`/#/revista/${encodeURIComponent(ficha.id)}/numero/${encodeURIComponent(numero.id)}`);
    await expect(page.locator('h1')).toContainText(numero.etiqueta);
    await page.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; }));

    const tarjetas = page.locator('li.articulo');
    await expect(tarjetas).toHaveCount(numero.articulos.length);
    for (let i = 0; i < numero.articulos.length; i++) {
      const articulo = numero.articulos[i];
      const titulo = tarjetas.nth(i).locator('h3');
      const resumen = tarjetas.nth(i).locator('p.articulo__resumen');
      const lt = langEsperado(articulo.idioma_titulo);
      expect(await titulo.getAttribute('lang'), `lang del título «${articulo.titulo}»`).toBe(lt);
      if (articulo.resumen) {
        const lr = langEsperado(articulo.idioma_resumen);
        expect(await resumen.getAttribute('lang'), `lang del resumen de «${articulo.titulo}»`).toBe(lr);
      } else {
        await expect(resumen).toHaveCount(0);
      }
    }
    expect(await analizarConAxe(page)).toEqual([]);

    // Reflujo: sin scroll horizontal a 320 píxeles con títulos y DOI reales.
    await page.setViewportSize({ width: 320, height: 640 });
    const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(desborde).toBeLessThanOrEqual(0);
  });
}
