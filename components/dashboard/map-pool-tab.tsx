'use client'

import { useState, useEffect } from 'react'
import { Loader2, Check, RefreshCw, Trash2, Sparkles, Wrench, FileCode, Clock } from 'lucide-react'
import type { PoolMap } from '@/lib/data'

export function MapPoolTab({
  maps,
  onFillPool,
  onClearPool,
  onDeleteMap,
  onGenerateBatch,
  onCleanupStale,
}: {
  maps: PoolMap[]
  onFillPool: () => void
  onClearPool: () => void
  onDeleteMap?: (mapPath: string) => void
  onGenerateBatch?: (count: number) => void
  onCleanupStale?: () => void
}) {
  const [batchCount, setBatchCount] = useState(3)
  const [deletedMaps, setDeletedMaps] = useState<any[]>([])
  const [isDeleting, setIsDeleting] = useState<Record<string, boolean>>({})

  const fetchDeletedMaps = async () => {
    try {
      const r = await fetch('/api/deleted_maps')
      const res = await r.json()
      if (res.ok) {
        setDeletedMaps(res.items || [])
      }
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    fetchDeletedMaps()
  }, [maps])

  const handleDelete = async (mapPath: string, seed: string) => {
    if (!onDeleteMap) return
    const confirm = window.confirm(`Вы уверены, что хотите удалить карту seed ${seed} из пула? Файлы будут перенесены в архив _deleted_maps.`)
    if (!confirm) return

    try {
      setIsDeleting((prev) => ({ ...prev, [mapPath]: true }))
      await onDeleteMap(mapPath)
    } finally {
      setIsDeleting((prev) => ({ ...prev, [mapPath]: false }))
    }
  }

  return (
    <div className="flex flex-col gap-8 w-full">
      {/* Pool Header & Basic Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Активный пул готовых карт ({maps.length})
        </h2>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onFillPool}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 shadow-md cursor-pointer"
          >
            <RefreshCw className="size-4" aria-hidden="true" />
            Добить пул (Fill Pool)
          </button>
          {onCleanupStale && (
            <button
              type="button"
              onClick={onCleanupStale}
              className="flex items-center gap-2 rounded-md border border-border bg-secondary px-4 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-secondary/80 cursor-pointer"
            >
              <Wrench className="size-4" aria-hidden="true" />
              Очистить мусор (Cleanup)
            </button>
          )}
          <button
            type="button"
            onClick={onClearPool}
            className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2.5 text-sm font-semibold text-destructive transition-colors hover:bg-destructive/20 cursor-pointer"
          >
            <Trash2 className="size-4" aria-hidden="true" />
            Очистить пул
          </button>
        </div>
      </div>

      {/* Manual Batch Generation Card */}
      {onGenerateBatch && (
        <section className="rounded-lg border border-border bg-card p-5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
            <Sparkles className="size-4 text-primary" />
            Ручной заказ генерации карт
          </h3>
          <div className="flex items-center gap-3">
            <div className="flex flex-col gap-1 w-24">
              <input
                type="number"
                min={1}
                max={7}
                value={batchCount}
                onChange={(e) => setBatchCount(Math.max(1, Math.min(7, Number(e.target.value))))}
                className="rounded-md border border-input bg-background px-3 py-2 text-center text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/50 font-mono"
              />
            </div>
            <button
              type="button"
              onClick={() => onGenerateBatch(batchCount)}
              className="rounded-md bg-secondary hover:bg-secondary/80 border border-border px-5 py-2 text-sm font-semibold text-foreground transition-colors cursor-pointer"
            >
              Сгенерировать пакет карт ({batchCount} шт.)
            </button>
          </div>
        </section>
      )}

      {/* Maps Grid */}
      {maps.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border py-16 text-center text-sm text-muted-foreground">
          Пул пуст. Нажмите «Добить пул» или настройте автовайп.
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4">
          {maps.map((map) => (
            <div
              key={map.id}
              className="group relative overflow-hidden rounded-lg border border-border bg-card transition-all hover:border-primary/50 hover:shadow-md"
            >
              <div className="relative aspect-square bg-black flex items-center justify-center">
                {map.preview ? (
                  <img
                    src={map.preview}
                    alt={`Превью карты seed ${map.seed}`}
                    className="absolute inset-0 h-full w-full object-cover transition-transform group-hover:scale-105"
                  />
                ) : (
                  <span className="text-xs text-muted-foreground">Без превью</span>
                )}
                
                {/* Status Dot */}
                <div className="absolute left-2.5 top-2.5">
                  {map.status === 'ready' ? (
                    <span className="flex items-center gap-1 rounded-full bg-success/90 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary-foreground shadow-sm">
                      <Check className="size-3" aria-hidden="true" />
                      Ready
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 rounded-full bg-warning/90 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary-foreground shadow-sm">
                      <Loader2 className="size-3 animate-spin" aria-hidden="true" />
                      Gen
                    </span>
                  )}
                </div>

                {/* Delete Button overlay on hover */}
                {onDeleteMap && map.map_path && (
                  <button
                    type="button"
                    disabled={isDeleting[map.map_path]}
                    onClick={() => handleDelete(map.map_path!, map.seed)}
                    className="absolute right-2.5 top-2.5 rounded bg-black/60 p-2 text-destructive border border-destructive/20 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive hover:text-white"
                    title="Удалить карту из пула"
                  >
                    {isDeleting[map.map_path] ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="size-3.5" />
                    )}
                  </button>
                )}
              </div>
              
              <div className="flex items-center justify-between px-3.5 py-3">
                <div>
                  <div className="font-mono text-sm font-semibold tabular-nums text-foreground">
                    {map.seed}
                  </div>
                  <div className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">
                    seed
                  </div>
                </div>
                <div className="font-mono text-xs text-foreground font-semibold bg-secondary/80 px-2 py-0.5 rounded border border-border">
                  {map.size}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Soft-deleted Maps Archive List */}
      {deletedMaps.length > 0 && (
        <section className="mt-4 border-t border-border pt-6">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">
            Недавно удалённые файлы карт (Архив восстановления)
          </h3>
          <div className="rounded-lg border border-border bg-card p-5 flex flex-col gap-3 max-h-60 overflow-y-auto">
            {deletedMaps.map((item, idx) => (
              <div key={idx} className="flex items-start justify-between border-b border-border/50 pb-2.5 last:border-b-0 last:pb-0 text-xs">
                <div className="flex items-start gap-2.5 font-mono">
                  <FileCode className="size-4 text-muted-foreground mt-0.5 shrink-0" />
                  <div className="flex flex-col gap-0.5">
                    <span className="text-foreground truncate max-w-md sm:max-w-xl">{item.folder.split('\\').pop() || item.folder}</span>
                    <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <Clock className="size-3" />
                      {new Date(item.created_at * 1000).toLocaleString()} | Карт в пакете: {item.map_count}
                    </span>
                  </div>
                </div>
                <div className="text-muted-foreground font-mono text-[10px] shrink-0">
                  {item.maps.map((m: string) => m.split(/[\\/]/).pop()).join(', ')}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
