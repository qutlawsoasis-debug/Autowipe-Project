'use client'

import { XCircle, Send } from 'lucide-react'
import { StatusDot } from './header'

export function VoteTab({
  systemState,
  onPublishVote,
  onCancelVote,
}: {
  systemState: any
  onPublishVote: () => void
  onCancelVote: () => void
}) {
  const vote = systemState?.vote
  const isActive = !!vote && vote.active !== false

  const candidates = vote?.candidates || []
  const totalVotes = candidates.reduce((sum: number, c: any) => sum + (c.votes || 0), 0)
  const maxVotes = Math.max(...candidates.map((c: any) => c.votes || 0), 1)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 rounded-md border border-border bg-card px-3.5 py-2 text-sm">
          <StatusDot status={isActive ? 'online' : 'offline'} />
          <span>{isActive ? 'Голосование активно в Discord' : 'Голосование не запущено'}</span>
          {isActive && (
            <span className="font-mono text-xs text-muted-foreground">
              {totalVotes} голосов
            </span>
          )}
        </div>
        
        {isActive ? (
          <button
            type="button"
            onClick={onCancelVote}
            className="flex items-center gap-2 rounded-md border border-border bg-secondary px-4 py-2 text-sm text-secondary-foreground transition-colors hover:bg-secondary/70"
          >
            <XCircle className="size-4" aria-hidden="true" />
            Отменить голосование
          </button>
        ) : (
          <button
            type="button"
            onClick={onPublishVote}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground transition-opacity hover:opacity-90"
          >
            <Send className="size-4" aria-hidden="true" />
            Опубликовать голосование
          </button>
        )}
      </div>

      {isActive && candidates.length > 0 ? (
        <div className="flex flex-col gap-3">
          {candidates.map((v: any, index: number) => {
            const percent = Math.round(((v.votes || 0) / maxVotes) * 100)
            const share = totalVotes > 0 ? Math.round(((v.votes || 0) / totalVotes) * 100) : 0
            const preview = v.preview_url ? `/media?path=${encodeURIComponent(v.map_path)}` : ''
            
            return (
              <div
                key={v.seed}
                className="flex flex-col gap-4 rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/40"
              >
                <div className="relative w-full h-64 shrink-0 overflow-hidden rounded-md border border-border bg-black flex items-center justify-center">
                  {preview ? (
                    <img
                      src={preview}
                      alt={`Превью карты seed ${v.seed}`}
                      className="absolute inset-0 h-full w-full object-cover"
                    />
                  ) : (
                    <span className="text-[10px] text-muted-foreground">No image</span>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-mono text-sm font-semibold tabular-nums">
                      Seed: {v.seed}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {v.size}m
                    </span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-secondary">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${percent}%` }}
                      role="progressbar"
                      aria-valuenow={v.votes || 0}
                      aria-valuemin={0}
                      aria-valuemax={maxVotes}
                      aria-label={`Голоса за карту ${v.seed}`}
                    />
                  </div>
                  <div className="mt-1.5 flex justify-between text-xs text-muted-foreground">
                    <span className="font-mono tabular-nums">{v.votes || 0} голосов</span>
                    <span className="font-mono tabular-nums">{share}%</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        isActive && (
          <div className="rounded-lg border border-dashed border-border py-16 text-center text-sm text-muted-foreground">
            Голосование запущено, но кандидаты отсутствуют.
          </div>
        )
      )}
    </div>
  )
}
