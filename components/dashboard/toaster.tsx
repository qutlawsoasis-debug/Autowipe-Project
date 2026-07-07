'use client'

import { CheckCircle2, AlertTriangle } from 'lucide-react'

export interface Toast {
  id: number
  message: string
  type: 'success' | 'warning'
}

export function Toaster({ toasts }: { toasts: Toast[] }) {
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className="flex items-center gap-2.5 rounded-md border border-border bg-card px-4 py-3 text-sm shadow-lg animate-in slide-in-from-bottom-2 fade-in"
        >
          {t.type === 'success' ? (
            <CheckCircle2 className="size-4 text-success" aria-hidden="true" />
          ) : (
            <AlertTriangle className="size-4 text-warning" aria-hidden="true" />
          )}
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  )
}
