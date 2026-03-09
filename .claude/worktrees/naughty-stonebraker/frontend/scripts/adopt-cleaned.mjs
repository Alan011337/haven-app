import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const args = new Set(process.argv.slice(2));
const skipBackup = args.has('--skip-backup');

const VALID_CATEGORIES = new Set([
  'DAILY_VIBE',
  'SOUL_DIVE',
  'SAFE_ZONE',
  'MEMORY_LANE',
  'GROWTH_QUEST',
  'AFTER_DARK',
  'CO_PILOT',
  'LOVE_BLUEPRINT',
]);

const MIN_PER_CATEGORY = Number(process.env.SEED_MIN_PER_CATEGORY ?? 100);
const SOURCE_PATH = path.join(__dirname, 'data', 'reports', 'cards.cleaned.json');
const TARGET_PATH = path.join(__dirname, 'data', 'cards.json');
const BACKUP_DIR = path.join(__dirname, 'data', 'backups');

function readJson(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`找不到檔案：${filePath}`);
  }
  const text = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(text);
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf-8');
}

function digestSha256(filePath) {
  const hash = crypto.createHash('sha256');
  hash.update(fs.readFileSync(filePath));
  return hash.digest('hex');
}

function assertCleanData(cards) {
  if (!Array.isArray(cards) || cards.length === 0) {
    throw new Error('cards.cleaned.json 不是有效陣列或內容為空。');
  }

  const errors = [];
  const counts = new Map();
  const seenQuestion = new Set();

  for (let i = 0; i < cards.length; i += 1) {
    const item = cards[i];
    if (!item || typeof item !== 'object') {
      errors.push(`row ${i}: 不是物件`);
      continue;
    }

    const category = typeof item.category === 'string' ? item.category.trim().toUpperCase() : '';
    const title = typeof item.title === 'string' ? item.title.trim() : '';
    const question = typeof item.question === 'string' ? item.question.trim() : '';
    const id = typeof item.id === 'string' ? item.id.trim() : '';

    if (!VALID_CATEGORIES.has(category)) {
      errors.push(`row ${i}: 無效 category (${item.category ?? 'empty'})`);
      continue;
    }
    if (!id || !title || !question) {
      errors.push(`row ${i}: 缺少 id/title/question`);
      continue;
    }

    const qKey = `${category}::${question.replace(/\s+/g, ' ').toLowerCase()}`;
    if (seenQuestion.has(qKey)) {
      errors.push(`row ${i}: 同分類重複題目 (${category})`);
      continue;
    }
    seenQuestion.add(qKey);
    counts.set(category, (counts.get(category) ?? 0) + 1);
  }

  for (const category of VALID_CATEGORIES) {
    const count = counts.get(category) ?? 0;
    if (count < MIN_PER_CATEGORY) {
      errors.push(`category ${category}: 只有 ${count} 題，低於門檻 ${MIN_PER_CATEGORY}`);
    }
  }

  if (errors.length > 0) {
    const preview = errors.slice(0, 12).join('\n- ');
    const suffix = errors.length > 12 ? `\n...其餘 ${errors.length - 12} 筆` : '';
    throw new Error(`清洗資料驗證失敗：\n- ${preview}${suffix}`);
  }

  return counts;
}

function backupTargetIfNeeded() {
  if (skipBackup) {
    console.log('ℹ️ 已使用 --skip-backup，略過備份。');
    return null;
  }

  if (!fs.existsSync(TARGET_PATH)) {
    console.log('ℹ️ 目前沒有既有 cards.json，略過備份。');
    return null;
  }

  fs.mkdirSync(BACKUP_DIR, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backupPath = path.join(BACKUP_DIR, `cards.${timestamp}.json`);
  fs.copyFileSync(TARGET_PATH, backupPath);
  console.log(`🗂️ 已建立備份：${backupPath}`);
  return backupPath;
}

function printCounts(counts) {
  console.log('📚 採納後牌組題數：');
  for (const category of VALID_CATEGORIES) {
    console.log(`   - ${category}: ${counts.get(category) ?? 0}`);
  }
}

function main() {
  console.log('🔄 開始採納 cleaned 資料為正式 cards.json ...');
  const cards = readJson(SOURCE_PATH);
  const counts = assertCleanData(cards);
  const backupPath = backupTargetIfNeeded();

  const beforeHash = fs.existsSync(TARGET_PATH) ? digestSha256(TARGET_PATH) : null;
  writeJson(TARGET_PATH, cards);
  const afterHash = digestSha256(TARGET_PATH);

  printCounts(counts);
  console.log(`✅ 已更新：${TARGET_PATH}`);
  if (backupPath) {
    console.log(`↩️ 可回滾檔案：${backupPath}`);
  }
  if (beforeHash) {
    console.log(`🔍 SHA256 (before): ${beforeHash}`);
  }
  console.log(`🔍 SHA256 (after):  ${afterHash}`);
}

try {
  main();
} catch (error) {
  console.error(`❌ adopt-cleaned 失敗：${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
