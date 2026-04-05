const DAILY_VIBE_CATEGORY = 'DAILY_VIBE';
const MEDIUM_DEEP_THRESHOLD = 2;
const PLACEHOLDER_TITLE_PATTERN = /^日常共感 #\d+$/u;

export const DAILY_VIBE_DEPTH_2_WARN_MIN = 35;
export const DAILY_VIBE_DEPTH_3_WARN_MIN = 7;

function normalizeCategory(value) {
  return String(value || '').trim().toUpperCase();
}

function normalizeDepth(value) {
  const depth = Number(value ?? 1);
  if (!Number.isInteger(depth) || depth < 1 || depth > 3) return 1;
  return depth;
}

function normalizeTitle(value) {
  return String(value || '').trim();
}

function toDailyVibeCards(cards) {
  return cards.filter((card) => normalizeCategory(card.category) === DAILY_VIBE_CATEGORY);
}

function sortSignals(left, right) {
  return right.count - left.count || left.title.localeCompare(right.title, 'zh-Hant');
}

function roundRatio(value) {
  return Number(value.toFixed(4));
}

export function collectDailyVibeDepthHealth(cards) {
  const dailyCards = toDailyVibeCards(cards);
  const totalCards = dailyCards.length;
  const depthCounts = { 1: 0, 2: 0, 3: 0 };

  for (const card of dailyCards) {
    depthCounts[normalizeDepth(card.depth_level)] += 1;
  }

  const depthRatios = {
    1: totalCards > 0 ? roundRatio(depthCounts[1] / totalCards) : 0,
    2: totalCards > 0 ? roundRatio(depthCounts[2] / totalCards) : 0,
    3: totalCards > 0 ? roundRatio(depthCounts[3] / totalCards) : 0,
  };

  const floorWarnings = [];
  if (depthCounts[2] < DAILY_VIBE_DEPTH_2_WARN_MIN) {
    floorWarnings.push(
      `depth 2 support below guard floor: ${depthCounts[2]} < ${DAILY_VIBE_DEPTH_2_WARN_MIN}`,
    );
  }
  if (depthCounts[3] < DAILY_VIBE_DEPTH_3_WARN_MIN) {
    floorWarnings.push(
      `depth 3 support below guard floor: ${depthCounts[3]} < ${DAILY_VIBE_DEPTH_3_WARN_MIN}`,
    );
  }

  return {
    total_cards: totalCards,
    depth_counts: depthCounts,
    depth_ratios: depthRatios,
    depth_2_warn_min: DAILY_VIBE_DEPTH_2_WARN_MIN,
    depth_3_warn_min: DAILY_VIBE_DEPTH_3_WARN_MIN,
    floor_warnings: floorWarnings,
  };
}

export function collectDailyVibeDuplicateTitleSignals(cards) {
  const titleMap = new Map();

  for (const card of toDailyVibeCards(cards)) {
    const title = normalizeTitle(card.title);
    if (!title) continue;
    if (!titleMap.has(title)) {
      titleMap.set(title, []);
    }
    titleMap.get(title).push({
      depth: normalizeDepth(card.depth_level),
      question: normalizeTitle(card.question),
    });
  }

  const duplicateSignals = [...titleMap.entries()]
    .filter(([, rows]) => rows.length > 1)
    .map(([title, rows]) => ({
      title,
      count: rows.length,
      depths: [...new Set(rows.map((row) => row.depth))].sort((a, b) => a - b),
      sample_questions: rows.slice(0, 3).map((row) => row.question),
    }));

  return {
    cross_depth_duplicate_titles: duplicateSignals
      .filter((signal) => signal.depths.length > 1)
      .sort(sortSignals),
    medium_deep_duplicate_titles: duplicateSignals
      .filter((signal) => signal.depths.some((depth) => depth >= MEDIUM_DEEP_THRESHOLD))
      .sort(sortSignals),
  };
}

export function collectDailyVibePlaceholderSignals(cards) {
  return {
    medium_deep_placeholder_titles: toDailyVibeCards(cards)
      .filter((card) => {
        const title = normalizeTitle(card.title);
        return PLACEHOLDER_TITLE_PATTERN.test(title) && normalizeDepth(card.depth_level) >= MEDIUM_DEEP_THRESHOLD;
      })
      .map((card) => ({
        title: normalizeTitle(card.title),
        depth: normalizeDepth(card.depth_level),
        question: normalizeTitle(card.question),
      })),
  };
}

export function buildDailyVibeQualityReport(cards) {
  const depthHealth = collectDailyVibeDepthHealth(cards);
  const duplicateSignals = collectDailyVibeDuplicateTitleSignals(cards);
  const placeholderSignals = collectDailyVibePlaceholderSignals(cards);

  const warnings = [...depthHealth.floor_warnings];
  if (duplicateSignals.cross_depth_duplicate_titles.length > 0) {
    warnings.push(
      `${duplicateSignals.cross_depth_duplicate_titles.length} cross-depth duplicate titles detected`,
    );
  }
  if (duplicateSignals.medium_deep_duplicate_titles.length > 0) {
    warnings.push(
      `${duplicateSignals.medium_deep_duplicate_titles.length} medium/deep duplicate titles detected`,
    );
  }
  if (placeholderSignals.medium_deep_placeholder_titles.length > 0) {
    warnings.push(
      `${placeholderSignals.medium_deep_placeholder_titles.length} medium/deep placeholder titles detected`,
    );
  }

  return {
    summary: {
      total_cards: depthHealth.total_cards,
      medium_deep_card_count: depthHealth.depth_counts[2] + depthHealth.depth_counts[3],
      cross_depth_duplicate_titles_count: duplicateSignals.cross_depth_duplicate_titles.length,
      medium_deep_duplicate_titles_count: duplicateSignals.medium_deep_duplicate_titles.length,
      medium_deep_placeholder_titles_count: placeholderSignals.medium_deep_placeholder_titles.length,
      warning_count: warnings.length,
    },
    ...depthHealth,
    ...duplicateSignals,
    ...placeholderSignals,
    warnings,
  };
}
