'use client'

import { useEffect, useRef } from 'react'

export interface ConfirmState {
  title: string
  message: string
  destructive?: boolean
  onConfirm: () => void
}

export function ConfirmDialog({
  state,
  onClose,
}: {
  state: ConfirmState | null
  onClose: () => void
}) {
  const confirmRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!state) return
    confirmRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [state, onClose])

  if (!state) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <button
        type="button"
        aria-label="Закрыть"
        onClick={onClose}
        className="absolute inset-0 bg-background/70 backdrop-blur-sm"
      />
      <div className="relative w-full max-w-sm rounded-lg border border-border bg-card p-6 shadow-xl">
        <h2 id="confirm-title" className="text-base font-semibold">
          {state.title}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {state.message}
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-border bg-secondary px-4 py-2 text-sm text-secondary-foreground transition-colors hover:bg-secondary/70"
          >
            Отмена
          </button>
          <button
            ref={confirmRef}
            type="button"
            onClick={() => {
              state.onConfirm()
              onClose()
            }}
            className={
              state.destructive
                ? 'rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground transition-opacity hover:opacity-90'
                : 'rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90'
            }
          >
            Подтвердить
          </button>
        </div>
      </div>
    </div>
  )
}
