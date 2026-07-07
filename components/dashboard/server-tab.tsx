'use client'

import { useState } from 'react'
import { Play, Square, RotateCw, Users, ShieldAlert, Loader2 } from 'lucide-react'
import { StatusDot } from './header'
import { OnlineChart } from './online-chart'

export function ServerTab({
  systemState,
  onStart,
  onStop,
  onRestart,
}: {
  systemState: any
  onStart: () => void
  onStop: () => void
  onRestart: () => void
}) {
  const isOnline = systemState?.health?.pterodactyl === 'ok'
  const [wipeActionLoading, setWipeActionLoading] = useState(false)
  const [unlockWipe, setUnlockWipe] = useState(false)

  // Try reading player count from Pterodactyl state if available
  const pteroData = systemState?.pterodactyl_server_details
  const currentPlayers = pteroData?.players_current ?? (isOnline ? 189 : 0)
  const maxPlayers = pteroData?.players_max ?? 256
  const fillPercent = maxPlayers > 0 ? Math.round((currentPlayers / maxPlayers) * 100) : 0

  const handleForceWipe = async (action: string) => {
    if (!unlockWipe) return
    const modeName = action === 'force_full_wipe' ? 'ПОЛНЫЙ (с чертежами)' : 'ОБЫЧНЫЙ'
    const confirm = window.confirm(`Вы подтверждаете немедленный запуск внеочередного вайпа? Тип вайпа: ${modeName}.\nСервер будет временно остановлен, файлы удалены, а затем сгенерирована новая карта.`)
    if (!confirm) return

    try {
      setWipeActionLoading(true)
      const r = await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      const res = await r.json()
      alert(res.message || 'Вайп успешно запущен в фоновом режиме.')
      setUnlockWipe(false)
    } catch (err) {
      alert('Ошибка при запуске экстренного вайпа на бэкенде.')
    } finally {
      setWipeActionLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-10 w-full">
      {/* Status grids */}
      <section className="grid gap-6 sm:grid-cols-2">
        <div className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-6 shadow-lg shadow-black/20 backdrop-blur-md">
          <div className="text-xs font-medium tracking-wider text-muted-foreground">
            Текущий статус (Pterodactyl)
          </div>
          <div className="mt-4 flex items-center gap-3">
            <StatusDot status={isOnline ? 'online' : 'offline'} />
            <span className={`font-mono text-3xl font-semibold tracking-tight ${isOnline ? 'text-success drop-shadow-[0_0_8px_rgba(var(--success),0.5)]' : 'text-destructive'}`}>
              {isOnline ? 'Online' : 'Offline'}
            </span>
          </div>
          <div className="mt-2 text-sm text-muted-foreground/70 font-medium">
            {isOnline ? 'Подключение установлено' : 'Подключение отсутствует'}
          </div>
        </div>
        
        <div className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-6 shadow-lg shadow-black/20 backdrop-blur-md">
          <div className="text-xs font-medium tracking-wider text-muted-foreground">
            Игроки онлайн
          </div>
          <div className="mt-4 flex items-center gap-3">
            <Users className="size-6 text-primary drop-shadow-[0_0_8px_rgba(var(--primary),0.5)]" aria-hidden="true" />
            <span className="font-mono text-3xl font-semibold tabular-nums tracking-tight text-foreground">
              {currentPlayers}<span className="text-muted-foreground/50 font-medium">/{maxPlayers}</span>
            </span>
          </div>
          <div className="mt-5 h-2 overflow-hidden rounded-full bg-white/5 ring-1 ring-inset ring-white/10">
            <div
              className="h-full rounded-full bg-primary drop-shadow-[0_0_8px_rgba(var(--primary),0.6)]"
              style={{ width: `${fillPercent}%` }}
              role="progressbar"
              aria-valuenow={currentPlayers}
              aria-valuemin={0}
              aria-valuemax={maxPlayers}
              aria-label="Заполненность сервера"
            />
          </div>
        </div>
      </section>

      {/* Online Chart */}
      <section className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-6 shadow-lg shadow-black/20 backdrop-blur-md">
        <OnlineChart />
      </section>

      {/* Pterodactyl Basic Controls */}
      <section className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-6 shadow-lg shadow-black/20 backdrop-blur-md">
        <h2 className="mb-6 text-sm font-semibold tracking-tight text-foreground">
          Управление питанием хостинга
        </h2>
        <div className="flex flex-wrap gap-4">
          <button
            type="button"
            onClick={onStart}
            className="flex items-center gap-2.5 rounded-xl ring-1 ring-success/30 bg-success/10 px-6 py-3 text-sm font-semibold text-success transition-all hover:bg-success hover:text-white hover:ring-success hover:drop-shadow-[0_0_12px_rgba(var(--success),0.4)]"
          >
            <Play className="size-4" aria-hidden="true" />
            Включить сервер
          </button>
          <button
            type="button"
            onClick={onStop}
            className="flex items-center gap-2.5 rounded-xl ring-1 ring-warning/30 bg-warning/10 px-6 py-3 text-sm font-semibold text-warning transition-all hover:bg-warning hover:text-black hover:ring-warning hover:drop-shadow-[0_0_12px_rgba(var(--warning),0.4)]"
          >
            <Square className="size-4" aria-hidden="true" />
            Остановить сервер
          </button>
          <button
            type="button"
            onClick={onRestart}
            className="flex items-center gap-2.5 rounded-xl ring-1 ring-white/10 bg-white/5 px-6 py-3 text-sm font-medium text-foreground transition-all hover:bg-white/10 hover:ring-white/20"
          >
            <RotateCw className="size-4" aria-hidden="true" />
            Перезагрузить сервер
          </button>
        </div>
      </section>

      {/* Emergency Manual Wipes Section */}
      <section className="rounded-2xl bg-destructive/[0.02] ring-1 ring-destructive/20 p-6 shadow-lg shadow-black/20 backdrop-blur-md relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-destructive/5 via-transparent to-transparent opacity-50" />
        <div className="relative z-10">
          <h2 className="mb-6 text-sm font-semibold tracking-tight text-destructive flex items-center gap-2">
            <ShieldAlert className="size-4" />
            Экстренный запуск внеочередного вайпа
          </h2>
          <div className="flex flex-col gap-6">
            <div className="flex items-center gap-3">
              <input
                id="unlockWipe"
                type="checkbox"
                checked={unlockWipe}
                onChange={(e) => setUnlockWipe(e.target.checked)}
                className="size-4.5 rounded ring-1 ring-white/10 bg-black/50 accent-destructive cursor-pointer transition-all"
              />
              <label htmlFor="unlockWipe" className="text-sm font-medium text-muted-foreground cursor-pointer select-none">
                Я разблокирую ручной запуск вайпа и осознаю последствия
              </label>
            </div>
            
            <div className="flex flex-wrap gap-4">
              <button
                type="button"
                disabled={!unlockWipe || wipeActionLoading}
                onClick={() => handleForceWipe('force_ordinary_wipe')}
                className={`flex items-center gap-2.5 rounded-xl ring-1 px-6 py-3 text-sm font-semibold transition-all ${
                  unlockWipe
                    ? 'ring-warning/30 bg-warning/10 text-warning hover:bg-warning hover:text-black hover:ring-warning hover:drop-shadow-[0_0_12px_rgba(var(--warning),0.4)]'
                    : 'ring-white/5 bg-white/5 text-muted-foreground/30 cursor-not-allowed opacity-50'
                }`}
              >
                {wipeActionLoading ? <Loader2 className="size-4 animate-spin" /> : null}
                Запустить Обычный Вайп (Ordinary)
              </button>
              <button
                type="button"
                disabled={!unlockWipe || wipeActionLoading}
                onClick={() => handleForceWipe('force_full_wipe')}
                className={`flex items-center gap-2.5 rounded-xl ring-1 px-6 py-3 text-sm font-semibold transition-all ${
                  unlockWipe
                    ? 'ring-destructive/30 bg-destructive/10 text-destructive hover:bg-destructive hover:text-white hover:ring-destructive hover:drop-shadow-[0_0_12px_rgba(var(--destructive),0.4)]'
                    : 'ring-white/5 bg-white/5 text-muted-foreground/30 cursor-not-allowed opacity-50'
                }`}
              >
                {wipeActionLoading ? <Loader2 className="size-4 animate-spin" /> : null}
                Запустить Полный Вайп (Full / Blueprints)
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold tracking-tight text-foreground">
          Параметры панели
        </h2>
        <div className="flex flex-col rounded-2xl bg-white/[0.02] ring-1 ring-white/5 overflow-hidden backdrop-blur-md shadow-lg shadow-black/20">
          {[
            { label: 'Урл панели управления', value: systemState?.settings?.pterodactyl?.panel_url || 'https://panel.example.com' },
            { label: 'UUID сервера', value: systemState?.settings?.pterodactyl?.server_id || 'Не настроен' },
          ].map((row, i) => (
            <div
              key={row.label}
              className={`flex items-center justify-between px-6 py-5 transition-colors hover:bg-white/[0.02] ${i === 0 ? 'border-b border-white/5' : ''}`}
            >
              <span className="text-sm font-medium text-foreground/90">{row.label}</span>
              <span className="font-mono tabular-nums text-muted-foreground bg-black/40 px-3 py-1.5 rounded-lg ring-1 ring-inset ring-white/5 text-sm">{row.value}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
