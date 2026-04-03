'use client';

import { type FormEvent, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowRight, CalendarDays, HeartHandshake, Sparkles, Stars } from 'lucide-react';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Input, { Textarea } from '@/components/ui/Input';
import { useBlueprint } from '@/hooks/queries';
import { useToast } from '@/hooks/useToast';
import { queryKeys } from '@/lib/query-keys';
import { logClientError } from '@/lib/safe-error-log';
import { addBlueprintItem } from '@/services/api-client';
import BlueprintSkeleton from './BlueprintSkeleton';
import {
  BlueprintCompanionWish,
  BlueprintCover,
  BlueprintFeaturedWish,
  BlueprintOverviewCard,
  BlueprintShelfWish,
  BlueprintStatePanel,
  BlueprintWishStudio,
} from './BlueprintPrimitives';

function formatWishDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function formatWishShortDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('zh-TW', {
    month: 'long',
    day: 'numeric',
  });
}

export default function BlueprintPageContent() {
  const blueprintQuery = useBlueprint();
  const queryClient = useQueryClient();
  const [submitting, setSubmitting] = useState(false);
  const [title, setTitle] = useState('');
  const [notes, setNotes] = useState('');
  const { showToast } = useToast();

  const items = blueprintQuery.data ?? [];
  const featuredItem = items[0] ?? null;
  const companionItems = items.slice(1, 3);
  const shelfItems = items.slice(3);
  const myCount = items.filter((item) => item.added_by_me).length;
  const partnerCount = items.length - myCount;
  const latestCreatedAt = items.reduce<string | null>((latest, item) => {
    if (!latest) {
      return item.created_at;
    }
    return new Date(item.created_at).getTime() > new Date(latest).getTime()
      ? item.created_at
      : latest;
  }, null);

  const pulse =
    items.length > 0
      ? `這裡已經收進 ${items.length} 個 Shared Future 片段。Relationship System 會整理其中最重要的摘要，而完整輪廓仍保留在這裡。`
      : '還沒有任何 Shared Future 片段也沒關係。真正重要的是，這裡開始替你們的未來留出一個可以被想像的位置。';

  const primaryActionLabel =
    items.length > 0 ? '再放進一個想一起實現的願望' : '寫下第一個未來片段';

  const handleAdd = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedTitle = title.trim();

    if (!trimmedTitle) {
      showToast('請輸入願望或項目', 'error');
      return;
    }

    setSubmitting(true);
    try {
      await addBlueprintItem(trimmedTitle, notes.trim() || undefined);
      setTitle('');
      setNotes('');
      await queryClient.invalidateQueries({ queryKey: queryKeys.blueprint() });
      showToast('已加入願望清單', 'success');
    } catch (err) {
      logClientError('blueprint-add-failed', err);
      showToast('加入失敗，請稍後再試', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  if (blueprintQuery.isLoading) {
    return <BlueprintSkeleton />;
  }

  return (
    <div className="space-y-[clamp(1.5rem,3vw,2.75rem)]">
      <BlueprintCover
        eyebrow="Shared Future / Blueprint"
        title="把你們想一起靠近的日子，放進 Shared Future 的完整藍圖。"
        description="Relationship System 會整理高價值的 Shared Future 摘要；Blueprint 則保留完整片段、備註與新增入口。這裡不是待辦清單，而是你們共同未來的完整工作台。"
        pulse={pulse}
        primaryActionHref="#wish-studio"
        primaryActionLabel={primaryActionLabel}
        highlights={
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-[1.7rem] border border-white/54 bg-white/74 px-4 py-4 shadow-soft backdrop-blur-md">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Sparkles className="h-4 w-4" aria-hidden />
                </span>
                <div className="space-y-1">
                  <p className="type-micro uppercase text-primary/80">共同想像</p>
                  <p className="text-xl font-semibold text-card-foreground">{items.length} 個片段</p>
                  <p className="type-caption text-muted-foreground">先讓願望被看見，再決定它什麼時候發生。</p>
                </div>
              </div>
            </div>

            <div className="rounded-[1.7rem] border border-white/54 bg-white/74 px-4 py-4 shadow-soft backdrop-blur-md">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <HeartHandshake className="h-4 w-4" aria-hidden />
                </span>
                <div className="space-y-1">
                  <p className="type-micro uppercase text-primary/80">一起寫下</p>
                  <p className="text-xl font-semibold text-card-foreground">
                    {partnerCount > 0 ? `${myCount} / ${partnerCount}` : `${myCount} / 0`}
                  </p>
                  <p className="type-caption text-muted-foreground">不是誰的清單，而是兩個人慢慢對齊的願景。</p>
                </div>
              </div>
            </div>

            <div className="rounded-[1.7rem] border border-white/54 bg-white/74 px-4 py-4 shadow-soft backdrop-blur-md">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <CalendarDays className="h-4 w-4" aria-hidden />
                </span>
                <div className="space-y-1">
                  <p className="type-micro uppercase text-primary/80">最近加入</p>
                  <p className="text-xl font-semibold text-card-foreground">
                    {latestCreatedAt ? formatWishShortDate(latestCreatedAt) : '等你們寫下'}
                  </p>
                  <p className="type-caption text-muted-foreground">每一次新增，都是把未來往前點亮一點點。</p>
                </div>
              </div>
            </div>
          </div>
        }
        aside={
          <>
            <BlueprintOverviewCard
              eyebrow="Shared Future"
              title="這張藍圖正在慢慢成形。"
              description="Relationship System 會引用這裡最重要的片段，讓共同未來同時是摘要，也是完整藍圖。"
            >
              <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                <div className="rounded-[1.6rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">我寫下</p>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground">{myCount}</p>
                </div>
                <div className="rounded-[1.6rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">伴侶寫下</p>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground">{partnerCount}</p>
                </div>
                <div className="rounded-[1.6rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                  <p className="type-micro uppercase text-primary/80">最近更新</p>
                  <p className="mt-2 text-lg font-semibold text-card-foreground">
                    {latestCreatedAt ? formatWishShortDate(latestCreatedAt) : '尚未開始'}
                  </p>
                </div>
              </div>
            </BlueprintOverviewCard>

            <BlueprintOverviewCard
              eyebrow="House Note"
              title="把願望放在會被重新翻開的地方。"
              description="這裡不急著把人生排滿，只是讓想一起過的日子，有一個被記住、被反覆想像、被慢慢靠近的輪廓。"
            >
              <div className="rounded-[1.8rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
                <div className="flex items-start gap-3">
                  <span className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Stars className="h-4 w-4" aria-hidden />
                  </span>
                  <p className="type-body-muted text-card-foreground">
                    寫下來的每一個願望，都不是壓力，而是對彼此說：「我還想和你一起把生活過成這個樣子。」
                  </p>
                </div>
              </div>
            </BlueprintOverviewCard>
          </>
        }
      />

      <BlueprintWishStudio
        id="wish-studio"
        eyebrow="Wish Studio"
        title="把下一個想一起擁有的場景寫下來。"
        description="可以是一個想去的地方、一個想一起養成的儀式、一個想實現的小願望，或只是某種你希望兩個人一起活成的樣子。"
        footer={
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-[1.7rem] border border-white/54 bg-white/72 px-4 py-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">如何寫會更好</p>
              <p className="mt-2 type-caption text-muted-foreground">
                標題寫願望本身，備註可以補上為什麼想做、什麼季節、或你期待和對方一起感受到什麼。
              </p>
            </div>
            <div className="rounded-[1.7rem] border border-white/54 bg-white/72 px-4 py-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">不是任務，是想像</p>
              <p className="mt-2 type-caption text-muted-foreground">
                先讓願望存在，再慢慢決定什麼時候靠近它。這裡的重點不是完成，而是共同想要。
              </p>
            </div>
          </div>
        }
      >
        <form onSubmit={handleAdd} className="space-y-4">
          <Input
            id="blueprint-title"
            label="標題"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="例如：冬天一起去看雪，或每個月留一晚只屬於我們"
            maxLength={500}
            helperText="標題最多 500 字。寫下最想一起擁有的畫面就好。"
          />

          <Textarea
            id="blueprint-notes"
            label="備註（選填）"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="補充這個願望背後的原因、氣味、季節、地點，或你想和對方一起感受到什麼。"
            maxLength={2000}
            helperText="備註最多 2000 字。可以留白，等下次再一起補上。"
          />

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <p className="type-caption text-muted-foreground">
              新增後會立刻回到這張藍圖裡，成為你們之後可以反覆回來看的未來片段。
            </p>
            <Button
              type="submit"
              size="lg"
              loading={submitting}
              rightIcon={<ArrowRight className="h-4 w-4" aria-hidden />}
              aria-label="加入願望清單"
            >
              放進共同藍圖
            </Button>
          </div>
        </form>
      </BlueprintWishStudio>

      {blueprintQuery.isError && !blueprintQuery.data ? (
        <BlueprintStatePanel
          tone="error"
          eyebrow="Collection unavailable"
          title="這張藍圖暫時沒有順利展開。"
          description="願望沒有遺失，只是這次載入失敗了。你可以重新整理這張頁面，讓那些已經寫下的未來片段再回到眼前。"
          action={
            <Button variant="secondary" onClick={() => void blueprintQuery.refetch()}>
              重新載入
            </Button>
          }
        />
      ) : null}

      {!blueprintQuery.isError && items.length === 0 ? (
        <BlueprintStatePanel
          tone="quiet"
          eyebrow="Your canvas is still open"
          title="還沒有任何願望，這正好代表它還完全敞開。"
          description="第一個願望不需要很大。只要先放進一個你們想一起擁有的畫面，這張藍圖就會開始變得值得回來看。"
          action={
            <a
              href="#wish-studio"
              className="inline-flex items-center gap-2 rounded-full border border-primary/18 bg-primary/10 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-primary/14 hover:shadow-lift focus-ring-premium"
            >
              把第一個願望寫下來
              <ArrowRight className="h-4 w-4" aria-hidden />
            </a>
          }
        />
      ) : null}

      {!blueprintQuery.isError && featuredItem ? (
        <section className="space-y-6">
          <div className="space-y-3 px-1">
            <Badge variant="metadata" size="sm" className="border-white/56 bg-white/72 text-primary/80 shadow-soft">
              Future Shelf
            </Badge>
            <div className="space-y-2">
              <h2 className="type-h2 text-card-foreground">正在成形的未來</h2>
              <p className="max-w-3xl type-body-muted text-muted-foreground">
                把最先被放進來的一個片段放大，讓這張藍圖先有一個可以停留的中心；其餘的願望則安靜地排在旁邊，像還沒發生、但已經開始存在的未來記憶。
              </p>
            </div>
          </div>

          <BlueprintFeaturedWish
            title={featuredItem.title}
            notes={featuredItem.notes}
            authorLabel={featuredItem.added_by_me ? '我先寫下' : '伴侶先寫下'}
            createdLabel={formatWishDate(featuredItem.created_at)}
            spotlight={
              featuredItem.added_by_me
                ? '這是你先遞出去的一個未來畫面。它讓對方知道，你想和他一起把生活帶去哪裡。'
                : '這是對方先放進來的一個未來畫面。先停一下，好好看看他想和你一起靠近的是什麼。'
            }
          />

          {companionItems.length > 0 ? (
            <div className="space-y-4">
              <div className="space-y-2 px-1">
                <p className="type-micro uppercase text-primary/80">Companion Wishes</p>
                <h3 className="type-h3 text-card-foreground">接在後面的兩個想像</h3>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                {companionItems.map((item) => (
                  <BlueprintCompanionWish
                    key={item.id}
                    title={item.title}
                    notes={item.notes}
                    authorLabel={item.added_by_me ? '我寫下' : '伴侶寫下'}
                    createdLabel={formatWishDate(item.created_at)}
                  />
                ))}
              </div>
            </div>
          ) : null}

          {shelfItems.length > 0 ? (
            <div className="space-y-4">
              <div className="space-y-2 px-1">
                <p className="type-micro uppercase text-primary/80">Quiet Future Shelf</p>
                <h3 className="type-h3 text-card-foreground">其餘還在等你們慢慢靠近的願望</h3>
              </div>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {shelfItems.map((item) => (
                  <BlueprintShelfWish
                    key={item.id}
                    title={item.title}
                    notes={item.notes}
                    authorLabel={item.added_by_me ? '我寫下' : '伴侶寫下'}
                    createdLabel={formatWishDate(item.created_at)}
                  />
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
