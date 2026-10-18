// Utilidades compartidas por las pruebas.
const path = require('path');
const fs = require('fs');
const AxeBuilder = require('@axe-core/playwright').default;

const CARPETA_DATOS = path.join(__dirname, 'datos');

// Sirve siempre los datos de prueba de pruebas/datos, sean cuales sean los
// datos reales de data/, para que las pruebas sean estables.
async function usarDatosDePrueba(page) {
  await page.route('**/data/**', async (ruta) => {
    const relativa = new URL(ruta.request().url()).pathname.replace(/^.*\/data\//, '');
    const archivo = path.join(CARPETA_DATOS, relativa);
    if (!archivo.startsWith(CARPETA_DATOS) || !fs.existsSync(archivo)) {
      await ruta.fulfill({ status: 404, body: 'No encontrado' });
      return;
    }
    await ruta.fulfill({
      status: 200,
      contentType: archivo.endsWith('.json') ? 'application/json' : 'text/javascript',
      body: fs.readFileSync(archivo),
    });
  });
}

// Normas WCAG 2.0, 2.1 y 2.2 en niveles A y AA, más buenas prácticas.
async function analizarConAxe(page) {
  const resultado = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
    .analyze();
  return resultado.violations.map((v) => ({
    regla: v.id,
    impacto: v.impact,
    descripcion: v.help,
    nodos: v.nodes.map((n) => n.target.join(' ')),
  }));
}

async function esperarVista(page, textoH1) {
  await page.locator('h1', { hasText: textoH1 }).waitFor();
}

module.exports = { usarDatosDePrueba, analizarConAxe, esperarVista };
