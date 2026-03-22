'use client';

import type { CSSProperties, ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { $createCodeNode } from '@lexical/code';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { $createLinkNode } from '@lexical/link';
import {
  INSERT_ORDERED_LIST_COMMAND,
  INSERT_UNORDERED_LIST_COMMAND,
} from '@lexical/list';
import { $createHeadingNode, $createQuoteNode } from '@lexical/rich-text';
import { $setBlocksType } from '@lexical/selection';
import {
  $createParagraphNode,
  $createTextNode,
  $getSelection,
  $isParagraphNode,
  $isRangeSelection,
  COMMAND_PRIORITY_LOW,
  KEY_DOWN_COMMAND,
} from 'lexical';
import {
  Code2,
  Heading1,
  Heading2,
  ImagePlus,
  Link2,
  List,
  ListOrdered,
  Pilcrow,
  Quote,
} from 'lucide-react';

type SlashActionId =
  | 'paragraph'
  | 'heading-1'
  | 'heading-2'
  | 'bullet-list'
  | 'ordered-list'
  | 'quote'
  | 'code-block'
  | 'link'
  | 'image';

interface SlashAction {
  aliases: string[];
  description: string;
  icon: ReactNode;
  id: SlashActionId;
  label: string;
}

const MENU_WIDTH = 292;
const MENU_GAP_PX = 10;
const MENU_MAX_HEIGHT_PX = 360;
const VIEWPORT_MARGIN_PX = 16;

const ACTIONS: SlashAction[] = [
  {
    id: 'paragraph',
    label: '一般段落',
    description: '回到最自然的長文段落。',
    aliases: ['text', 'paragraph', 'para'],
    icon: <Pilcrow className="h-4 w-4" aria-hidden />,
  },
  {
    id: 'heading-1',
    label: '主標題',
    description: '建立大的章節節奏。',
    aliases: ['h1', 'heading', 'title'],
    icon: <Heading1 className="h-4 w-4" aria-hidden />,
  },
  {
    id: 'heading-2',
    label: '小節標題',
    description: '把長文切成清楚小節。',
    aliases: ['h2', 'section'],
    icon: <Heading2 className="h-4 w-4" aria-hidden />,
  },
  {
    id: 'bullet-list',
    label: '項目清單',
    description: '列出幾個想被看見的重點。',
    aliases: ['list', 'bullet', 'ul'],
    icon: <List className="h-4 w-4" aria-hidden />,
  },
  {
    id: 'ordered-list',
    label: '編號清單',
    description: '整理步驟、順序或脈絡。',
    aliases: ['ordered', 'number', 'ol'],
    icon: <ListOrdered className="h-4 w-4" aria-hidden />,
  },
  {
    id: 'quote',
    label: '引用',
    description: '留下那句最想被聽懂的話。',
    aliases: ['quote', 'blockquote'],
    icon: <Quote className="h-4 w-4" aria-hidden />,
  },
  {
    id: 'code-block',
    label: '程式碼區塊',
    description: '貼進片段、格式或範例。',
    aliases: ['code', 'fence'],
    icon: <Code2 className="h-4 w-4" aria-hidden />,
  },
  {
    id: 'link',
    label: '連結',
    description: '插入一個可點開的參照。',
    aliases: ['link', 'url'],
    icon: <Link2 className="h-4 w-4" aria-hidden />,
  },
  {
    id: 'image',
    label: '圖片',
    description: '把圖片放進寫作版面。',
    aliases: ['image', 'photo', 'img'],
    icon: <ImagePlus className="h-4 w-4" aria-hidden />,
  },
];

function normalizeSlashQuery(text: string): string | null {
  const trimmed = text.trim();
  const match = trimmed.match(/^\/([a-zA-Z0-9-]*)$/);
  return match ? match[1].toLowerCase() : null;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export function JournalSlashMenu({
  onRequestImage,
}: {
  onRequestImage: () => void;
}) {
  const [editor] = useLexicalComposerContext();
  const [activeIndex, setActiveIndex] = useState(0);
  const [menuState, setMenuState] = useState<{
    anchorBottom: number;
    anchorLeft: number;
    anchorTop: number;
    query: string;
    visible: boolean;
  }>({
    anchorBottom: 0,
    anchorLeft: 0,
    anchorTop: 0,
    query: '',
    visible: false,
  });
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const visibleActions = useMemo(() => {
    if (!menuState.query) return ACTIONS;
    return ACTIONS.filter((action) => {
      return (
        action.label.includes(menuState.query) ||
        action.aliases.some((alias) => alias.includes(menuState.query))
      );
    });
  }, [menuState.query]);
  const resolvedActiveIndex =
    activeIndex < visibleActions.length ? activeIndex : 0;

  const closeMenu = useCallback(() => {
    setMenuState((current) => ({ ...current, visible: false, query: '' }));
    setActiveIndex(0);
  }, []);

  const clearSlashParagraph = useCallback(() => {
    editor.update(() => {
      const selection = $getSelection();
      if (!$isRangeSelection(selection)) return;
      const topLevel = selection.anchor.getNode().getTopLevelElement();
      if (!topLevel) return;
      if ($isParagraphNode(topLevel)) {
        topLevel.clear();
      }
    });
  }, [editor]);

  const applyAction = useCallback(
    (action: SlashAction) => {
      clearSlashParagraph();

      if (action.id === 'bullet-list') {
        editor.dispatchCommand(INSERT_UNORDERED_LIST_COMMAND, undefined);
        closeMenu();
        return;
      }

      if (action.id === 'ordered-list') {
        editor.dispatchCommand(INSERT_ORDERED_LIST_COMMAND, undefined);
        closeMenu();
        return;
      }

      if (action.id === 'image') {
        onRequestImage();
        closeMenu();
        return;
      }

      editor.update(() => {
        const selection = $getSelection();
        if (!$isRangeSelection(selection)) return;

        switch (action.id) {
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
            codeNode.append($createTextNode(''));
            topLevel.replace(codeNode, true);
            codeNode.selectEnd();
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

      closeMenu();
    },
    [clearSlashParagraph, closeMenu, editor, onRequestImage],
  );

  const updateMenu = useCallback(() => {
    editor.getEditorState().read(() => {
      const selection = $getSelection();
      if (!$isRangeSelection(selection) || !selection.isCollapsed()) {
        closeMenu();
        return;
      }

      const topLevel = selection.anchor.getNode().getTopLevelElement();
      if (!topLevel || !$isParagraphNode(topLevel)) {
        closeMenu();
        return;
      }

      const query = normalizeSlashQuery(topLevel.getTextContent());
      if (query === null) {
        closeMenu();
        return;
      }

      const domSelection = window.getSelection();
      if (!domSelection || domSelection.rangeCount === 0) {
        closeMenu();
        return;
      }

      const rect = domSelection.getRangeAt(0).getBoundingClientRect();
      setMenuState({
        anchorBottom: rect.bottom,
        anchorLeft: rect.left,
        anchorTop: rect.top,
        query,
        visible: true,
      });
      setActiveIndex((current) => (menuState.query === query ? current : 0));
    });
  }, [closeMenu, editor, menuState.query]);

  useEffect(() => {
    return editor.registerUpdateListener(() => {
      updateMenu();
    });
  }, [editor, updateMenu]);

  useEffect(() => {
    if (!menuState.visible) return undefined;
    const reposition = () => updateMenu();
    window.addEventListener('resize', reposition);
    window.addEventListener('scroll', reposition, true);
    return () => {
      window.removeEventListener('resize', reposition);
      window.removeEventListener('scroll', reposition, true);
    };
  }, [menuState.visible, updateMenu]);

  useEffect(() => {
    if (!menuState.visible) return;
    itemRefs.current[resolvedActiveIndex]?.scrollIntoView({ block: 'nearest' });
  }, [menuState.visible, resolvedActiveIndex]);

  useEffect(() => {
    return editor.registerCommand(
      KEY_DOWN_COMMAND,
      (event) => {
        if (!menuState.visible || visibleActions.length === 0) return false;

        if (event.key === 'ArrowDown') {
          event.preventDefault();
          setActiveIndex((index) => (index + 1) % visibleActions.length);
          return true;
        }

        if (event.key === 'ArrowUp') {
          event.preventDefault();
          setActiveIndex((index) => (index - 1 + visibleActions.length) % visibleActions.length);
          return true;
        }

        if (event.key === 'Enter') {
          event.preventDefault();
          applyAction(visibleActions[resolvedActiveIndex] ?? visibleActions[0]);
          return true;
        }

        if (event.key === 'Escape') {
          event.preventDefault();
          closeMenu();
          return true;
        }

        return false;
      },
      COMMAND_PRIORITY_LOW,
    );
  }, [applyAction, closeMenu, editor, menuState.visible, resolvedActiveIndex, visibleActions]);

  const menuStyle = useMemo(() => {
    if (!menuState.visible || typeof window === 'undefined') return null;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const maxHeight = Math.min(
      MENU_MAX_HEIGHT_PX,
      Math.max(180, viewportHeight - VIEWPORT_MARGIN_PX * 2),
    );
    const estimatedHeight = Math.min(maxHeight, 52 + visibleActions.length * 76);
    const width = Math.min(MENU_WIDTH, viewportWidth - VIEWPORT_MARGIN_PX * 2);
    const left = clamp(
      menuState.anchorLeft,
      VIEWPORT_MARGIN_PX,
      viewportWidth - width - VIEWPORT_MARGIN_PX,
    );
    const openUpward =
      menuState.anchorBottom + MENU_GAP_PX + estimatedHeight >
        viewportHeight - VIEWPORT_MARGIN_PX &&
      menuState.anchorTop - MENU_GAP_PX - estimatedHeight >= VIEWPORT_MARGIN_PX;
    const top = openUpward
      ? Math.max(VIEWPORT_MARGIN_PX, menuState.anchorTop - MENU_GAP_PX - estimatedHeight)
      : Math.min(
          menuState.anchorBottom + MENU_GAP_PX,
          viewportHeight - VIEWPORT_MARGIN_PX - estimatedHeight,
        );

    return {
      left,
      maxHeight,
      top,
      width,
    };
  }, [menuState, visibleActions.length]);

  if (!menuState.visible || visibleActions.length === 0 || !menuStyle || typeof document === 'undefined') {
    return null;
  }

  const menuContent = (
    <div
      role="listbox"
      aria-label="Journal slash menu"
      data-testid="journal-slash-menu"
      className="fixed z-[140] hidden rounded-[1.5rem] border border-white/58 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(247,241,234,0.96))] p-1.5 shadow-lift backdrop-blur-xl md:block"
      style={
        {
          left: menuStyle.left,
          top: menuStyle.top,
          width: menuStyle.width,
        } satisfies CSSProperties
      }
    >
      <div className="px-3 pb-1.5 pt-1">
        <p className="text-xs leading-6 text-muted-foreground">插入下一個段落節奏</p>
      </div>

      <div
        data-testid="journal-slash-menu-scroll"
        className="space-y-1 overflow-y-auto"
        style={{ maxHeight: menuStyle.maxHeight }}
      >
        {visibleActions.map((action, index) => {
          const active = index === resolvedActiveIndex;
          return (
            <button
              key={action.id}
              role="option"
              aria-selected={active}
              data-active={active ? 'true' : 'false'}
              data-testid={`journal-slash-option-${action.id}`}
              ref={(node) => {
                itemRefs.current[index] = node;
              }}
              type="button"
              onMouseDown={(event) => {
                event.preventDefault();
                applyAction(action);
              }}
              className={`flex w-full items-start gap-3 rounded-[1.1rem] px-3 py-3 text-left transition-all duration-haven ease-haven ${
                active ? 'bg-primary/[0.08] shadow-soft' : 'hover:bg-white/82'
              }`}
            >
              <span
                className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/55 bg-white/74 text-primary/78 shadow-soft"
                aria-hidden
              >
                {action.icon}
              </span>
              <span className="min-w-0 space-y-1">
                <span className="block text-sm font-medium text-card-foreground">
                  {action.label}
                </span>
                <span className="block text-xs leading-6 text-muted-foreground">
                  {action.description}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );

  return createPortal(menuContent, document.body);
}
