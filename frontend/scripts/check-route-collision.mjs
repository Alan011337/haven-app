#!/usr/bin/env node

import { readdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const ROOT = process.cwd();
const APP_DIR = path.join(ROOT, "src", "app");
const SUPPORTED_EXTENSIONS = new Set([".js", ".jsx", ".ts", ".tsx", ".mdx"]);
const NEXT_ROUTE_FILE_NAMES = new Set([
  "page",
  "layout",
  "template",
  "error",
  "loading",
  "not-found",
  "default",
  "route",
]);

async function walk(dirPath) {
  const entries = await readdir(dirPath, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await walk(fullPath)));
      continue;
    }
    if (entry.isFile()) {
      files.push(fullPath);
    }
  }
  return files;
}

function buildCollisionMap(files) {
  const map = new Map();
  for (const filePath of files) {
    const extension = path.extname(filePath).toLowerCase();
    if (!SUPPORTED_EXTENSIONS.has(extension)) {
      continue;
    }
    const baseName = path.basename(filePath, extension);
    if (!NEXT_ROUTE_FILE_NAMES.has(baseName)) {
      continue;
    }
    const directory = path.relative(APP_DIR, path.dirname(filePath)) || ".";
    const key = `${directory}/${baseName}`;
    const record = map.get(key) ?? [];
    record.push(path.basename(filePath));
    map.set(key, record);
  }
  return map;
}

function formatCollisionLabel(collisionKey, fileNames) {
  return `${collisionKey} => ${fileNames.sort().join(", ")}`;
}

async function main() {
  try {
    const files = await walk(APP_DIR);
    const routeFiles = buildCollisionMap(files);
    const collisions = [];

    for (const [routeKey, fileNames] of routeFiles.entries()) {
      if (fileNames.length > 1) {
        collisions.push(formatCollisionLabel(routeKey, fileNames));
      }
    }

    if (collisions.length > 0) {
      console.error("[route-collision-guard] fail: duplicate Next.js app route files found.");
      for (const item of collisions.sort()) {
        console.error(`  - ${item}`);
      }
      process.exit(1);
    }

    console.log("[route-collision-guard] ok: no duplicate app route files detected.");
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("[route-collision-guard] fail: unable to scan app routes.");
    console.error(`  reason: ${message}`);
    process.exit(1);
  }
}

await main();
