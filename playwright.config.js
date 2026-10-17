// Configuración de las pruebas automáticas de accesibilidad y comportamiento.
const { defineConfig } = require('@playwright/test');
const fs = require('fs');

// En el entorno de desarrollo en la nube Chromium ya está instalado aquí.
const chromiumLocal = '/opt/pw-browsers/chromium';

module.exports = defineConfig({
  testDir: 'pruebas',
  timeout: 30000,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    locale: 'es-ES',
    launchOptions: fs.existsSync(chromiumLocal) && !process.env.CI ? { executablePath: chromiumLocal } : {},
  },
  webServer: {
    command: 'python3 -m http.server 4173 --bind 127.0.0.1',
    url: 'http://127.0.0.1:4173/index.html',
    reuseExistingServer: !process.env.CI,
  },
});
