'use client';

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { ImagePlus, Plus } from 'lucide-react';
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
import { JOURNAL_RHYTHM } from '@/features/journal/journal-document-rhythm';
import { JOURNAL_IMAGE_ALT_FALLBACK } from '@/features/journal/editor/journal-attachment-markdown';

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
  // Two-state affordance: fresh uncaptioned images collapse to a prompt
  // button; existing captioned images open expanded so re-edit is one click.
  const [expanded, setExpanded] = useState<boolean>(() =>
    Boolean((serverCaption ?? '').trim()),
  );
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    setDraft(serverCaption);
    // Server-driven growth (cross-tab, partner-side save): if the caption
    // arrives from elsewhere while we were collapsed, expand so the author
    // sees it immediately.
    if ((serverCaption ?? '').trim() && !expanded) setExpanded(true);
  }, [serverCaption, expanded]);

  // User-initiated expansion drops focus into the textarea so typing starts
  // immediately. Server-initiated expansion also routes here, which is
  // acceptable — focus follows the newly-surfaced editable surface.
  useEffect(() => {
    if (expanded) textareaRef.current?.focus();
  }, [expanded]);

  const persistCaption = async (value: string) => {
    if (!attachmentId || !onCaptionChange) return;
    try {
      setSaving(true);
      await onCaptionChange(attachmentId, value.length > 0 ? value : null);
    } finally {
      setSaving(false);
    }
  };

  // Synchronous blur: capture state, schedule save, decide collapse. The
  // save is fire-and-forget (void) so the UI can settle into its next
  // state without waiting on the network.
  const handleBlur = () => {
    if (!canAuthor || !attachmentId || !onCaptionChange) return;
    if (saving) return;
    const trimmed = draft.trim();
    const previous = (serverCaption ?? '').trim();
    const shouldSave = trimmed !== previous;
    const shouldCollapse = trimmed.length === 0 && previous.length === 0;
    if (shouldSave) void persistCaption(trimmed);
    if (shouldCollapse) setExpanded(false);
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

  // SR alt: prefer the current draft, then any server caption, then the
  // humanized alt from the wire format, with the shared fallback constant
  // as the final backstop. The visible caption is decided independently
  // below so a suppressed figcaption never strips alt from the <img>.
  const altForImage = (draft.trim() || serverCaption || alt || JOURNAL_IMAGE_ALT_FALLBACK).trim();
  const captionId = attachmentId ? `journal-image-caption-${attachmentId}` : undefined;

  return (
    <figure
      data-testid="journal-figure"
      className={`group ${JOURNAL_RHYTHM.figure}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- Signed attachment URLs are dynamic and unsuitable for Next image optimization. */}
      <img
        data-testid="journal-figure-image"
        alt={altForImage}
        className={JOURNAL_RHYTHM.figureImage}
        src={resolvedSrc}
      />
      {canAuthor && !expanded ? (
        <button
          type="button"
          data-testid="journal-figure-caption-prompt"
          aria-expanded="false"
          aria-controls={captionId}
          onClick={() => setExpanded(true)}
          className={JOURNAL_RHYTHM.figcaptionPromptButton}
        >
          <Plus className="h-3.5 w-3.5" aria-hidden />
          <span>為這段影像加一句描述</span>
        </button>
      ) : null}
      {canAuthor && expanded ? (
        <figcaption
          data-testid="journal-figure-caption"
          data-caption-kind="authored"
          className={JOURNAL_RHYTHM.figcaptionWriteShell}
        >
          <label className="sr-only" htmlFor={captionId}>
            為這張照片寫一句話
          </label>
          <textarea
            id={captionId}
            ref={textareaRef}
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
            className="w-full resize-none bg-transparent font-art italic text-[0.95rem] leading-[1.75] text-muted-foreground placeholder:text-muted-foreground/55 focus:outline-none focus:text-card-foreground disabled:opacity-60"
            aria-describedby={captionId ? `${captionId}-hint` : undefined}
          />
          <p
            id={captionId ? `${captionId}-hint` : undefined}
            className="mt-1 text-[0.68rem] tracking-[0.12em] text-muted-foreground/55 tabular-nums"
          >
            {draft.length > 0
              ? `${draft.length} / ${JOURNAL_ATTACHMENT_CAPTION_MAX_LENGTH}`
              : '失焦時會自動儲存'}
          </p>
        </figcaption>
      ) : null}
      {!canAuthor && serverCaption ? (
        <figcaption
          data-testid="journal-figure-caption"
          data-caption-kind="authored"
          className={JOURNAL_RHYTHM.figcaptionAuthored}
        >
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
