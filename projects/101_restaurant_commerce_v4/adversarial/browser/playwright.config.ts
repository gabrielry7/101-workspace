import { defineConfig } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const configPath=process.env.COMMERCE_RUN_CONFIG;
const config=configPath ? JSON.parse(fs.readFileSync(configPath,'utf8')) : {};
const output=process.env.COMMERCE_BROWSER_OUTPUT || '/tmp/101-commerce-browser-unconfigured';
export default defineConfig({
  testDir:'.',testMatch:['tests/*.spec.ts'],fullyParallel:false,workers:1,retries:0,
  timeout:35000,expect:{timeout:8000},
  outputDir:path.join(output,'traces'),
  reporter:[['list'],['json',{outputFile:path.join(output,'playwright.json')}]],
  use:{baseURL:config.base_url || 'http://127.0.0.1:1',headless:true,
    launchOptions:{executablePath:'/usr/bin/chromium'},
    trace:'retain-on-failure',screenshot:'only-on-failure',actionTimeout:10000},
});
