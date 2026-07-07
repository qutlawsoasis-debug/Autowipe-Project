'use client'

import { cn } from '@/lib/utils'

export function StatusDot({
  status,
  className,
}: {
  status: 'online' | 'warning' | 'offline'
  className?: string
}) {
  return (
    <span className="relative flex size-2" aria-hidden="true">
      {status === 'online' && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-40" />
      )}
      <span
        className={cn(
          'relative inline-flex size-2 rounded-full',
          status === 'online' && 'bg-success',
          status === 'warning' && 'bg-warning',
          status === 'offline' && 'bg-destructive',
          className
        )}
      />
    </span>
  )
}

const services: { name: string; status: 'online' | 'warning' | 'offline' }[] = [
  { name: 'Backend', status: 'online' },
  { name: 'Discord', status: 'online' },
  { name: 'Pterodactyl', status: 'online' },
]

export function Header({ title }: { title: string }) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4 md:px-8">
      <h1 className="text-lg font-semibold text-balance md:text-xl">{title}</h1>
      <div className="flex flex-wrap items-center gap-2">
        {services.map((s) => (
          <div
            key={s.name}
            className="flex items-center gap-2 rounded-md border border-border bg-card px-2.5 py-1.5 text-xs text-muted-foreground"
          >
            <StatusDot status={s.status} />
            <span>{s.name}</span>
          </div>
        ))}
      </div>
    </header>
  )
}
