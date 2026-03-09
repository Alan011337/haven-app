import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createHash } from 'crypto';

// 設定 __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 1. 載入環境變數
dotenv.config({ path: '.env.local' });

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

const UUID_V4_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const args = new Set(process.argv.slice(2));
const isValidateOnly = args.has('--validate-only');
const isDryRun = args.has('--dry-run');
const isStrict = args.has('--strict');
const shouldWriteReportJson = args.has('--write-report-json');
const shouldWriteCleanJson = args.has('--write-clean-json');
const minCardsPerCategory = Number(process.env.SEED_MIN_PER_CATEGORY ?? 100);

const REPORT_DIR = path.join(__dirname, 'data', 'reports');
const REPORT_JSON_PATH = path.join(REPORT_DIR, 'seed-validation-report.json');
const CLEAN_JSON_PATH = path.join(REPORT_DIR, 'cards.cleaned.json');

type CardData = {
  category: string;
  title: string;
  description: string;
  question: string;
  difficulty_level: number;
  depth_level?: number;
  tags: string[];
  is_ai_generated: boolean;
  id: string;
  created_at: string;
  deck_id?: number;
};

type DeckRow = {
  id: number;
  name: string;
};

type PreparedCard = {
  id: string;
  deck_id?: number;
  category: string;
  title: string;
  description: string;
  question: string;
  difficulty_level: number;
  depth_level: number;
  tags: string[];
  is_ai_generated: boolean;
  created_at: string;
};

type PrepareResult = {
  cards: PreparedCard[];
  skippedInvalid: number;
  regeneratedIds: number;
  dedupedById: number;
  dedupedByQuestion: number;
  warningMessages: string[];
  duplicateQuestionRows: DuplicateQuestionRow[];
  invalidRows: InvalidRow[];
};

type UploadCard = PreparedCard & {
  deck_id: number;
};

type DuplicateQuestionRow = {
  category: string;
  question: string;
  first_title: string;
  first_id: string;
  duplicate_title: string;
  duplicate_id: string;
};

type InvalidRow = {
  reason: string;
  category: string;
  title: string;
  id: string;
};

function normalizeText(value: unknown): string {
  if (typeof value !== 'string') return '';
  return value.trim();
}

function normalizeQuestionKey(category: string, question: string): string {
  return `${category}::${question.replace(/\s+/g, ' ').trim().toLowerCase()}`;
}

function deterministicUuidV4(seed: string): string {
  const digest = createHash('sha256').update(seed).digest();
  const bytes = Array.from(digest.subarray(0, 16));

  // Force UUID v4 + RFC4122 variant bits
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  const hex = bytes.map((value) => value.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20, 32)}`;
}

function buildStableUuid(seed: string, existingIds: Map<string, PreparedCard>): string {
  let suffix = 0;
  while (suffix < 10000) {
    const value = suffix === 0 ? deterministicUuidV4(seed) : deterministicUuidV4(`${seed}::${suffix}`);
    if (!existingIds.has(value)) {
      return value;
    }
    suffix += 1;
  }
  throw new Error(`無法為 seed 產生唯一 UUID：${seed}`);
}

function normalizeDifficulty(value: unknown): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed)) return 1;
  if (parsed < 1) return 1;
  if (parsed > 3) return 3;
  return parsed;
}

function normalizeDepth(value: unknown): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed)) return 1;
  if (parsed < 1) return 1;
  if (parsed > 3) return 3;
  return parsed;
}

function normalizeTags(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  const tags: string[] = [];
  for (const rawTag of value) {
    const tag = normalizeText(rawTag);
    if (!tag) continue;
    if (seen.has(tag)) continue;
    seen.add(tag);
    tags.push(tag);
  }
  return tags;
}

function getCategoryCounts(cards: PreparedCard[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const card of cards) {
    counts.set(card.category, (counts.get(card.category) ?? 0) + 1);
  }
  return counts;
}

function toCountObject(counts: Map<string, number>): Record<string, number> {
  const result: Record<string, number> = {};
  for (const category of VALID_CATEGORIES) {
    result[category] = counts.get(category) ?? 0;
  }
  return result;
}

function writeJsonFile(filePath: string, data: unknown): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, 'utf-8');
}

function prepareCards(rawCards: CardData[]): PrepareResult {
  const warningMessages: string[] = [];
  const duplicateQuestionRows: DuplicateQuestionRow[] = [];
  const invalidRows: InvalidRow[] = [];
  const prepared: PreparedCard[] = [];
  const seenIds = new Map<string, PreparedCard>();
  const seenQuestionMap = new Map<string, { id: string; title: string; question: string; category: string }>();

  let skippedInvalid = 0;
  let regeneratedIds = 0;
  let dedupedById = 0;
  let dedupedByQuestion = 0;

  for (const rawCard of rawCards) {
    const category = normalizeText(rawCard.category).toUpperCase();
    const title = normalizeText(rawCard.title);
    const description = normalizeText(rawCard.description);
    const question = normalizeText(rawCard.question);
    const created_at = normalizeText(rawCard.created_at);
    const rawId = normalizeText(rawCard.id);

    if (!VALID_CATEGORIES.has(category)) {
      const warning = `無效 category，略過：${rawCard.category ?? '(empty)'}`;
      warningMessages.push(warning);
      invalidRows.push({
        reason: warning,
        category,
        title,
        id: rawId,
      });
      skippedInvalid += 1;
      continue;
    }
    if (!title || !description || !question || !created_at) {
      const warning = `缺少必要欄位，略過：${title || '(untitled)'} / ${category}`;
      warningMessages.push(warning);
      invalidRows.push({
        reason: warning,
        category,
        title,
        id: rawId,
      });
      skippedInvalid += 1;
      continue;
    }

    const questionKey = normalizeQuestionKey(category, question);
    const seenQuestion = seenQuestionMap.get(questionKey);
    if (seenQuestion) {
      dedupedByQuestion += 1;
      duplicateQuestionRows.push({
        category,
        question,
        first_title: seenQuestion.title,
        first_id: seenQuestion.id,
        duplicate_title: title,
        duplicate_id: rawId,
      });
      continue;
    }

    let nextId = rawId;
    if (!UUID_V4_REGEX.test(nextId)) {
      const replacementId = buildStableUuid(
        `invalid-id:${category}:${title}:${question}:${created_at}`,
        seenIds,
      );
      warningMessages.push(`非 UUID v4，已重建 ID：${nextId || '(empty)'} -> ${replacementId}`);
      nextId = replacementId;
      regeneratedIds += 1;
    }

    const nextCard: PreparedCard = {
      id: nextId,
      deck_id: rawCard.deck_id,
      category,
      title,
      description,
      question,
      difficulty_level: normalizeDifficulty(rawCard.difficulty_level),
      depth_level: normalizeDepth(rawCard.depth_level),
      tags: normalizeTags(rawCard.tags),
      is_ai_generated: Boolean(rawCard.is_ai_generated),
      created_at,
    };

    if (seenIds.has(nextCard.id)) {
      const existingCard = seenIds.get(nextCard.id)!;
      if (
        existingCard.title !== nextCard.title ||
        existingCard.question !== nextCard.question ||
        existingCard.category !== nextCard.category
      ) {
        const replacementId = buildStableUuid(
          `id-collision:${nextCard.id}:${nextCard.category}:${nextCard.title}:${nextCard.question}`,
          seenIds,
        );
        warningMessages.push(`ID 衝突但內容不同，已重建 ID：${nextCard.id} -> ${replacementId}`);
        nextCard.id = replacementId;
        regeneratedIds += 1;
      } else {
        dedupedById += 1;
        continue;
      }
    }

    seenQuestionMap.set(questionKey, {
      id: nextCard.id,
      title: nextCard.title,
      question: nextCard.question,
      category: nextCard.category,
    });
    seenIds.set(nextCard.id, nextCard);
    prepared.push(nextCard);
  }

  return {
    cards: prepared,
    skippedInvalid,
    regeneratedIds,
    dedupedById,
    dedupedByQuestion,
    warningMessages,
    duplicateQuestionRows,
    invalidRows,
  };
}

function printCategoryCounts(counts: Map<string, number>): void {
  console.log('📚 每個牌組題數：');
  for (const category of VALID_CATEGORIES) {
    const value = counts.get(category) ?? 0;
    const marker = value >= minCardsPerCategory ? '✅' : '⚠️';
    console.log(`   ${marker} ${category}: ${value}`);
  }
}

function assertQualityGate(cards: PreparedCard[], warningMessages: string[]): {
  counts: Map<string, number>;
  insufficientCategories: string[];
} {
  const counts = getCategoryCounts(cards);
  printCategoryCounts(counts);

  const insufficientCategories = [...VALID_CATEGORIES].filter(
    (category) => (counts.get(category) ?? 0) < minCardsPerCategory,
  );

  if (insufficientCategories.length > 0) {
    console.error(
      `❌ 品質門檻未通過：以下牌組低於 ${minCardsPerCategory} 題：${insufficientCategories.join(', ')}`,
    );
    process.exit(1);
  }

  if (isStrict && warningMessages.length > 0) {
    console.error(`❌ strict 模式啟用：存在 ${warningMessages.length} 個警告，停止執行。`);
    process.exit(1);
  }

  return {
    counts,
    insufficientCategories,
  };
}

async function createSupabaseClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !supabaseServiceKey) {
    console.error('❌ 缺少環境變數：請確認 .env.local 中有 NEXT_PUBLIC_SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY');
    process.exit(1);
  }

  return createClient(supabaseUrl, supabaseServiceKey);
}

async function seedCards() {
  const modeLabel = isValidateOnly ? 'Validate-Only' : isDryRun ? 'Dry-Run' : 'Seeding';
  console.log(`🌱 開始執行卡片資料流程 (${modeLabel})...`);

  const dataPath = path.join(__dirname, 'data', 'cards.json');
  
  if (!fs.existsSync(dataPath)) {
    console.error(`❌ 找不到資料檔：${dataPath}`);
    return;
  }

  const fileContent = fs.readFileSync(dataPath, 'utf-8');
  const rawCards: CardData[] = JSON.parse(fileContent);
  
  console.log(`📦 讀取到 ${rawCards.length} 張卡片資料，準備處理...`);

  const prepareResult = prepareCards(rawCards);
  const {
    cards: normalizedCards,
    warningMessages,
    duplicateQuestionRows,
    invalidRows,
  } = prepareResult;

  console.log('📊 資料整理報告：');
  console.log(`   - 原始數量：${rawCards.length}`);
  console.log(`   - 無效資料略過：${prepareResult.skippedInvalid}`);
  console.log(`   - 問題重複略過（同分類同題）：${prepareResult.dedupedByQuestion}`);
  console.log(`   - ID 重複略過（內容相同）：${prepareResult.dedupedById}`);
  console.log(`   - ID 重建次數：${prepareResult.regeneratedIds}`);
  console.log(`   - 最終可用數量：${normalizedCards.length}`);

  if (warningMessages.length > 0) {
    console.log(`⚠️ 資料警告共 ${warningMessages.length} 筆（顯示前 15 筆）：`);
    for (const message of warningMessages.slice(0, 15)) {
      console.log(`   - ${message}`);
    }
    if (warningMessages.length > 15) {
      console.log(`   - ...其餘 ${warningMessages.length - 15} 筆省略`);
    }
  }

  if (normalizedCards.length === 0) {
    console.log('⚠️ 沒有有效的卡片可以匯入。');
    return;
  }

  const qualityGate = assertQualityGate(normalizedCards, warningMessages);
  const reportBase = {
    generated_at: new Date().toISOString(),
    mode: modeLabel,
    source_file: dataPath,
    summary: {
      raw_cards: rawCards.length,
      normalized_cards: normalizedCards.length,
      skipped_invalid: prepareResult.skippedInvalid,
      deduped_by_question: prepareResult.dedupedByQuestion,
      deduped_by_id: prepareResult.dedupedById,
      regenerated_ids: prepareResult.regeneratedIds,
      warnings_count: warningMessages.length,
      invalid_rows_count: invalidRows.length,
      duplicate_question_rows_count: duplicateQuestionRows.length,
      min_cards_per_category: minCardsPerCategory,
    },
    category_counts: toCountObject(qualityGate.counts),
    insufficient_categories: qualityGate.insufficientCategories,
    warning_messages_sample: warningMessages.slice(0, 50),
    invalid_rows: invalidRows.slice(0, 200),
    duplicate_question_rows: duplicateQuestionRows,
  };
  let report: Record<string, unknown> = reportBase;

  if (shouldWriteCleanJson) {
    writeJsonFile(CLEAN_JSON_PATH, normalizedCards);
    console.log(`🧹 已輸出清洗後資料：${CLEAN_JSON_PATH}`);
  }

  if (isValidateOnly) {
    if (shouldWriteReportJson) {
      writeJsonFile(REPORT_JSON_PATH, report);
      console.log(`📝 已輸出驗證報告：${REPORT_JSON_PATH}`);
    }
    console.log('✅ validate-only 完成，未寫入資料庫。');
    return;
  }

  const supabase = await createSupabaseClient();

  // 3. 獲取所有牌組，填 deck_id
  const { data: decks, error: deckError } = await supabase
    .from('card_decks')
    .select('id, name')
    .returns<DeckRow[]>();

  if (deckError || !decks) {
    console.error('❌ 無法讀取 card_decks:', deckError);
    return;
  }
  const deckMap = new Map(decks.map((d) => [d.name, d.id]));
  const missingDeckMappingRows: InvalidRow[] = [];

  const uploadCards: UploadCard[] = normalizedCards
    .map((card) => {
      const mappedDeckId = deckMap.get(card.category);
      if (!mappedDeckId) {
        console.warn(`⚠️ 資料庫缺少對應牌組：${card.category}，略過卡片：${card.title}`);
        missingDeckMappingRows.push({
          reason: 'missing deck mapping in database',
          category: card.category,
          title: card.title,
          id: card.id,
        });
        return null;
      }
      return {
        ...card,
        deck_id: mappedDeckId,
      };
    })
    .filter((item): item is UploadCard => item !== null);

  report = {
    ...report,
    mapping_summary: {
      deck_rows_in_db: decks.length,
      mapped_cards: uploadCards.length,
      missing_mapping_rows_count: missingDeckMappingRows.length,
    },
    missing_mapping_rows: missingDeckMappingRows.slice(0, 200),
  };

  if (uploadCards.length === 0) {
    if (shouldWriteReportJson) {
      writeJsonFile(REPORT_JSON_PATH, report);
      console.log(`📝 已輸出驗證報告：${REPORT_JSON_PATH}`);
    }
    console.log('⚠️ 找不到可寫入的卡片（deck mapping 全數失敗）。');
    return;
  }

  if (isDryRun) {
    if (shouldWriteReportJson) {
      writeJsonFile(REPORT_JSON_PATH, report);
      console.log(`📝 已輸出驗證報告：${REPORT_JSON_PATH}`);
    }
    console.log(`✅ dry-run 完成，預計可寫入 ${uploadCards.length} 張，未執行 upsert。`);
    return;
  }

  // 5. 寫入資料庫
  const BATCH_SIZE = 100;
  for (let i = 0; i < uploadCards.length; i += BATCH_SIZE) {
    const batch = uploadCards.slice(i, i + BATCH_SIZE);
    
    const { error: insertError } = await supabase
      .from('cards')
      .upsert(batch, { onConflict: 'id' });

    if (insertError) {
      console.error(`❌ 第 ${i / BATCH_SIZE + 1} 批次匯入失敗:`, insertError);
    } else {
      process.stdout.write('.'); // 進度條效果
    }
  }

  if (shouldWriteReportJson) {
    writeJsonFile(REPORT_JSON_PATH, report);
    console.log(`📝 已輸出驗證報告：${REPORT_JSON_PATH}`);
  }
  console.log(`\n✅ 全部處理完成！成功匯入/更新 ${uploadCards.length} 張卡片！`);
}

seedCards();
