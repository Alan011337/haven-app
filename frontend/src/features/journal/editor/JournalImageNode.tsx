'use client';

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { ImagePlus } from 'lucide-react';
import {
  DecoratorNode,
  createCommand,
  type LexicalCommand,
  type LexicalNode,
  type NodeKey,
  type SerializedLexicalNode,
  type Spread,
} from 'lexical';
import type { JournalAttachmentPublic } from '@/types';

export interface InsertJournalImagePayload {
  alt: string;
  src: string;
}

export const INSERT_JOURNAL_IMAGE_COMMAND: LexicalCommand<InsertJournalImagePayload> =
  createCommand('INSERT_JOURNAL_IMAGE_COMMAND');

export const JOURNAL_ATTACHMENT_CAPTION_MAX_LENGTH = 280;

type AttachmentMap = Record<string, JournalAttachmentPublic>;

type CaptionChangeHandler = (
  attachmentId: string,
  caption: string | null,
) => Promise<void> | void;

interface JournalAttachmentContextValue {
  attachmentMap: AttachmentMap;
  onCaptionChange?: CaptionChangeHandler;
}

const JournalAttachmentContext = createContext<JournalAttachmentContextValue>({
  attachmentMap: {},
});

export type SerializedJournalImageNode = Spread<
  {
    alt: string;
    src: string;
    type: 'journal-image';
    version: 1;
  },
  SerializedLexicalNode
>;

export function JournalAttachmentProvider({
  attachments,
  onCaptionChange,
  children,
}: {
  attachments: JournalAttachmentPublic[];
  onCaptionChange?: CaptionChangeHandler;
  children: ReactNode;
}) {
  const attachmentMap = useMemo<AttachmentMap>(() => {
    return attachments.reduce<AttachmentMap>((map, attachment) => {
      map[attachment.id] = attachment;
      return map;
    }, {});
  }, [attachments]);

  const value = useMemo<JournalAttachmentContextValue>(
    () => ({ attachmentMap, onCaptionChange }),
    [attachmentMap, onCaptionChange],
  );

  return (
    <JournalAttachmentContext.Provider value={value}>
      {children}
    </JournalAttachmentContext.Provider>
  );
}

function parseAttachmentIdFromSrc(src: string): string | null {
  const trimmed = src.trim();
  if (!trimmed.startsWith('attachment:')) return null;
  const id = trimmed.replace('attachment:', '').trim();
  return id || null;
}

function resolveJournalImageSource(src: string, attachmentMap: AttachmentMap): string | null {
  const trimmed = src.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith('attachment:')) {
    const attachmentId = trimmed.replace('attachment:', '').trim();
    return attachmentMap[attachmentId]?.url ?? null;
  }
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return null;
}

function JournalImageCard({ alt, src }: InsertJournalImagePayload) {
  const { attachmentMap, onCaptionChange } = useContext(JournalAttachmentContext);
  const attachmentId = parseAttachmentIdFromSrc(src);
  const attachment = attachmentId ? attachmentMap[attachmentId] : null;
  const resolvedSrc = resolveJournalImageSource(src, attachmentMap);
  const serverCaption = attachment?.caption ?? '';
  const canAuthor = Boolean(attachmentId && onCaptionChange);

  const [draft, setDraft] = useState<string>(serverCaption);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft(serverCaption);
  }, [serverCaption]);

  const handleBlur = async () => {
    if (!canAuthor || !attachmentId || !onCaptionChange) return;
    const trimmed = draft.trim();
    const previous = (serverCaption ?? '').trim();
    if (trimmed === previous) return;
    try {
      setSaving(true);
      await onCaptionChange(attachmentId, trimmed.length > 0 ? trimmed : null);
    } finally {
      setSaving(false);
    }
  };

  if (!resolvedSrc) {
    return (
      <figure className="my-8 overflow-hidden rounded-[1.9rem] border border-dashed border-border/80 bg-[linear-gradient(180deg,rgba(255,250,246,0.9),rgba(246,240,233,0.84))] p-5 shadow-glass-inset">
        <div className="flex min-h-[180px] flex-col items-center justify-center gap-3 rounded-[1.45rem] border border-white/58 bg-white/66 text-center text-muted-foreground">
          <span className="icon-badge !h-10 !w-10" aria-hidden>
            <ImagePlus className="h-4 w-4" />
          </span>
          <div className="space-y-1">
            <p className="text-sm font-medium text-card-foreground">
              圖片正在安靜整理
            </p>
            <p className="max-w-sm text-xs leading-6">
              資產已經掛在這一頁上，Haven 會在附件同步回來後把它補成真正的版面。
            </p>
          </div>
        </div>
      </figure>
    );
  }

  const altForImage = (draft.trim() || serverCaption || alt || 'journal image').trim();

  return (
    <figure className="group my-8 overflow-hidden rounded-[2rem] border border-[rgba(219,204,187,0.45)] bg-[linear-gradient(180deg,rgba(255,255,255,0.82),rgba(249,244,237,0.9))] shadow-soft">
      {/* eslint-disable-next-line @next/next/no-img-element -- Signed attachment URLs are dynamic and unsuitable for Next image optimization. */}
      <img
        alt={altForImage}
        className="max-h-[520px] w-full object-contain"
        src={resolvedSrc}
      />
      {canAuthor ? (
        <figcaption className="border-t border-white/58 px-5 py-3">
          <label className="sr-only" htmlFor={`journal-image-caption-${attachmentId}`}>
            為這張照片寫一句話
          </label>
          <textarea
            id={`journal-image-caption-${attachmentId}`}
            value={draft}
            onChange={(event) => {
              const next = event.target.value.slice(0, JOURNAL_ATTACHMENT_CAPTION_MAX_LENGTH);
              setDraft(next);
            }}
            onBlur={handleBlur}
            placeholder="為這張照片寫一句話（選填）"
            rows={1}
            maxLength={JOURNAL_ATTACHMENT_CAPTION_MAX_LENGTH}
            disabled={saving}
            className="w-full resize-none bg-transparent text-sm leading-7 text-muted-foreground placeholder:text-muted-foreground/55 focus:outline-none focus:text-card-foreground disabled:opacity-60"
            aria-describedby={`journal-image-caption-${attachmentId}-hint`}
          />
          <p
            id={`journal-image-caption-${attachmentId}-hint`}
            className="mt-1 text-[0.68rem] tracking-[0.12em] text-muted-foreground/55 tabular-nums"
          >
            {draft.length > 0
              ? `${draft.length} / ${JOURNAL_ATTACHMENT_CAPTION_MAX_LENGTH}`
              : '失焦時會自動儲存'}
          </p>
        </figcaption>
      ) : serverCaption ? (
        <figcaption className="border-t border-white/58 px-5 py-3 text-sm leading-7 text-muted-foreground">
          {serverCaption}
        </figcaption>
      ) : null}
    </figure>
  );
}

export class JournalImageNode extends DecoratorNode<ReactNode> {
  __alt: string;
  __src: string;

  static getType(): string {
    return 'journal-image';
  }

  static clone(node: JournalImageNode): JournalImageNode {
    return new JournalImageNode(node.__src, node.__alt, node.__key);
  }

  static importJSON(serializedNode: SerializedJournalImageNode): JournalImageNode {
    return new JournalImageNode(serializedNode.src, serializedNode.alt);
  }

  constructor(src: string, alt = '', key?: NodeKey) {
    super(key);
    this.__src = src;
    this.__alt = alt;
  }

  exportJSON(): SerializedJournalImageNode {
    return {
      ...super.exportJSON(),
      alt: this.getAltText(),
      src: this.getSrc(),
      type: 'journal-image',
      version: 1,
    };
  }

  createDOM(): HTMLElement {
    const element = document.createElement('div');
    element.className = 'journal-image-node';
    return element;
  }

  updateDOM(): false {
    return false;
  }

  getAltText(): string {
    return this.getLatest().__alt;
  }

  getSrc(): string {
    return this.getLatest().__src;
  }

  setAltText(alt: string): void {
    const writable = this.getWritable();
    writable.__alt = alt;
  }

  setSrc(src: string): void {
    const writable = this.getWritable();
    writable.__src = src;
  }

  decorate(): ReactNode {
    return <JournalImageCard alt={this.__alt} src={this.__src} />;
  }
}

export function $createJournalImageNode(payload: InsertJournalImagePayload): JournalImageNode {
  return new JournalImageNode(payload.src, payload.alt);
}

export function $isJournalImageNode(
  node: LexicalNode | null | undefined,
): node is JournalImageNode {
  return node instanceof JournalImageNode;
}
