// Phase 0, stream D. Points at docker-compose.e2e.yml's web service.
// @ts-check
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'line' : 'list',
  use: {
    baseURL: process.env.POOTLE_E2E_BASE_URL || 'http://localhost:8000',
    trace: 'retain-on-failure',
  },
});
