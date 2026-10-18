// Análisis automático con axe de todas las vistas y estados, en distintas
// condiciones: tema claro y oscuro, ancho de 320 píxeles (equivalente a un
// zoom del 400 por ciento) y texto aumentado al 200 por ciento.
const { test, expect } = require('@playwright/test');
const { usarDatosDePrueba, analizarConAxe, esperarVista } = require('./utilidades');

const VISTAS = [
  { nombre: 'listado', ruta: '/#/', h1: 'Revistas de sociología en español' },
  { nombre: 'ficha de revista', ruta: '/#/revista/prueba-0001', h1: 'Revista de Prueba de Estudios Sociales' },
  { nombre: 'índice de número', ruta: '/#/revista/prueba-0001/numero/v12-n2-2026', h1: 'Vol. 12, núm. 2 (2026)' },
  { nombre: 'revista sin números (estado vacío)', ruta: '/#/revista/prueba-0005', h1: 'Revista de Prueba sin Números' },
  { nombre: 'número sin artículos (estado vacío)', ruta: '/#/revista/prueba-0003/numero/v12-n1-2026', h1: 'Vol. 12, núm. 1 (2026)' },
  { nombre: 'revista inexistente', ruta: '/#/revista/no-existe', h1: 'No hemos encontrado esta revista' },
  { nombre: 'página inexistente', ruta: '/#/otra/cosa', h1: 'Página no encontrada' },
];

const CONDICIONES = [
  { nombre: 'tema claro', opciones: { colorScheme: 'light' } },
  { nombre: 'tema oscuro', opciones: { colorScheme: 'dark' } },
  { nombre: '320 píxeles de ancho', opciones: { viewport: { width: 320, height: 640 } } },
];

for (const condicion of CONDICIONES) {
  test.describe(condicion.nombre, () => {
    test.use(condicion.opciones);
    for (const vista of VISTAS) {
      test(`axe sin errores: ${vista.nombre}`, async ({ page }) => {
        await usarDatosDePrueba(page);
        await page.goto(vista.ruta);
        await esperarVista(page, vista.h1);
        // Se abren los resúmenes para analizar también su contenido.
        await page.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; }));
        expect(await analizarConAxe(page)).toEqual([]);
      });
    }
  });
}

test('axe sin errores con el texto al 200 por ciento', async ({ page }) => {
  await usarDatosDePrueba(page);
  await page.goto('/#/revista/prueba-0001/numero/v12-n2-2026');
  await esperarVista(page, 'Vol. 12, núm. 2');
  for (let i = 0; i < 4; i++) await page.getByRole('button', { name: /Aumentar/ }).click();
  await expect(page.locator('#texto-tamano-valor')).toHaveText('200 %');
  expect(await analizarConAxe(page)).toEqual([]);
});

test('axe sin errores en el estado de error', async ({ page }) => {
  await page.route('**/data/**', (ruta) => ruta.abort('internetdisconnected'));
  await page.goto('/#/');
  await esperarVista(page, 'No se han podido cargar los datos');
  expect(await analizarConAxe(page)).toEqual([]);
});

test('axe sin errores en el estado de carga', async ({ page }) => {
  await page.route('**/data/**', () => { /* nunca responde: se queda cargando */ });
  await page.goto('/#/');
  await esperarVista(page, 'Cargando');
  expect(await analizarConAxe(page)).toEqual([]);
});

test('axe sin errores en el listado sin resultados de búsqueda', async ({ page }) => {
  await usarDatosDePrueba(page);
  await page.goto('/#/');
  await esperarVista(page, 'Revistas de sociología');
  await page.getByLabel('Buscar por nombre de revista').fill('zzzz');
  await expect(page.getByText('Ninguna revista coincide con «zzzz».')).toBeVisible();
  expect(await analizarConAxe(page)).toEqual([]);
});
