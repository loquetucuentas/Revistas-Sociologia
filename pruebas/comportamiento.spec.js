// Comprobaciones de comportamiento accesible: teclado, foco, anuncios,
// rutas, reflujo, tamaño de las áreas de pulsación e idiomas.
const path = require('path');
const { test, expect } = require('@playwright/test');
const { usarDatosDePrueba, esperarVista } = require('./utilidades');

test.beforeEach(async ({ page }) => {
  await usarDatosDePrueba(page);
});

test('la página declara el idioma español y tiene los puntos de referencia', async ({ page }) => {
  await page.goto('/');
  await esperarVista(page, 'Revistas de sociología en español');
  await expect(page.locator('html')).toHaveAttribute('lang', 'es');
  await expect(page.locator('header')).toHaveCount(1);
  await expect(page.locator('nav')).toHaveCount(1);
  await expect(page.locator('main')).toHaveCount(1);
  await expect(page.locator('footer')).toHaveCount(1);
  await expect(page.locator('h1')).toHaveCount(1);
});

test('el enlace de salto es lo primero, se ve con el foco y lleva al contenido', async ({ page }) => {
  await page.goto('/');
  await esperarVista(page, 'Revistas de sociología');
  await page.keyboard.press('Tab');
  const salto = page.getByRole('link', { name: 'Saltar al contenido principal' });
  await expect(salto).toBeFocused();
  await expect(salto).toBeInViewport();
  await page.keyboard.press('Enter');
  await expect(page.locator('h1')).toBeFocused();
  // La dirección no cambia: la ruta sigue siendo la misma.
  expect(new URL(page.url()).hash).not.toBe('#contenido');
});

test('al cambiar de vista se mueve el foco, cambia el título y se anuncia', async ({ page }) => {
  await page.goto('/');
  await esperarVista(page, 'Revistas de sociología');
  await page.getByRole('link', { name: 'Revista de Prueba de Estudios Sociales' }).click();
  const h1 = page.locator('h1');
  await expect(h1).toHaveText('Revista de Prueba de Estudios Sociales');
  await expect(h1).toBeFocused();
  await expect(page).toHaveTitle('Revista de Prueba de Estudios Sociales · Revistas de sociología en acceso abierto');
  await expect(page.locator('#anuncios')).toHaveText('Ficha de la revista cargada. 3 números disponibles.');
  await expect(page.locator('#anuncios')).toHaveAttribute('aria-live', 'polite');

  await page.getByRole('link', { name: 'Vol. 12, núm. 2 (2026)' }).click();
  await expect(h1).toContainText('Vol. 12, núm. 2 (2026)');
  await expect(h1).toBeFocused();
  await expect(page.locator('#anuncios')).toHaveText('Índice del número cargado. 4 artículos. Uno se puede leer completo en esta aplicación.');
  await expect(page.locator('nav [aria-current="page"]')).toHaveText('Vol. 12, núm. 2 (2026)');
});

test('el botón atrás del navegador vuelve a la vista anterior', async ({ page }) => {
  await page.goto('/');
  await esperarVista(page, 'Revistas de sociología');
  await page.getByRole('link', { name: 'Revista de Prueba de Estudios Sociales' }).click();
  await esperarVista(page, 'Revista de Prueba de Estudios Sociales');
  await page.goBack();
  await expect(page.locator('h1')).toHaveText('Revistas de sociología en español');
  await expect(page.locator('h1')).toBeFocused();
  await page.goForward();
  await expect(page.locator('h1')).toHaveText('Revista de Prueba de Estudios Sociales');
});

test('el listado está en orden alfabético español y se puede invertir', async ({ page }) => {
  await page.goto('/');
  await esperarVista(page, 'Revistas de sociología');
  const titulos = page.locator('#lista-revistas h3');
  await expect(titulos).toHaveText([
    'Ánfora de Prueba: Sociología y Cultura',
    'Cuadernos de Ejemplo de Sociología Urbana',
    'Ñandú, revista de prueba',
    'Revista de Prueba de Estudios Sociales',
    'Revista de Prueba sin Números',
  ]);
  await page.getByLabel('Orden').selectOption('desc');
  await expect(titulos.first()).toHaveText('Revista de Prueba sin Números');
  await expect(page.locator('#anuncios')).toHaveText('Revistas ordenadas de la Z a la A.');
});

test('el buscador ignora tildes y mayúsculas y anuncia los resultados', async ({ page }) => {
  await page.goto('/');
  await esperarVista(page, 'Revistas de sociología');
  const buscador = page.getByLabel('Buscar por nombre de revista');
  await expect(buscador).toHaveAttribute('aria-describedby', 'busqueda-ayuda');
  await buscador.fill('ANFORA');
  await expect(page.locator('#lista-revistas h3')).toHaveText(['Ánfora de Prueba: Sociología y Cultura']);
  await expect(page.locator('#anuncios')).toHaveText('Se muestran 1 de 5 revistas para la búsqueda «ANFORA».');
  await buscador.press('Enter');
  await expect(page).toHaveURL(/#\/$|\/$/);
});

test('sin resultados se explica qué hacer y se puede borrar la búsqueda', async ({ page }) => {
  await page.goto('/');
  await esperarVista(page, 'Revistas de sociología');
  await page.getByLabel('Buscar por nombre de revista').fill('xyz');
  await expect(page.getByText('Prueba con una palabra más corta')).toBeVisible();
  await page.getByRole('button', { name: 'Borrar la búsqueda y ver todas las revistas' }).click();
  await expect(page.locator('#lista-revistas h3')).toHaveCount(5);
  await expect(page.getByLabel('Buscar por nombre de revista')).toBeFocused();
});

test('la búsqueda se conserva al volver al listado', async ({ page }) => {
  await page.goto('/');
  await esperarVista(page, 'Revistas de sociología');
  await page.getByLabel('Buscar por nombre de revista').fill('cuadernos');
  await page.getByRole('link', { name: 'Cuadernos de Ejemplo de Sociología Urbana' }).click();
  await esperarVista(page, 'Cuadernos de Ejemplo');
  await page.goBack();
  await expect(page.getByLabel('Buscar por nombre de revista')).toHaveValue('cuadernos');
  await expect(page.locator('#lista-revistas h3')).toHaveCount(1);
});

test('los enlaces externos avisan de que se abren en una pestaña nueva', async ({ page }) => {
  await page.goto('/#/revista/prueba-0001/numero/v12-n2-2026');
  await esperarVista(page, 'Vol. 12, núm. 2');
  const enlaces = page.locator('main a[target="_blank"]');
  expect(await enlaces.count()).toBeGreaterThan(0);
  for (const enlace of await enlaces.all()) {
    await expect(enlace).toContainText('se abre en una pestaña nueva');
    await expect(enlace).toHaveAttribute('rel', /noopener/);
  }
  const primero = page.getByRole('link', { name: /^Leer en la web de la revista ?: Artículo de prueba 1/ });
  await expect(primero).toHaveAttribute('href', /^https:\/\/example\.org\//);
});

test('los textos en otro idioma llevan su atributo lang', async ({ page }) => {
  await page.goto('/#/revista/prueba-0001/numero/v12-n2-2026');
  await esperarVista(page, 'Vol. 12, núm. 2');
  const titulo = page.locator('h3', { hasText: 'Test article' });
  await expect(titulo).toHaveAttribute('lang', 'en');
  await expect(page.locator('p.articulo__resumen[lang="en"]')).toHaveCount(1);
  // Los textos en español no llevan lang propio: heredan el de la página.
  await expect(page.locator('h3', { hasText: 'Artículo de prueba 1' })).not.toHaveAttribute('lang', /.+/);
});

test('el resumen se despliega con el teclado', async ({ page }) => {
  await page.goto('/#/revista/prueba-0001/numero/v12-n2-2026');
  await esperarVista(page, 'Vol. 12, núm. 2');
  const resumen = page.locator('summary').first();
  // Las decoraciones son formas de CSS y no forman parte del nombre.
  await expect(resumen).toHaveAccessibleName(/^Resumen del artículo: Artículo de prueba 1/);
  await resumen.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('details').first()).toHaveAttribute('open', '');
  await expect(page.getByText('Resumen no disponible en la fuente.')).toBeVisible();
});

test('los controles de tamaño de texto funcionan, se anuncian y se recuerdan', async ({ page }) => {
  await page.goto('/');
  await esperarVista(page, 'Revistas de sociología');
  const reducir = page.getByRole('button', { name: /Reducir/ });
  await expect(reducir).toHaveAttribute('aria-disabled', 'true');
  await page.getByRole('button', { name: /Aumentar/ }).click();
  await expect(page.locator('#texto-tamano-valor')).toHaveText('125 %');
  await expect(page.locator('#anuncios')).toHaveText('Tamaño del texto: 125 %.');
  const tamano = await page.evaluate(() => getComputedStyle(document.documentElement).fontSize);
  expect(tamano).toBe('20px');
  await page.reload();
  await expect(page.locator('#texto-tamano-valor')).toHaveText('125 %');
  await page.getByRole('button', { name: /Normal/ }).click();
  await expect(page.locator('#texto-tamano-valor')).toHaveText('100 %');
});

test.describe('reflujo a 320 píxeles (zoom del 400 por ciento)', () => {
  test.use({ viewport: { width: 320, height: 640 } });
  for (const ruta of ['/#/', '/#/revista/prueba-0001', '/#/revista/prueba-0001/numero/v12-n2-2026']) {
    test(`sin scroll horizontal en ${ruta}, también con el texto al 200 por ciento`, async ({ page }) => {
      await page.goto(ruta);
      await page.locator('h1').waitFor();
      await page.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; }));
      const desborda = () => page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
      expect(await desborda()).toBe(false);
      for (let i = 0; i < 4; i++) await page.getByRole('button', { name: /Aumentar/ }).click();
      expect(await desborda()).toBe(false);
    });
  }
});

test('las áreas de pulsación miden al menos 44 por 44 píxeles', async ({ page }) => {
  for (const ruta of ['/#/', '/#/revista/prueba-0001', '/#/revista/prueba-0001/numero/v12-n2-2026']) {
    await page.goto(ruta);
    await page.locator('h1').waitFor();
    const pequenos = await page.evaluate(() => {
      // Los enlaces dentro de un párrafo de texto quedan exentos (WCAG 2.5.8).
      const controles = document.querySelectorAll('button, input, select, summary, a:not(p > a):not(.salto)');
      return Array.from(controles).filter((c) => {
        const r = c.getBoundingClientRect();
        return r.width > 0 && (r.width < 44 || r.height < 44);
      }).map((c) => `${c.tagName} «${c.textContent.trim().slice(0, 40)}» ${Math.round(c.getBoundingClientRect().width)}x${Math.round(c.getBoundingClientRect().height)}`);
    });
    expect(pequenos, ruta).toEqual([]);
  }
});

test('el foco se ve y no queda tapado al recorrer la página con el tabulador', async ({ page }) => {
  await page.goto('/#/revista/prueba-0001/numero/v12-n2-2026');
  await esperarVista(page, 'Vol. 12, núm. 2');
  for (let i = 0; i < 25; i++) {
    await page.keyboard.press('Tab');
    const info = await page.evaluate(() => {
      const activo = document.activeElement;
      const estilo = getComputedStyle(activo);
      const r = activo.getBoundingClientRect();
      const centro = document.elementFromPoint(r.left + r.width / 2, r.top + Math.min(r.height / 2, 10));
      if (activo === document.body) return null;
      return {
        nombre: activo.tagName + ' ' + activo.textContent.trim().slice(0, 30),
        contorno: estilo.outlineStyle !== 'none' && parseFloat(estilo.outlineWidth) >= 2,
        tapado: !(activo === centro || activo.contains(centro)),
      };
    });
    if (!info) break; // se ha recorrido toda la página
    expect(info.contorno, `foco visible en ${info.nombre}`).toBe(true);
    expect(info.tapado, `foco no tapado en ${info.nombre}`).toBe(false);
  }
});

test('los fallos de red muestran un error con instrucciones y se puede reintentar', async ({ page }) => {
  let fallar = true;
  // La última ruta registrada se aplica primero y, si no falla, pasa a los datos de prueba.
  await page.route('**/data/**', async (ruta) => {
    if (fallar) return ruta.abort('internetdisconnected');
    return ruta.fallback();
  });
  await page.goto('/#/');
  await esperarVista(page, 'No se han podido cargar los datos');
  await expect(page.getByText('Qué puedes hacer:')).toBeVisible();
  fallar = false;
  await page.getByRole('button', { name: 'Reintentar' }).click();
  await expect(page.locator('h1')).toHaveText('Revistas de sociología en español');
  await expect(page.locator('h1')).toBeFocused();
});

test('mientras carga se muestra un estado de carga accesible', async ({ page }) => {
  let soltar;
  const espera = new Promise((r) => { soltar = r; });
  await page.route('**/data/**', async (ruta) => { await espera; return ruta.fallback(); });
  await page.goto('/#/');
  await expect(page.locator('h1')).toHaveText('Cargando…');
  await expect(page.getByRole('status')).toContainText('Cargando el listado de revistas');
  soltar();
  await expect(page.locator('h1')).toHaveText('Revistas de sociología en español');
});

test('una dirección de número inexistente ofrece salidas claras', async ({ page }) => {
  await page.goto('/#/revista/prueba-0001/numero/no-existe');
  await esperarVista(page, 'No hemos encontrado este número');
  await expect(page.getByRole('link', { name: 'Ver los números disponibles de la revista' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Volver al listado de revistas' })).toBeVisible();
});

test('nada depende solo del color: los enlaces están subrayados', async ({ page }) => {
  await page.goto('/#/revista/prueba-0001');
  await esperarVista(page, 'Revista de Prueba');
  const sinSubrayar = await page.evaluate(() => Array.from(document.querySelectorAll('main a:not(.boton)'))
    .filter((a) => !getComputedStyle(a).textDecorationLine.includes('underline')).map((a) => a.textContent));
  expect(sinSubrayar).toEqual([]);
});

test('funciona abriendo el archivo directamente, sin servidor', async ({ page }) => {
  await page.unroute('**/data/**');
  await page.goto('file://' + path.join(__dirname, '..', 'index.html'));
  await expect(page.locator('h1')).toHaveText('Revistas de sociología en español');
  expect(await page.locator('#lista-revistas li').count()).toBeGreaterThan(0);
});
