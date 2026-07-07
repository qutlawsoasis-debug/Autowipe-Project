'use client'

import { AlertTriangle, Eraser, RotateCcw } from 'lucide-react'

interface WipeRecord {
  date: string
  type: 'Ordinary' | 'Full'
  seed: number
  size: string
  success: boolean
}

export function ScheduleTab({
  systemState,
  onWipeOrdinary,
  onWipeFull,
  onClearError,
}: {
  systemState: any
  onWipeOrdinary: () => void
  onWipeFull: () => void
  onClearError: () => void
}) {
  const history: WipeRecord[] = systemState?.wipe_history || [
    { date: 'Сегодня, 20:00 UTC (Запланировано)', type: 'Ordinary', seed: 45621, size: '3500x3500', success: true },
    { date: '30 июня 2026, 20:00 UTC', type: 'Full', seed: 28456, size: '4000x4000', success: true },
    { date: '23 июня 2026, 20:00 UTC', type: 'Ordinary', seed: 91234, size: '3500x3500', success: true },
  ]

  const hasWipeError = !!systemState?.wipe_error

  return (
    <div className="flex flex-col gap-8">
      {hasWipeError && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive flex items-center justify-between">
          <span>⚠️ Ошибка вайпа: {systemState.wipe_error}</span>
          <button
            type="button"
            onClick={onClearError}
            className="rounded bg-destructive px-3 py-1.5 text-xs font-semibold text-white hover:bg-destructive/90"
          >
            Сбросить ошибку
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onWipeOrdinary}
          className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/20"
        >
          <RotateCcw className="size-4" aria-hidden="true" />
          Ordinary Wipe (сейчас)
        </button>
        <button
          type="button"
          onClick={onWipeFull}
          className="flex items-center gap-2 rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground transition-opacity hover:opacity-90"
        >
          <AlertTriangle className="size-4" aria-hidden="true" />
          Full Wipe (сейчас)
        </button>
        <button
          type="button"
          onClick={onClearError}
          className="flex items-center gap-2 rounded-md border border-border bg-secondary px-4 py-2 text-sm text-secondary-foreground transition-colors hover:bg-secondary/70"
        >
          <Eraser className="size-4" aria-hidden="true" />
          Clear Wipe Error
        </button>
      </div>

      <section>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          История вайпов
        </h2>
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-border bg-card text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                <th className="px-4 py-3 font-medium">Дата и время</th>
                <th className="px-4 py-3 font-medium">Тип</th>
                <th className="px-4 py-3 font-medium">Карта (seed)</th>
                <th className="px-4 py-3 font-medium">Размер</th>
                <th className="px-4 py-3 font-medium">Статус</th>
              </tr>
            </thead>
            <tbody>
              {history.map((w, i) => (
                <tr
                  key={i}
                  className="border-b border-border last:border-0 hover:bg-card"
                >
                  <td className="px-4 py-3 text-muted-foreground">{w.date}</td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        w.type === 'Full'
                          ? 'rounded-full bg-destructive/15 px-2.5 py-0.5 text-xs font-medium text-destructive'
                          : 'rounded-full bg-primary/15 px-2.5 py-0.5 text-xs font-medium text-primary'
                      }
                    >
                      {w.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono tabular-nums">{w.seed}</td>
                  <td className="px-4 py-3 font-mono text-muted-foreground">
                    {w.size}
                  </td>
                  <td className="px-4 py-3">
                    {w.success ? (
                      <span className="text-xs font-medium text-success">
                        Success
                      </span>
                    ) : (
                      <span className="text-xs font-medium text-destructive">
                        Failed
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
