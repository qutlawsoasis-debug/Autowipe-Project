'use client'

import { useState, useEffect } from 'react'
import { Save, Upload, Loader2, RefreshCw } from 'lucide-react'

export function SettingsTab({
  systemState,
  onSaveSettings,
}: {
  systemState: any
  onSaveSettings: (settings: any) => void
}) {
  // Discord & Pterodactyl
  const [discordToken, setDiscordToken] = useState('')
  const [discordChannelId, setDiscordChannelId] = useState('')
  const [discordEmoji, setDiscordEmoji] = useState('✅')
  const [pteroUrl, setPteroUrl] = useState('')
  const [pteroId, setPteroId] = useState('')
  const [pteroKey, setPteroKey] = useState('')

  // RustMaps
  const [rustmapsKey, setRustmapsKey] = useState('')
  const [rustmapsSize, setRustmapsSize] = useState(3750)
  const [rustmapsPoolSize, setRustmapsPoolSize] = useState(5)

  // Schedule
  const [timezone, setTimezone] = useState('UTC')
  const [wipeTime, setWipeTime] = useState('11:55')
  const [ordinaryInterval, setOrdinaryInterval] = useState(3)
  const [fullInterval, setFullInterval] = useState(6)
  const [votePublishBefore, setVotePublishBefore] = useState(60)
  const [voteDuration, setVoteDuration] = useState(60)
  const [autoPublishVote, setAutoPublishVote] = useState(true)
  // Advanced schedule keys
  const [ordinaryWipeCron, setOrdinaryWipeCron] = useState('')
  const [fullWipeCron, setFullWipeCron] = useState('')
  const [ordinaryWipeStartDate, setOrdinaryWipeStartDate] = useState('')
  const [fullWipeStartDate, setFullWipeStartDate] = useState('')
  const [voteCloseMode, setVoteCloseMode] = useState('finalize_before_wipe')
  const [publishWhenPoolReadyMin, setPublishWhenPoolReadyMin] = useState(3)

  // Notifications (Branding)
  const [serverName, setServerName] = useState('')
  const [serverBrand, setServerBrand] = useState('')
  const [logoUrl, setLogoUrl] = useState('')
  const [connectAddress, setConnectAddress] = useState('')
  const [notifyEnabled, setNotifyEnabled] = useState(false)
  const [logoUploading, setLogoUploading] = useState(false)

  // Commits
  const [commitsEnabled, setCommitsEnabled] = useState(false)
  const [commitsWebhook, setCommitsWebhook] = useState('')
  const [commitsLabel, setCommitsLabel] = useState('main')
  const [commitsPing, setCommitsPing] = useState('')
  const [commitsColor, setCommitsColor] = useState('#22dd6a')

  // Connection testing states
  const [testLoading, setTestLoading] = useState<Record<string, boolean>>({})

  useEffect(() => {
    const settings = systemState?.settings
    if (settings) {
      // Discord
      setDiscordToken(settings.discord?.token || '')
      setDiscordChannelId(settings.discord?.channel_id || '')
      setDiscordEmoji(settings.discord?.reaction_emoji || '✅')

      // Pterodactyl
      setPteroUrl(settings.pterodactyl?.panel_url || '')
      setPteroId(settings.pterodactyl?.server_id || '')
      setPteroKey(settings.pterodactyl?.api_key || '')

      // RustMaps
      setRustmapsKey(settings.rustmaps?.api_key || '')
      setRustmapsSize(settings.rustmaps?.size || 3750)
      setRustmapsPoolSize(settings.rustmaps?.target_pool_size || 5)

      // Schedule
      const sch = settings.schedule || {}
      setTimezone(sch.timezone || 'UTC')
      setWipeTime(sch.wipe_time || '11:55')
      setOrdinaryInterval(sch.ordinary_interval_days ?? 3)
      setFullInterval(sch.full_interval_days ?? 6)
      setVotePublishBefore(sch.vote_publish_before_minutes ?? 60)
      setVoteDuration(sch.vote_duration_minutes ?? 60)
      setAutoPublishVote(sch.auto_publish_vote ?? true)
      // Advanced
      setOrdinaryWipeCron(sch.ordinary_wipe_cron || '')
      setFullWipeCron(sch.full_wipe_cron || '')
      setOrdinaryWipeStartDate(sch.ordinary_wipe_start_date || '')
      setFullWipeStartDate(sch.full_wipe_start_date || '')
      setVoteCloseMode(sch.vote_close_mode || 'finalize_before_wipe')
      setPublishWhenPoolReadyMin(sch.publish_when_pool_ready_min ?? 3)

      // Notifications
      const not = settings.notifications || {}
      setServerName(not.server_name || '')
      setServerBrand(not.server_brand || '')
      setLogoUrl(not.logo_url || '')
      setConnectAddress(not.connect_address || '')
      setNotifyEnabled(not.enabled ?? false)

      // Commits
      const com = settings.commits || {}
      setCommitsEnabled(com.enabled ?? false)
      setCommitsWebhook(com.webhook_url || '')
      setCommitsLabel(com.channel_label || 'main')
      setCommitsPing(com.ping_target || '')
      setCommitsColor(com.color || '#22dd6a')
    }
  }, [systemState])

  const handleTestConnection = async (action: string) => {
    try {
      setTestLoading((prev) => ({ ...prev, [action]: true }))
      const r = await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      const res = await r.json()
      alert(res.message || 'Действие выполнено успешно')
    } catch (err) {
      alert('Ошибка при тестировании подключения бэкенда')
    } finally {
      setTestLoading((prev) => ({ ...prev, [action]: false }))
    }
  }

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('logo', file)

    try {
      setLogoUploading(true)
      const r = await fetch('/api/upload_logo', {
        method: 'POST',
        body: formData,
      })
      const res = await r.json()
      if (res.ok) {
        setLogoUrl('/dashboard-logo')
        alert('Логотип успешно загружен на сервер!')
      } else {
        alert(res.message || 'Ошибка загрузки логотипа')
      }
    } catch (err) {
      alert('Ошибка соединения с сервером при загрузке')
    } finally {
      setLogoUploading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload = {
      discord: {
        token: discordToken,
        channel_id: discordChannelId,
        reaction_emoji: discordEmoji,
      },
      pterodactyl: {
        panel_url: pteroUrl,
        server_id: pteroId,
        api_key: pteroKey,
      },
      rustmaps: {
        api_key: rustmapsKey,
        size: Number(rustmapsSize),
        target_pool_size: Number(rustmapsPoolSize),
      },
      schedule: {
        ...systemState?.settings?.schedule,
        timezone,
        wipe_time: wipeTime,
        ordinary_interval_days: Number(ordinaryInterval),
        full_interval_days: Number(fullInterval),
        vote_publish_before_minutes: Number(votePublishBefore),
        vote_duration_minutes: Number(voteDuration),
        auto_publish_vote: autoPublishVote,
        ordinary_wipe_cron: ordinaryWipeCron,
        full_wipe_cron: fullWipeCron,
        ordinary_wipe_start_date: ordinaryWipeStartDate,
        full_wipe_start_date: fullWipeStartDate,
        vote_close_mode: voteCloseMode,
        publish_when_pool_ready_min: Number(publishWhenPoolReadyMin),
      },
      notifications: {
        ...systemState?.settings?.notifications,
        server_name: serverName,
        server_brand: serverBrand,
        logo_url: logoUrl,
        connect_address: connectAddress,
        enabled: notifyEnabled,
      },
      commits: {
        ...systemState?.settings?.commits,
        enabled: commitsEnabled,
        webhook_url: commitsWebhook,
        channel_label: commitsLabel,
        ping_target: commitsPing,
        color: commitsColor,
      },
    }
    onSaveSettings(payload)
  }

  return (
    <form className="flex w-full flex-col gap-10" onSubmit={handleSubmit}>
      {/* Top action header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            Конфигурация системы
          </h2>
          <p className="text-sm text-muted-foreground mt-1">Управление токенами, ключами API и параметрами среды.</p>
        </div>
        <button
          type="submit"
          className="flex items-center gap-2 rounded-xl ring-1 ring-primary/30 bg-primary/10 px-6 py-2.5 text-sm font-semibold text-primary transition-all hover:bg-primary hover:text-white hover:ring-primary hover:drop-shadow-[0_0_12px_rgba(var(--primary),0.4)] shadow-sm shrink-0 h-fit"
        >
          <Save className="size-4" aria-hidden="true" />
          Сохранить все настройки
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 items-start">
        {/* Левая колонка */}
        <div className="flex flex-col gap-8">
          {/* Discord настройки */}
          <section className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-8 shadow-lg shadow-black/20 backdrop-blur-md">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-semibold tracking-tight text-foreground">
                Discord Бот
              </h2>
              <button
                type="button"
                disabled={testLoading['test_discord']}
                onClick={() => handleTestConnection('test_discord')}
                className="text-[13px] font-medium text-primary hover:text-primary/80 transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                {testLoading['test_discord'] ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="size-3.5" />
                )}
                Проверить бота
              </button>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="flex flex-col gap-2 sm:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">Токен бота</label>
                <input
                  type="password"
                  value={discordToken}
                  onChange={(e) => setDiscordToken(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-sm text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">ID Канала для голосования</label>
                <input
                  type="text"
                  value={discordChannelId}
                  onChange={(e) => setDiscordChannelId(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-sm text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Эмодзи для реакций</label>
                <input
                  type="text"
                  value={discordEmoji}
                  onChange={(e) => setDiscordEmoji(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-sm text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
            </div>
          </section>

          {/* RustMaps API */}
          <section className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-8 shadow-lg shadow-black/20 backdrop-blur-md">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-semibold tracking-tight text-foreground">
                RustMaps API
              </h2>
              <button
                type="button"
                disabled={testLoading['test_rustmaps']}
                onClick={() => handleTestConnection('test_rustmaps')}
                className="text-[13px] font-medium text-primary hover:text-primary/80 transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                {testLoading['test_rustmaps'] ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="size-3.5" />
                )}
                Проверить API ключ
              </button>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="flex flex-col gap-2 sm:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">API Ключ</label>
                <input
                  type="password"
                  value={rustmapsKey}
                  onChange={(e) => setRustmapsKey(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-sm text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Размер карты по умолчанию</label>
                <input
                  type="number"
                  value={rustmapsSize}
                  onChange={(e) => setRustmapsSize(Number(e.target.value))}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-sm text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Целевой размер пула</label>
                <input
                  type="number"
                  value={rustmapsPoolSize}
                  onChange={(e) => setRustmapsPoolSize(Number(e.target.value))}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-sm text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
            </div>
          </section>

          {/* Брендинг и логотипы */}
          <section className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-8 shadow-lg shadow-black/20 backdrop-blur-md">
            <h2 className="mb-6 text-sm font-semibold tracking-tight text-foreground">
              Сервер и Брендинг
            </h2>
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="flex items-center gap-3 sm:col-span-2 mb-2">
                <input
                  id="notifyEnabled"
                  type="checkbox"
                  checked={notifyEnabled}
                  onChange={(e) => setNotifyEnabled(e.target.checked)}
                  className="size-4.5 rounded ring-1 ring-white/10 bg-black/50 accent-primary cursor-pointer transition-all"
                />
                <label htmlFor="notifyEnabled" className="text-sm font-medium text-foreground cursor-pointer select-none">
                  Включить вебхуки уведомлений
                </label>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Имя сервера</label>
                <input
                  type="text"
                  value={serverName}
                  onChange={(e) => setServerName(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Бренд сервера</label>
                <input
                  type="text"
                  value={serverBrand}
                  onChange={(e) => setServerBrand(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2 sm:col-span-2 mt-2">
                <label className="text-xs font-semibold text-muted-foreground">Логотип сервера (файл)</label>
                <label className="flex items-center gap-2 rounded-xl ring-1 ring-white/10 bg-white/5 px-4 py-3 text-[13px] font-medium text-foreground hover:bg-white/10 cursor-pointer transition-colors w-full justify-center shadow-sm">
                  {logoUploading ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Upload className="size-4" />
                  )}
                  Загрузить новый логотип (.png, .jpg, .webp)
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleLogoUpload}
                    disabled={logoUploading}
                    className="hidden"
                  />
                </label>
              </div>
              <div className="flex flex-col gap-2 sm:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">Ссылка на логотип (Logo URL)</label>
                <input
                  type="text"
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2 sm:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">Адрес подключения (play.xxx.ru:28015)</label>
                <input
                  type="text"
                  value={connectAddress}
                  onChange={(e) => setConnectAddress(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
            </div>
          </section>
        </div>

        {/* Правая колонка */}
        <div className="flex flex-col gap-8">
          {/* Pterodactyl панель */}
          <section className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-8 shadow-lg shadow-black/20 backdrop-blur-md">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-semibold tracking-tight text-foreground">
                Pterodactyl Панель
              </h2>
              <button
                type="button"
                disabled={testLoading['test_pterodactyl']}
                onClick={() => handleTestConnection('test_pterodactyl')}
                className="text-[13px] font-medium text-primary hover:text-primary/80 transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                {testLoading['test_pterodactyl'] ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="size-3.5" />
                )}
                Проверить панель
              </button>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="flex flex-col gap-2 sm:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">URL Панели</label>
                <input
                  type="text"
                  value={pteroUrl}
                  onChange={(e) => setPteroUrl(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">ID Сервера</label>
                <input
                  type="text"
                  value={pteroId}
                  onChange={(e) => setPteroId(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">API Ключ клиента</label>
                <input
                  type="password"
                  value={pteroKey}
                  onChange={(e) => setPteroKey(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
            </div>
          </section>

          {/* Advanced Schedule */}
          <section className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-8 shadow-lg shadow-black/20 backdrop-blur-md">
            <h2 className="mb-6 text-sm font-semibold tracking-tight text-foreground">
              Расписание и Автоматизация
            </h2>
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Часовой пояс</label>
                <input
                  type="text"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Время вайпа (HH:MM)</label>
                <input
                  type="text"
                  value={wipeTime}
                  onChange={(e) => setWipeTime(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Интервал обычного вайпа (дней)</label>
                <input
                  type="number"
                  value={ordinaryInterval}
                  onChange={(e) => setOrdinaryInterval(Number(e.target.value))}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Интервал полного вайпа (дней)</label>
                <input
                  type="number"
                  value={fullInterval}
                  onChange={(e) => setFullInterval(Number(e.target.value))}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Публикация голосования (минут до вайпа)</label>
                <input
                  type="number"
                  value={votePublishBefore}
                  onChange={(e) => setVotePublishBefore(Number(e.target.value))}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Длительность голосования (минут)</label>
                <input
                  type="number"
                  value={voteDuration}
                  onChange={(e) => setVoteDuration(Number(e.target.value))}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>

              {/* Cron */}
              <div className="flex flex-col gap-2 mt-4">
                <label className="text-xs font-semibold text-muted-foreground">Cron обычного вайпа (опционально)</label>
                <input
                  type="text"
                  placeholder="* * * * *"
                  value={ordinaryWipeCron}
                  onChange={(e) => setOrdinaryWipeCron(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner placeholder:text-muted-foreground/40"
                />
              </div>
              <div className="flex flex-col gap-2 mt-4">
                <label className="text-xs font-semibold text-muted-foreground">Cron полного вайпа (опционально)</label>
                <input
                  type="text"
                  placeholder="* * * * *"
                  value={fullWipeCron}
                  onChange={(e) => setFullWipeCron(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner placeholder:text-muted-foreground/40"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Дата начала обычного вайпа</label>
                <input
                  type="text"
                  placeholder="ГГГГ-ММ-ДД"
                  value={ordinaryWipeStartDate}
                  onChange={(e) => setOrdinaryWipeStartDate(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner placeholder:text-muted-foreground/40"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Дата начала полного вайпа</label>
                <input
                  type="text"
                  placeholder="ГГГГ-ММ-ДД"
                  value={fullWipeStartDate}
                  onChange={(e) => setFullWipeStartDate(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner placeholder:text-muted-foreground/40"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Режим закрытия голосования</label>
                <select
                  value={voteCloseMode}
                  onChange={(e) => setVoteCloseMode(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner cursor-pointer"
                >
                  <option value="finalize_before_wipe">Завершать перед вайпом</option>
                  <option value="keep_open">Оставлять открытым</option>
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Минимум готовых карт в пуле</label>
                <input
                  type="number"
                  value={publishWhenPoolReadyMin}
                  onChange={(e) => setPublishWhenPoolReadyMin(Number(e.target.value))}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>

              <div className="flex items-center gap-3 sm:col-span-2 mt-4">
                <input
                  id="autoPublishVote"
                  type="checkbox"
                  checked={autoPublishVote}
                  onChange={(e) => setAutoPublishVote(e.target.checked)}
                  className="size-4.5 rounded ring-1 ring-white/10 bg-black/50 accent-primary cursor-pointer transition-all"
                />
                <label htmlFor="autoPublishVote" className="text-sm font-medium text-foreground cursor-pointer select-none">
                  Автоматически публиковать голосование
                </label>
              </div>
            </div>
          </section>

          {/* Discord логирование коммитов */}
          <section className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-8 shadow-lg shadow-black/20 backdrop-blur-md">
            <h2 className="mb-6 text-sm font-semibold tracking-tight text-foreground">
              Логирование коммитов в Discord
            </h2>
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="flex items-center gap-3 sm:col-span-2 mb-2">
                <input
                  id="commitsEnabled"
                  type="checkbox"
                  checked={commitsEnabled}
                  onChange={(e) => setCommitsEnabled(e.target.checked)}
                  className="size-4.5 rounded ring-1 ring-white/10 bg-black/50 accent-primary cursor-pointer transition-all"
                />
                <label htmlFor="commitsEnabled" className="text-sm font-medium text-foreground cursor-pointer select-none">
                  Включить логирование коммитов
                </label>
              </div>
              <div className="flex flex-col gap-2 sm:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">URL Вебхука Discord</label>
                <input
                  type="text"
                  value={commitsWebhook}
                  onChange={(e) => setCommitsWebhook(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Лейбл канала (например, main)</label>
                <input
                  type="text"
                  value={commitsLabel}
                  onChange={(e) => setCommitsLabel(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Цвет эмбеда (Hex)</label>
                <input
                  type="text"
                  value={commitsColor}
                  onChange={(e) => setCommitsColor(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
              <div className="flex flex-col gap-2 sm:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">Пинг цель (например, @everyone)</label>
                <input
                  type="text"
                  value={commitsPing}
                  onChange={(e) => setCommitsPing(e.target.value)}
                  className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
                />
              </div>
            </div>
          </section>
        </div>
      </div>
    </form>
  )
}
