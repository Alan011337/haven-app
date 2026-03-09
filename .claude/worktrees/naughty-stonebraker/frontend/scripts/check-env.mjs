#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import process from 'process';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';

const SCRIPT_FILE = fileURLToPath(import.meta.url);
const FRONTEND_ROOT = path.resolve(path.dirname(SCRIPT_FILE), '..');
const ENV_FILE = path.join(FRONTEND_ROOT, '.env.local');

if (fs.existsSync(ENV_FILE)) {
  dotenv.config({ path: ENV_FILE });
} else {
  dotenv.config();
}

const required = ['NEXT_PUBLIC_API_URL'];
const optional = [
  'NEXT_PUBLIC_WS_URL',
  'NEXT_PUBLIC_SUPABASE_URL',
  'NEXT_PUBLIC_SUPABASE_ANON_KEY',
  'SUPABASE_SERVICE_ROLE_KEY',
];

const missing = [];
const invalid = [];

for (const key of required) {
  const value = process.env[key];
  if (!value || !value.trim()) {
    missing.push(key);
  }
}

const apiUrl = process.env.NEXT_PUBLIC_API_URL;
if (apiUrl) {
  try {
    const parsed = new URL(apiUrl);
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      invalid.push('NEXT_PUBLIC_API_URL must use http:// or https://');
    }
  } catch {
    invalid.push('NEXT_PUBLIC_API_URL must be a valid URL');
  }
}

const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
if (wsUrl) {
  try {
    const parsed = new URL(wsUrl);
    if (!['ws:', 'wss:'].includes(parsed.protocol)) {
      invalid.push('NEXT_PUBLIC_WS_URL must use ws:// or wss://');
    }
  } catch {
    invalid.push('NEXT_PUBLIC_WS_URL must be a valid URL');
  }
}

console.log('[frontend env check]');
console.log(`  loaded_from: ${fs.existsSync(ENV_FILE) ? ENV_FILE : 'process env'}`);

if (missing.length) {
  console.log('  missing_required:');
  for (const key of missing) {
    console.log(`    - ${key}`);
  }
}

if (invalid.length) {
  console.log('  invalid_values:');
  for (const issue of invalid) {
    console.log(`    - ${issue}`);
  }
}

console.log('  optional_present:');
for (const key of optional) {
  console.log(`    - ${key}: ${process.env[key] ? 'yes' : 'no'}`);
}

if (missing.length || invalid.length) {
  console.log('result: fail');
  process.exit(1);
}

console.log('result: ok');
