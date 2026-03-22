'use client';

import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { $findMatchingParent, $getSelection, $isRangeSelection, COMMAND_PRIORITY_LOW, FORMAT_TEXT_COMMAND, KEY_DOWN_COMMAND, SELECTION_CHANGE_COMMAND, type LexicalEditor } from 'lexical';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { $isLinkNode, TOGGLE_LINK_COMMAND } from '@lexical/link';
import { Bold, Code2, Italic, Link2 } from 'lucide-react';

interface ToolbarState {
  activeFormats: {
    bold: boolean;
    code: boolean;
    italic: boolean;
  };
  left: number;
  top: number;
  visible: boolean;
}

function getSelectedLinkUrl(editor: LexicalEditor): string {
  return editor.getEditorState().read(() => {
    const selection = $getSelection();
    if (!$isRangeSelection(selection)) return '';
    for (const node of selection.getNodes()) {
      if ($isLinkNode(node)) {
        return node.getURL();
      }
      const parentLink = $findMatchingParent(node, (candidate) => $isLinkNode(candidate));
      if (parentLink && $isLinkNode(parentLink)) {
        return parentLink.getURL();
      }
    }
    return '';
  });
}

function ToolbarButton({
  active,
  icon,
  label,
  onClick,
}: {
  active?: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      onMouseDown={(event) => {
        event.preventDefault();
        onClick();
      }}
      className={`inline-flex h-9 w-9 items-center justify-center rounded-full border transition-all duration-haven ease-haven ${
        active
          ? 'border-primary/20 bg-primary/[0.1] text-card-foreground shadow-soft'
          : 'border-white/52 bg-white/84 text-card-foreground shadow-soft hover:bg-white'
      }`}
    >
      {icon}
    </button>
  );
}

export function JournalFloatingToolbar() {
  const [editor] = useLexicalComposerContext();
  const [toolbarState, setToolbarState] = useState<ToolbarState>({
    activeFormats: { bold: false, code: false, italic: false },
    left: 0,
    top: 0,
    visible: false,
  });
  const [linkInputOpen, setLinkInputOpen] = useState(false);
  const [linkValue, setLinkValue] = useState('');

  const updateToolbar = useCallback(() => {
    editor.getEditorState().read(() => {
      const selection = $getSelection();
      if (!$isRangeSelection(selection) || selection.isCollapsed()) {
        setToolbarState((current) => ({ ...current, visible: false }));
        setLinkInputOpen(false);
        return;
      }

      const domSelection = window.getSelection();
      if (!domSelection || domSelection.rangeCount === 0) {
        setToolbarState((current) => ({ ...current, visible: false }));
        return;
      }

      const rect = domSelection.getRangeAt(0).getBoundingClientRect();
      if (!rect.width && !rect.height) {
        setToolbarState((current) => ({ ...current, visible: false }));
        return;
      }

      setToolbarState({
        activeFormats: {
          bold: selection.hasFormat('bold'),
          code: selection.hasFormat('code'),
          italic: selection.hasFormat('italic'),
        },
        left: rect.left + rect.width / 2,
        top: Math.max(20, rect.top - 16),
        visible: true,
      });

      if (!linkInputOpen) {
        setLinkValue(getSelectedLinkUrl(editor));
      }
    });
  }, [editor, linkInputOpen]);

  useEffect(() => {
    return editor.registerCommand(
      SELECTION_CHANGE_COMMAND,
      () => {
        updateToolbar();
        return false;
      },
      COMMAND_PRIORITY_LOW,
    );
  }, [editor, updateToolbar]);

  useEffect(() => {
    return editor.registerCommand(
      KEY_DOWN_COMMAND,
      (event) => {
        if (!(event.metaKey || event.ctrlKey)) return false;
        const key = event.key.toLowerCase();

        if (key === 'k') {
          event.preventDefault();
          setLinkValue(getSelectedLinkUrl(editor));
          setLinkInputOpen(true);
          updateToolbar();
          return true;
        }

        if (key === 'e') {
          event.preventDefault();
          editor.dispatchCommand(FORMAT_TEXT_COMMAND, 'code');
          return true;
        }

        return false;
      },
      COMMAND_PRIORITY_LOW,
    );
  }, [editor, updateToolbar]);

  useEffect(() => {
    const onViewportShift = () => updateToolbar();
    window.addEventListener('resize', onViewportShift);
    window.addEventListener('scroll', onViewportShift, true);
    return () => {
      window.removeEventListener('resize', onViewportShift);
      window.removeEventListener('scroll', onViewportShift, true);
    };
  }, [updateToolbar]);

  const toolbarStyle = useMemo(
    () => ({
      left: toolbarState.left,
      top: toolbarState.top,
      transform: 'translate(-50%, -100%)',
    }),
    [toolbarState.left, toolbarState.top],
  );

  if (!toolbarState.visible) return null;

  return (
    <div className="pointer-events-none fixed z-[120] hidden md:block" style={toolbarStyle}>
      <div className="pointer-events-auto flex items-center gap-1.5 rounded-full border border-white/56 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(247,241,234,0.93))] px-1.5 py-1.5 shadow-lift backdrop-blur-xl">
        <ToolbarButton
          active={toolbarState.activeFormats.bold}
          icon={<Bold className="h-4 w-4" aria-hidden />}
          label="粗體"
          onClick={() => editor.dispatchCommand(FORMAT_TEXT_COMMAND, 'bold')}
        />
        <ToolbarButton
          active={toolbarState.activeFormats.italic}
          icon={<Italic className="h-4 w-4" aria-hidden />}
          label="斜體"
          onClick={() => editor.dispatchCommand(FORMAT_TEXT_COMMAND, 'italic')}
        />
        <ToolbarButton
          active={toolbarState.activeFormats.code}
          icon={<Code2 className="h-4 w-4" aria-hidden />}
          label="行內程式碼"
          onClick={() => editor.dispatchCommand(FORMAT_TEXT_COMMAND, 'code')}
        />
        <ToolbarButton
          icon={<Link2 className="h-4 w-4" aria-hidden />}
          label="連結"
          onClick={() => {
            setLinkValue(getSelectedLinkUrl(editor));
            setLinkInputOpen((open) => !open);
          }}
        />

        {linkInputOpen ? (
          <div className="ml-1 flex items-center gap-2 rounded-full border border-white/56 bg-white/86 px-2 py-1.5 shadow-soft">
            <input
              type="url"
              value={linkValue}
              onChange={(event) => setLinkValue(event.target.value)}
              placeholder="貼上連結"
              className="w-40 bg-transparent text-sm text-card-foreground outline-none placeholder:text-muted-foreground/55"
            />
            <button
              type="button"
              onMouseDown={(event) => {
                event.preventDefault();
                editor.dispatchCommand(TOGGLE_LINK_COMMAND, linkValue.trim() || null);
                setLinkInputOpen(false);
              }}
              className="rounded-full border border-primary/12 bg-primary/[0.12] px-3 py-1 text-xs font-semibold text-card-foreground shadow-soft"
            >
              套用
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
