#!/usr/bin/env node
/**
 * P2-L DS-01: Generate design-tokens.json from globals.css.
 * Single source of truth: frontend/src/app/globals.css.
 * Output: frontend/src/design-tokens.json (for RN, docs, cross-platform).
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const globalsPath = path.join(__dirname, '..', 'src', 'app', 'globals.css');
const outPath = path.join(__dirname, '..', 'src', 'design-tokens.json');

const css = fs.readFileSync(globalsPath, 'utf8');

// Extract :root { ... } block (first brace-balanced block after :root)
const rootMatch = css.match(/:root\s*\{([^]*?)\n\}/);
if (!rootMatch) {
  console.error('generate-design-tokens: could not find :root block in globals.css');
  process.exit(1);
}
const rootBlock = rootMatch[1];

const tokens = {};
const varRe = /--([a-zA-Z0-9-]+)\s*:\s*([^;]+);/g;
let m;
while ((m = varRe.exec(rootBlock)) !== null) {
  const key = m[1];
  const value = m[2].trim();
  if (key.startsWith('font-sans') || key.startsWith('font-art')) continue; // set by next/font
  tokens[key] = value;
}

// Motion tokens may live in @theme inline in Tailwind v4
const themeMatch = css.match(/@theme inline\s*\{([^]*?)\n\}/);
if (themeMatch) {
  const themeBlock = themeMatch[1];
  const themeVarRe = /--(ease-haven|ease-haven-spring|duration-haven-fast|duration-haven|duration-haven-slow|duration-haven-ritual)\s*:\s*([^;]+);/g;
  while ((m = themeVarRe.exec(themeBlock)) !== null) {
    const v = m[2].trim();
    if (!v.startsWith('var(')) tokens[m[1]] = v;
  }
}

// Build structured output (W3C-style + Haven groups)
const colorKeys = [
  'background', 'foreground', 'muted', 'muted-foreground', 'card', 'card-foreground',
  'popover', 'popover-foreground', 'primary', 'primary-foreground', 'secondary', 'secondary-foreground',
  'accent', 'accent-foreground', 'destructive', 'destructive-foreground',
  'border', 'input', 'ring', 'chart-1', 'chart-2', 'chart-3', 'chart-4', 'chart-5',
  'sidebar', 'sidebar-foreground', 'sidebar-primary', 'sidebar-primary-foreground',
  'sidebar-accent', 'sidebar-accent-foreground', 'sidebar-border', 'sidebar-ring',
];
const radiusKeys = ['radius', 'radius-card', 'radius-button', 'radius-input'];
const spaceKeys = ['space-page', 'space-section', 'space-block'];
const shadowKeys = ['shadow-soft', 'shadow-lift', 'shadow-modal', 'shadow-card', 'shadow-card-hover'];
const textKeys = ['text-display', 'text-title', 'text-body', 'text-caption'];

const color = {};
colorKeys.forEach((k) => { if (tokens[k] !== undefined) color[k] = tokens[k]; });
const radius = {};
radiusKeys.forEach((k) => { if (tokens[k] !== undefined) radius[k.replace('radius-', '')] = tokens[k]; });
if (tokens.radius !== undefined) radius.base = tokens.radius;
const spacing = {};
spaceKeys.forEach((k) => { if (tokens[k] !== undefined) spacing[k.replace('space-', '')] = tokens[k]; });
const shadow = {};
shadowKeys.forEach((k) => { if (tokens[k] !== undefined) shadow[k.replace('shadow-', '')] = tokens[k]; });
const typography = {};
textKeys.forEach((k) => { if (tokens[k] !== undefined) typography[k.replace('text-', '')] = tokens[k]; });
const motion = { ease: {}, duration: {} };
if (tokens['ease-haven']) motion.ease.haven = tokens['ease-haven'];
if (tokens['ease-haven-spring']) motion.ease['haven-spring'] = tokens['ease-haven-spring'];
if (tokens['duration-haven-fast']) motion.duration['haven-fast'] = tokens['duration-haven-fast'];
if (tokens['duration-haven']) motion.duration.haven = tokens['duration-haven'];
if (tokens['duration-haven-slow']) motion.duration['haven-slow'] = tokens['duration-haven-slow'];
if (tokens['duration-haven-ritual']) motion.duration['haven-ritual'] = tokens['duration-haven-ritual'];

const output = {
  $schema: 'https://design-tokens.github.io/community-group/format/',
  description: 'Haven design tokens — generated from globals.css. Single source of truth: frontend/src/app/globals.css.',
  color,
  radius,
  spacing,
  shadow,
  typography,
  motion,
  font: {
    mono: tokens['font-mono'],
    comment: 'font-sans and font-art are set by next/font on <html>.',
  },
};

fs.writeFileSync(outPath, JSON.stringify(output, null, 2) + '\n', 'utf8');
console.log('Generated', outPath);
