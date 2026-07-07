'use client'

import { useEffect, useState } from 'react'
import { StatusDot } from './header'
import { cn } from '@/lib/utils'
import { AlertTriangle, Clock, RotateCw } from 'lucide-react'

export function OverviewTab({
  maps,
  systemState,
}: {
  maps: any[]
  systemState: any
}) {
  const [timeLeftStr, setTimeLeftStr] = useState('Загрузка...')
  const [actionLoading, setActionLoading] = useState(false)
  const nextWipeAt = systemState?.schedule?.next_wipe_at || 'Не запланирован'

  useEffect(() => {
    if (systemState?.schedule?.next_wipe_at) {
      const calculateTimeLeft = () => {
        try {
          const target = new Date(systemState.schedule.next_wipe_at)
          const diff = target.getTime() - Date.now()
          if (diff <= 0) {
            setTimeLeftStr('00:00:00')
            return
          }
          const h = Math.floor(diff / 3600000)
          const m = Math.floor((diff % 3600000) / 60000)
          const s = Math.floor((diff % 60000) / 1000)
          setTimeLeftStr(
            `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
          )
        } catch (e) {
          setTimeLeftStr('Запланирован')
        }
      }
      calculateTimeLeft()
      const timer = setInterval(calculateTimeLeft, 1000)
      return () => clearInterval(timer)
    } else {
      setTimeLeftStr('Не запланирован')
    }
  }, [systemState])

  const handleAction = async (action: string) => {
    try {
      setActionLoading(true)
      const r = await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      const res = await r.json()
      alert(res.message || 'Действие выполнено')
      window.location.reload()
    } catch (err) {
      alert('Ошибка связи с сервером при отправке команды.')
    } finally {
      setActionLoading(false)
    }
  }

  const ready = maps.filter((mp) => mp.status === 'ready').length
  const generating = maps.length - ready
  const genPercent = maps.length > 0 ? Math.round((ready / maps.length) * 100) : 0

  const activeVote = systemState?.vote ? 'Да' : 'Нет'
  const activeVoteSub = systemState?.vote
    ? `${Object.keys(systemState.vote.user_votes || {}).length} проголосовали`
    : 'Голосование не начато'

  const serverStatus = systemState?.health?.pterodactyl === 'ok' ? 'Online' : 'Offline'

  const stats = [
    { label: 'Карт в пуле', value: String(maps.length), sub: `Из ${systemState?.generation?.target || 10} целевых` },
    { label: 'Генерация', value: `${genPercent}%`, sub: `${generating} в процессе` },
    { label: 'Голосование', value: activeVote, sub: activeVoteSub },
    { label: 'Сервер', value: serverStatus, sub: serverStatus === 'Online' ? 'Подключен' : 'Недоступен', accent: serverStatus === 'Online' },
  ]

  const healthItems = [
    { label: 'Backend Server', status: systemState?.health?.backend === 'ok' ? ('online' as const) : ('offline' as const) },
    { label: 'Discord Bot API', status: systemState?.health?.discord === 'ok' ? ('online' as const) : ('offline' as const) },
    { label: 'Pterodactyl Panel', status: systemState?.health?.pterodactyl === 'ok' ? ('online' as const) : ('offline' as const) },
    { label: 'RustMaps API Key', status: systemState?.health?.rustmaps === 'ok' ? ('online' as const) : ('offline' as const) },
  ]

  const logsList: string[] = systemState?.logs || [
    'Загрузка системных логов бэкенда...'
  ]

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Alerts */}
      <div className="flex flex-col gap-4">
        {systemState?.wipe_error && (
          <div className="rounded-2xl ring-1 ring-destructive/30 bg-destructive/5 p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-6 backdrop-blur-md">
            <div className="flex items-start gap-4">
              <div className="p-2 rounded-full bg-destructive/10">
                <AlertTriangle className="size-5 text-destructive shrink-0" />
              </div>
              <div className="flex flex-col gap-1.5">
                <span className="text-sm font-semibold tracking-tight text-destructive">Ошибка Pterodactyl Вайпа</span>
                <span className="text-sm text-foreground/80 font-mono leading-relaxed">{systemState.wipe_error}</span>
              </div>
            </div>
            <button
              type="button"
              disabled={actionLoading}
              onClick={() => handleAction('clear_wipe_error')}
              className="rounded-xl ring-1 ring-white/10 bg-white/5 px-5 py-2.5 text-sm font-medium text-foreground hover:bg-destructive hover:text-white transition-all shadow-sm"
            >
              Сбросить
            </button>
          </div>
        )}

        {systemState?.scheduled_wipe_requested_at && (
          <div className="rounded-2xl ring-1 ring-warning/30 bg-warning/5 p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-6 backdrop-blur-md">
            <div className="flex items-start gap-4">
              <div className="p-2 rounded-full bg-warning/10">
                <Clock className="size-5 text-warning shrink-0" />
              </div>
              <div className="flex flex-col gap-1.5">
                <span className="text-sm font-semibold tracking-tight text-warning">Экстренный вайп в очереди</span>
                <span className="text-sm text-foreground/80 leading-relaxed">
                  Запрошен {systemState.scheduled_wipe_mode === 'full' ? 'полный' : 'обычный'} вайп в {new Date(systemState.scheduled_wipe_requested_at).toLocaleString()}
                </span>
              </div>
            </div>
            <button
              type="button"
              disabled={actionLoading}
              onClick={() => handleAction('clear_scheduled_wipe')}
              className="rounded-xl ring-1 ring-white/10 bg-white/5 px-5 py-2.5 text-sm font-medium text-foreground hover:bg-warning hover:text-black transition-all shadow-sm"
            >
              Отменить запуск
            </button>
          </div>
        )}
      </div>

      {/* Countdown Hero Section */}
      <section className="relative overflow-hidden rounded-3xl bg-white/[0.02] ring-1 ring-white/10 px-8 py-10 text-center shadow-2xl shadow-black/50 backdrop-blur-xl">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent"
        />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent opacity-50" />
        
        <div className="relative z-10 flex flex-col items-center justify-center">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground font-medium">
            Следующий вайп
          </div>
          <div className="mt-4 font-mono text-6xl tracking-tighter tabular-nums text-foreground md:text-8xl font-bold bg-gradient-to-b from-white to-white/60 bg-clip-text text-transparent drop-shadow-sm">
            {timeLeftStr}
          </div>
          {nextWipeAt !== 'Не запланирован' && (
            <div className="mt-5 px-4 py-1.5 rounded-full ring-1 ring-white/10 bg-white/5 text-sm font-medium text-muted-foreground backdrop-blur-md">
              Запланировано на {nextWipeAt}
            </div>
          )}
        </div>
      </section>

      {/* Stats Grid */}
      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="group rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-5 transition-all hover:ring-primary/40 hover:bg-white/[0.04] shadow-lg shadow-black/20"
          >
            <div className="text-xs font-medium text-muted-foreground">
              {stat.label}
            </div>
            <div
              className={cn(
                'mt-4 font-mono text-3xl tracking-tight tabular-nums font-semibold',
                stat.accent ? 'text-success drop-shadow-[0_0_8px_rgba(var(--success),0.5)]' : 'text-foreground'
              )}
            >
              {stat.value}
            </div>
            <div className="mt-2 text-sm text-muted-foreground/70 font-medium">{stat.sub}</div>
          </div>
        ))}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Health */}
        <section className="flex flex-col gap-4 h-full">
          <h2 className="text-lg font-semibold tracking-tight text-foreground flex items-center gap-2">
            Состояние API
          </h2>
          <div className="flex flex-col h-full rounded-2xl bg-white/[0.02] ring-1 ring-white/5 overflow-hidden backdrop-blur-md shadow-lg shadow-black/20">
            {healthItems.map((item, i) => (
              <div
                key={item.label}
                className={cn(
                  "flex-1 flex items-center justify-between px-6 py-4 transition-colors hover:bg-white/[0.02]",
                  i !== healthItems.length - 1 && "border-b border-white/5"
                )}
              >
                <span className="text-sm font-medium text-foreground/90">{item.label}</span>
                <span className={cn("flex items-center gap-2.5 text-sm font-semibold tracking-tight", item.status === 'online' ? 'text-success' : 'text-destructive')}>
                  <StatusDot status={item.status} />
                  {item.status === 'online' ? 'Online' : 'Offline'}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Logs */}
        <section className="flex flex-col gap-4 h-full">
          <h2 className="text-lg font-semibold tracking-tight text-foreground">
            Системный лог
          </h2>
          <div className="flex flex-col h-full rounded-2xl ring-1 ring-white/5 bg-[#0a0a0a] overflow-hidden shadow-lg shadow-black/40">
            <div className="flex items-center gap-3 border-b border-white/5 px-5 py-3.5 bg-white/[0.02]">
              <div className="flex gap-1.5">
                <span className="size-3 rounded-full bg-white/20" />
                <span className="size-3 rounded-full bg-white/20" />
                <span className="size-3 rounded-full bg-white/20" />
              </div>
              <span className="font-mono text-xs font-medium text-muted-foreground/80">
                autowipe.log
              </span>
            </div>
            <div className="flex flex-col gap-2 p-5 font-mono text-[13px] leading-relaxed h-[200px] overflow-y-auto">
              {logsList.map((logLine, i) => {
                const isErr = logLine.toLowerCase().includes('err') || logLine.toLowerCase().includes('fail')
                const isWarn = logLine.toLowerCase().includes('warn')
                const isOk = logLine.toLowerCase().includes('ok') || logLine.toLowerCase().includes('succ')
                
                return (
                  <div key={i} className="flex gap-3">
                    <span
                      className={cn(
                        "opacity-90",
                        isOk && 'text-success',
                        isWarn && 'text-warning',
                        isErr && 'text-destructive',
                        !isOk && !isWarn && !isErr && 'text-foreground/70'
                      )}
                    >
                      {logLine}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
