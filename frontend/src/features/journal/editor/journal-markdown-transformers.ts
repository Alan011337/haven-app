'use client';

import {
  $convertFromMarkdownString,
  $convertToMarkdownString,
  TRANSFORMERS,
  type ElementTransformer,
  type Transformer,
} from '@lexical/markdown';
import { $createParagraphNode, $createTextNode, $getRoot, type LexicalEditor } from 'lexical';
import {
  $createJournalImageNode,
  $isJournalImageNode,
  JournalImageNode,
} from '@/features/journal/editor/JournalImageNode';

const IMAGE_REG_EXP = /^!\[([^\]]*)\]\((.+)\)$/;

export const JOURNAL_IMAGE_TRANSFORMER: ElementTransformer = {
  dependencies: [JournalImageNode],
  export: (node) => {
    if (!$isJournalImageNode(node)) return null;
    return `![${node.getAltText()}](${node.getSrc()})`;
  },
  regExp: IMAGE_REG_EXP,
  replace: (parentNode, _children, match) => {
    parentNode.replace(
      $createJournalImageNode({
        alt: match[1] ?? '',
        src: match[2] ?? '',
      }),
    );
  },
  type: 'element',
};

export const JOURNAL_MARKDOWN_TRANSFORMERS: Array<Transformer> = [
  JOURNAL_IMAGE_TRANSFORMER,
  ...TRANSFORMERS,
];

export function normalizeJournalMarkdown(markdown: string): string {
  return markdown.replace(/\r\n/g, '\n').trim();
}

export function importJournalMarkdown(
  editor: LexicalEditor,
  markdown: string,
): { failed: boolean; warning: string | null } {
  const normalized = normalizeJournalMarkdown(markdown);

  try {
    editor.update(() => {
      const root = $getRoot();
      root.clear();
      if (!normalized) {
        root.append($createParagraphNode());
        return;
      }
      $convertFromMarkdownString(normalized, JOURNAL_MARKDOWN_TRANSFORMERS);
      if (root.getChildrenSize() === 0) {
        root.append($createParagraphNode());
      }
    });
    return { failed: false, warning: null };
  } catch {
    editor.update(() => {
      const root = $getRoot();
      root.clear();
      const paragraph = $createParagraphNode();
      paragraph.append($createTextNode(normalized));
      root.append(paragraph);
    });
    return {
      failed: true,
      warning: '這篇原稿的 Markdown 沒有完整轉進編輯器，Haven 先用純文字把內容帶回來。',
    };
  }
}

export function exportJournalMarkdown(editor: LexicalEditor): string {
  return editor.getEditorState().read(() => {
    return $convertToMarkdownString(JOURNAL_MARKDOWN_TRANSFORMERS).trim();
  });
}
