'use client';

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import { $createCodeNode, CodeNode } from '@lexical/code';
import { AutoFocusPlugin } from '@lexical/react/LexicalAutoFocusPlugin';
import { LexicalComposer } from '@lexical/react/LexicalComposer';
import { ContentEditable } from '@lexical/react/LexicalContentEditable';
import { LexicalErrorBoundary } from '@lexical/react/LexicalErrorBoundary';
import { HistoryPlugin } from '@lexical/react/LexicalHistoryPlugin';
import { LinkPlugin } from '@lexical/react/LexicalLinkPlugin';
import { ListPlugin } from '@lexical/react/LexicalListPlugin';
import { MarkdownShortcutPlugin } from '@lexical/react/LexicalMarkdownShortcutPlugin';
import { OnChangePlugin } from '@lexical/react/LexicalOnChangePlugin';
import { RichTextPlugin } from '@lexical/react/LexicalRichTextPlugin';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { INSERT_ORDERED_LIST_COMMAND, INSERT_UNORDERED_LIST_COMMAND, ListItemNode, ListNode } from '@lexical/list';
import { $createLinkNode, LinkNode } from '@lexical/link';
import { $createHeadingNode, $createQuoteNode, HeadingNode, QuoteNode } from '@lexical/rich-text';
import { $setBlocksType } from '@lexical/selection';
import {
  $createParagraphNode,
  $createTextNode,
  $getRoot,
  $getSelection,
  $isRangeSelection,
  COMMAND_PRIORITY_EDITOR,
  COMMAND_PRIORITY_LOW,
  FORMAT_TEXT_COMMAND,
  KEY_DOWN_COMMAND,
  type LexicalEditor,
} from 'lexical';
import { logClientError } from '@/lib/safe-error-log';
import type { JournalAttachmentPublic } from '@/types';
import { cn } from '@/lib/utils';
import { HorizontalRuleNode, INSERT_HORIZONTAL_RULE_COMMAND } from '@lexical/react/LexicalHorizontalRuleNode';
import { HorizontalRulePlugin } from '@lexical/react/LexicalHorizontalRulePlugin';
import { JournalFloatingToolbar } from '@/features/journal/editor/JournalFloatingToolbar';
import {
  $createJournalImageNode,
  INSERT_JOURNAL_IMAGE_COMMAND,
  JournalAttachmentProvider,
  JournalImageNode,
  type InsertJournalImagePayload,
} from '@/features/journal/editor/JournalImageNode';
import {
  exportJournalMarkdown,
  importJournalMarkdown,
  JOURNAL_MARKDOWN_TRANSFORMERS,
} from '@/features/journal/editor/journal-markdown-transformers';
import { JournalSlashMenu } from '@/features/journal/editor/JournalSlashMenu';
import {
  buildJournalSectionDomId,
  type JournalOutlineEntry,
} from '@/lib/journal-outline';
import { JOURNAL_RHYTHM } from '@/features/journal/journal-document-rhythm';

// Block-level rhythm is sourced from JOURNAL_RHYTHM so Lexical write mode and
// the `'read'` variant of journal-markdown stay in lock-step. Inline character
// formatting (link, bold/italic/code) is kept local — it is not part of the
// write/read continuity contract.
const editorTheme = {
  heading: {
    h1: JOURNAL_RHYTHM.h1,
    h2: JOURNAL_RHYTHM.h2,
  },
  link: 'text-primary underline decoration-primary/26 underline-offset-4 transition-colors duration-haven ease-haven hover:text-primary/80',
  list: {
    listitem: JOURNAL_RHYTHM.listItem,
    nested: {
      listitem: 'mt-2',
    },
    olDepth: ['list-decimal', 'list-decimal', 'list-decimal', 'list-decimal', 'list-decimal'],
    ol: JOURNAL_RHYTHM.ol,
    ul: JOURNAL_RHYTHM.ul,
    ulDepth: ['list-disc', 'list-disc', 'list-disc', 'list-disc', 'list-disc'],
  },
  paragraph: JOURNAL_RHYTHM.paragraph,
  quote: JOURNAL_RHYTHM.quote,
  text: {
    bold: 'font-semibold text-card-foreground',
    code: 'rounded-md bg-[rgba(72,55,36,0.08)] px-1.5 py-0.5 font-mono text-[0.95em] text-card-foreground',
    italic: 'italic text-card-foreground',
    strikethrough: 'line-through decoration-card-foreground/40',
    underline: 'underline underline-offset-4',
  },
  hr: JOURNAL_RHYTHM.hr,
};

export interface JournalLexicalComposerHandle {
  applyBlockAction: (action: JournalEditorBlockAction) => void;
  applyInlineFormat: (format: JournalEditorInlineFormat) => void;
  focus: () => void;
  getMarkdown: () => string;
  insertImage: (payload: InsertJournalImagePayload) => string;
  insertReflectionSection: (payload: JournalReflectionSectionPayload) => string;
  scrollToSection: (sectionId: string) => boolean;
}

export type JournalReflectionSectionPayload = {
  heading: string;
  prompt: string;
};

export type JournalEditorBlockAction =
  | 'bullet-list'
  | 'code-block'
  | 'divider'
  | 'heading-1'
  | 'heading-2'
  | 'link'
  | 'ordered-list'
  | 'paragraph'
  | 'quote';

export type JournalEditorInlineFormat = 'bold' | 'code' | 'italic' | 'strikethrough';

interface JournalLexicalComposerProps {
  attachments: JournalAttachmentPublic[];
  autoFocus?: boolean;
  className?: string;
  headingEntries?: JournalOutlineEntry[];
  initialMarkdown: string;
  onAttachmentCaptionChange?: (
    attachmentId: string,
    caption: string | null,
  ) => Promise<void> | void;
  onChange: (markdown: string) => void;
  onFilesDropped: (files: File[]) => void;
  onImportWarning?: (warning: string | null) => void;
  onRequestImage: () => void;
}

function insertJournalImageNode(payload: InsertJournalImagePayload) {
  const selection = $getSelection();
  const imageNode = $createJournalImageNode(payload);
  const trailingParagraph = $createParagraphNode();

  if ($isRangeSelection(selection)) {
    selection.insertNodes([imageNode, trailingParagraph]);
    trailingParagraph.selectStart();
    return;
  }

  const root = $getRoot();
  root.append(imageNode, trailingParagraph);
  trailingParagraph.selectStart();
}

function insertReflectionSectionNode(payload: JournalReflectionSectionPayload) {
  const heading = payload.heading.trim();
  const prompt = payload.prompt.trim();
  if (!heading) return;

  const root = $getRoot();
  const headingNode = $createHeadingNode('h2');
  const promptNode = $createParagraphNode();
  const trailingParagraph = $createParagraphNode();

  headingNode.append($createTextNode(heading));
  if (prompt) {
    promptNode.append($createTextNode(prompt));
    root.append(headingNode, promptNode, trailingParagraph);
  } else {
    root.append(headingNode, trailingParagraph);
  }
  trailingParagraph.selectStart();
}

function applyJournalBlockAction(editor: LexicalEditor, action: JournalEditorBlockAction) {
  if (action === 'bullet-list') {
    editor.dispatchCommand(INSERT_UNORDERED_LIST_COMMAND, undefined);
    return;
  }

  if (action === 'ordered-list') {
    editor.dispatchCommand(INSERT_ORDERED_LIST_COMMAND, undefined);
    return;
  }

  if (action === 'divider') {
    editor.dispatchCommand(INSERT_HORIZONTAL_RULE_COMMAND, undefined);
    return;
  }

  editor.update(() => {
    const selection = $getSelection();
    if (!$isRangeSelection(selection)) return;

    switch (action) {
      case 'paragraph':
        $setBlocksType(selection, () => $createParagraphNode());
        break;
      case 'heading-1':
        $setBlocksType(selection, () => $createHeadingNode('h1'));
        break;
      case 'heading-2':
        $setBlocksType(selection, () => $createHeadingNode('h2'));
        break;
      case 'quote':
        $setBlocksType(selection, () => $createQuoteNode());
        break;
      case 'code-block': {
        const topLevel = selection.anchor.getNode().getTopLevelElement();
        if (!topLevel) return;
        const codeNode = $createCodeNode();
        topLevel.replace(codeNode, true);
        codeNode.selectStart();
        break;
      }
      case 'link': {
        const topLevel = selection.anchor.getNode().getTopLevelElement();
        if (!topLevel) return;
        const paragraph = $createParagraphNode();
        const linkNode = $createLinkNode('https://example.com');
        linkNode.append($createTextNode('連結文字'));
        paragraph.append(linkNode);
        topLevel.replace(paragraph, true);
        paragraph.selectEnd();
        break;
      }
      default:
        break;
    }
  });
}

function EditorBridgePlugin({
  onReady,
}: {
  onReady: (editor: LexicalEditor) => void;
}) {
  const [editor] = useLexicalComposerContext();

  useEffect(() => {
    onReady(editor);
  }, [editor, onReady]);

  return null;
}

function InitialMarkdownPlugin({
  initialMarkdown,
  onImportWarning,
}: {
  initialMarkdown: string;
  onImportWarning?: (warning: string | null) => void;
}) {
  const [editor] = useLexicalComposerContext();
  const importedRef = useRef(false);

  useEffect(() => {
    if (importedRef.current) return;
    importedRef.current = true;
    const result = importJournalMarkdown(editor, initialMarkdown);
    onImportWarning?.(result.warning);
  }, [editor, initialMarkdown, onImportWarning]);

  return null;
}

function syncHeadingAnchors(
  editor: LexicalEditor,
  headingEntries: JournalOutlineEntry[],
) {
  const rootElement = editor.getRootElement();
  if (!rootElement) return;

  const headingElements = Array.from(
    rootElement.querySelectorAll<HTMLElement>('h1, h2'),
  );

  headingElements.forEach((element, index) => {
    const entry = headingEntries[index] ?? null;
    if (!entry) {
      element.removeAttribute('id');
      element.removeAttribute('data-journal-section-id');
      element.removeAttribute('data-journal-surface');
      element.removeAttribute('data-testid');
      element.style.scrollMarginTop = '';
      return;
    }

    element.id = buildJournalSectionDomId('write', entry.id);
    element.dataset.journalSectionId = entry.id;
    element.dataset.journalSurface = 'write';
    element.dataset.testid = `journal-write-section-${entry.id}`;
    element.style.scrollMarginTop = `${JOURNAL_RHYTHM.scrollMarginPx}px`;
  });
}

function JournalHeadingAnchorPlugin({
  headingEntries,
}: {
  headingEntries: JournalOutlineEntry[];
}) {
  const [editor] = useLexicalComposerContext();
  const syncAnchors = useCallback(() => {
    syncHeadingAnchors(editor, headingEntries);
  }, [editor, headingEntries]);

  useEffect(() => {
    syncAnchors();
    return editor.registerUpdateListener(() => {
      syncAnchors();
    });
  }, [editor, syncAnchors]);

  return null;
}

function JournalCommandPlugin({
  onRequestImage,
}: {
  onRequestImage: () => void;
}) {
  const [editor] = useLexicalComposerContext();

  useEffect(() => {
    return editor.registerCommand(
      INSERT_JOURNAL_IMAGE_COMMAND,
      (payload) => {
        editor.update(() => {
          insertJournalImageNode(payload);
        });
        return true;
      },
      COMMAND_PRIORITY_EDITOR,
    );
  }, [editor]);

  useEffect(() => {
    return editor.registerCommand(
      KEY_DOWN_COMMAND,
      (event) => {
        if (!(event.metaKey || event.ctrlKey)) return false;
        const key = event.key.toLowerCase();

        if (key === 'b') {
          event.preventDefault();
          editor.dispatchCommand(FORMAT_TEXT_COMMAND, 'bold');
          return true;
        }

        if (key === 'i') {
          event.preventDefault();
          editor.dispatchCommand(FORMAT_TEXT_COMMAND, 'italic');
          return true;
        }

        if (key === 'e') {
          event.preventDefault();
          editor.dispatchCommand(FORMAT_TEXT_COMMAND, 'code');
          return true;
        }

        if (event.altKey && key === '1') {
          event.preventDefault();
          editor.update(() => {
            $setBlocksType($getSelection(), () => $createHeadingNode('h1'));
          });
          return true;
        }

        if (event.altKey && key === '2') {
          event.preventDefault();
          editor.update(() => {
            $setBlocksType($getSelection(), () => $createHeadingNode('h2'));
          });
          return true;
        }

        if (event.shiftKey && key === '8') {
          event.preventDefault();
          editor.dispatchCommand(INSERT_UNORDERED_LIST_COMMAND, undefined);
          return true;
        }

        if (event.shiftKey && key === '7') {
          event.preventDefault();
          editor.dispatchCommand(INSERT_ORDERED_LIST_COMMAND, undefined);
          return true;
        }

        if (event.shiftKey && key === '9') {
          event.preventDefault();
          editor.update(() => {
            $setBlocksType($getSelection(), () => $createQuoteNode());
          });
          return true;
        }

        if (event.altKey && key === 'c') {
          event.preventDefault();
          editor.update(() => {
            const selection = $getSelection();
            if (!$isRangeSelection(selection)) return;
            const topLevel = selection.anchor.getNode().getTopLevelElement();
            if (!topLevel) return;
            const codeNode = $createCodeNode();
            topLevel.replace(codeNode, true);
            codeNode.selectStart();
          });
          return true;
        }

        if (event.shiftKey && key === 'u') {
          event.preventDefault();
          onRequestImage();
          return true;
        }

        return false;
      },
      COMMAND_PRIORITY_LOW,
    );
  }, [editor, onRequestImage]);

  return null;
}

const JournalLexicalComposer = forwardRef<
  JournalLexicalComposerHandle,
  JournalLexicalComposerProps
>(function JournalLexicalComposer(
  {
    attachments,
    autoFocus = false,
    className,
    headingEntries = [],
    initialMarkdown,
    onAttachmentCaptionChange,
    onChange,
    onFilesDropped,
    onImportWarning,
    onRequestImage,
  },
  ref,
) {
  const [editor, setEditor] = useState<LexicalEditor | null>(null);
  const initialConfig = useMemo(
    () => ({
      namespace: 'haven-journal-v3',
      nodes: [HeadingNode, QuoteNode, ListNode, ListItemNode, LinkNode, CodeNode, HorizontalRuleNode, JournalImageNode],
      onError: (error: Error) => {
        logClientError('journal_editor_runtime_failed', error);
        throw error;
      },
      theme: editorTheme,
    }),
    [],
  );

  useImperativeHandle(
    ref,
    () => ({
      applyBlockAction: (action) => {
        if (!editor) return;
        applyJournalBlockAction(editor, action);
        editor.focus();
      },
      applyInlineFormat: (format) => {
        if (!editor) return;
        editor.dispatchCommand(FORMAT_TEXT_COMMAND, format);
        editor.focus();
      },
      focus: () => {
        editor?.focus();
      },
      getMarkdown: () => {
        return editor ? exportJournalMarkdown(editor) : '';
      },
      insertImage: (payload) => {
        if (!editor) return '';
        let nextMarkdown = '';
        editor.update(() => {
          insertJournalImageNode(payload);
          nextMarkdown = exportJournalMarkdown(editor);
        }, { discrete: true });
        return nextMarkdown;
      },
      insertReflectionSection: (payload) => {
        if (!editor) return '';
        let nextMarkdown = '';
        editor.update(() => {
          insertReflectionSectionNode(payload);
          nextMarkdown = exportJournalMarkdown(editor);
        }, { discrete: true });
        editor.focus();
        return nextMarkdown;
      },
      scrollToSection: (sectionId) => {
        if (!editor) return false;
        const rootElement = editor.getRootElement();
        if (!rootElement) return false;
        const target = Array.from(
          rootElement.querySelectorAll<HTMLElement>('[data-journal-section-id]'),
        ).find((element) => element.dataset.journalSectionId === sectionId);
        if (!target) return false;
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return true;
      },
    }),
    [editor],
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      const files = Array.from(event.dataTransfer.files ?? []).filter((file) =>
        file.type.startsWith('image/'),
      );
      if (!files.length) return;
      event.preventDefault();
      onFilesDropped(files);
    },
    [onFilesDropped],
  );

  return (
    <JournalAttachmentProvider
      attachments={attachments}
      onCaptionChange={onAttachmentCaptionChange}
    >
      <div
        className={cn(
          'relative overflow-hidden rounded-[2rem] bg-transparent',
          className,
        )}
        onDragOver={(event) => {
          if (Array.from(event.dataTransfer.types).includes('Files')) {
            event.preventDefault();
          }
        }}
        onDrop={handleDrop}
      >
        <LexicalComposer initialConfig={initialConfig}>
          <EditorBridgePlugin onReady={setEditor} />
          <InitialMarkdownPlugin
            initialMarkdown={initialMarkdown}
            onImportWarning={onImportWarning}
          />
          <JournalHeadingAnchorPlugin headingEntries={headingEntries} />
          <HistoryPlugin />
          <ListPlugin />
          <LinkPlugin />
          <HorizontalRulePlugin />
          <MarkdownShortcutPlugin transformers={JOURNAL_MARKDOWN_TRANSFORMERS} />
          <OnChangePlugin
            onChange={(_, editorInstance) => {
              onChange(exportJournalMarkdown(editorInstance));
            }}
          />
          <JournalCommandPlugin onRequestImage={onRequestImage} />
          <JournalFloatingToolbar />
          <JournalSlashMenu onRequestImage={onRequestImage} />
          {autoFocus ? <AutoFocusPlugin /> : null}

          <div className="relative min-h-[560px]">
            <RichTextPlugin
              ErrorBoundary={LexicalErrorBoundary}
              contentEditable={
                <ContentEditable
                  aria-label="Journal writing canvas"
                  className="min-h-[560px] px-7 pb-20 pt-10 text-[1.07rem] leading-[2.02] text-card-foreground outline-none md:px-12 md:pb-24 md:pt-14 md:text-[1.08rem]"
                  spellCheck
                />
              }
              placeholder={
                <div className="pointer-events-none absolute inset-x-7 top-10 max-w-[34rem] text-[1.02rem] leading-[1.95] text-muted-foreground/52 md:inset-x-12 md:top-14">
                  <p className="font-art text-[1.55rem] leading-[1.15] text-muted-foreground/46">
                    先把今天最想留下來的一句，安靜地放進來。
                  </p>
                  <p className="mt-3">
                    先寫，再慢慢整理。你可以直接打字、用 <span className="font-medium text-muted-foreground/66">/</span> 插入段落結構，或在選取後輕輕修正文氣。
                  </p>
                </div>
              }
            />
          </div>
        </LexicalComposer>
      </div>
    </JournalAttachmentProvider>
  );
});

export default JournalLexicalComposer;
