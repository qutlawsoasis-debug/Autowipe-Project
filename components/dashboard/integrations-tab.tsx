'use client'

import { useState, useEffect } from 'react'
import { Save, Info, CheckCircle, HelpCircle, Loader2, RefreshCw } from 'lucide-react'

export function IntegrationsTab({
  systemState,
  onSaveSettings,
}: {
  systemState: any
  onSaveSettings: (settings: any) => void
}) {
  const [webhookUrl, setWebhookUrl] = useState('')
  const [testLoading, setTestLoading] = useState(false)

  useEffect(() => {
    if (systemState?.settings?.notifications?.wipe_webhook_url) {
      setWebhookUrl(systemState.settings.notifications.wipe_webhook_url)
    }
  }, [systemState])

  const handleTestWebhook = async () => {
    try {
      setTestLoading(true)
      const r = await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'test_integrations' }),
      })
      const res = await r.json()
      alert(res.message || 'Тестовый сигнал отправлен в Discord.')
    } catch (err) {
      alert('Ошибка при отправке тестового сигнала.')
    } finally {
      setTestLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload = {
      notifications: {
        ...systemState?.settings?.notifications,
        wipe_webhook_url: webhookUrl,
      },
    }
    onSaveSettings(payload)
  }

  return (
    <form className="flex w-full flex-col gap-6" onSubmit={handleSubmit}>
      {/* Top action block */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          Внешние уведомления
        </h2>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={testLoading}
            onClick={handleTestWebhook}
            className="flex items-center gap-2 rounded-xl ring-1 ring-white/10 bg-white/5 px-5 py-2.5 text-sm font-medium text-foreground transition-all hover:bg-white/10 disabled:opacity-50"
          >
            {testLoading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4 text-muted-foreground" />
            )}
            Тестовое сообщение
          </button>
          <button
            type="submit"
            className="flex items-center gap-2 rounded-xl ring-1 ring-primary/30 bg-primary/10 px-6 py-2.5 text-sm font-semibold text-primary transition-all hover:bg-primary hover:text-white hover:ring-primary hover:drop-shadow-[0_0_12px_rgba(var(--primary),0.4)] shadow-sm"
          >
            <Save className="size-4" aria-hidden="true" />
            Сохранить интеграции
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 items-start">
        {/* Форма вебхука и предпросмотр */}
        <div className="xl:col-span-2 flex flex-col gap-8 w-full">
          {/* Webhook Input */}
          <div className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-8 shadow-lg shadow-black/20 backdrop-blur-md">
            <div className="flex flex-col gap-3">
              <label htmlFor="webhookUrl" className="text-sm font-medium text-foreground">
                Discord Webhook URL (Оповещения о вайпах)
              </label>
              <input
                id="webhookUrl"
                type="text"
                placeholder="https://discord.com/api/webhooks/..."
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="w-full max-w-xl rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-sm text-foreground placeholder:text-muted-foreground/40 focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
              />
            </div>
          </div>

          {/* Discord Embed Message Mockup */}
          <section className="w-full flex flex-col gap-3">
            <h3 className="text-sm font-medium text-muted-foreground px-2">
              Предпросмотр уведомления в Discord
            </h3>
            <div className="rounded-2xl border-none ring-1 ring-[#202225] bg-[#36393f] p-6 flex gap-4 font-sans select-none shadow-xl w-full text-left relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-20 pointer-events-none" />
              
              {/* Bot icon */}
              <div className="w-10 h-10 rounded-full bg-[#5865f2] flex items-center justify-center text-white font-bold text-sm shrink-0 shadow-md z-10 relative">
                GP
              </div>
              <div className="flex flex-col gap-1 w-full z-10 relative">
                {/* Bot name header */}
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white text-[15px] hover:underline cursor-pointer">Gothbreach Bot</span>
                  <span className="bg-[#5865f2] text-white text-[10px] font-bold px-1.5 py-0.5 rounded leading-none flex items-center h-4">БОТ</span>
                  <span className="text-[#72767d] text-xs font-medium ml-1">Сегодня, в 20:00</span>
                </div>
                {/* Embed body */}
                <div className="border-l-[4px] border-[#4fce74] bg-[#2f3136] px-4 py-4 flex flex-col gap-3 rounded-[4px] max-w-xl mt-1 shadow-sm">
                  <h4 className="font-bold text-white text-[15px]">🟢 Сервер успешно запущен!</h4>
                  <p className="text-[14px] text-[#dcddde] leading-snug">
                    Процедура автоматического вайпа успешно завершена. Сервер готов к игре и ждет бойцов!
                  </p>
                  
                  <div className="grid grid-cols-2 gap-x-4 gap-y-4 text-sm mt-2">
                    <div>
                      <div className="text-[#b9bbbe] text-[12px] font-bold mb-1">Адрес подключения</div>
                      <div className="text-[#00aff4] font-mono hover:underline cursor-pointer">connect play.gothbreach.ru:28015</div>
                    </div>
                    <div>
                      <div className="text-[#b9bbbe] text-[12px] font-bold mb-1">Тип вайпа</div>
                      <div className="text-[#dcddde]">Обычный (Сброс строений)</div>
                    </div>
                    <div className="col-span-2">
                      <div className="text-[#b9bbbe] text-[12px] font-bold mb-1">Информация о карте</div>
                      <div className="text-[#dcddde]">Procedural Map (размер 3750, seed 1489028)</div>
                    </div>
                  </div>

                  <div className="flex gap-2 mt-2 pt-4 border-t border-white/5">
                    <div className="bg-[#4fce74]/15 text-[#4fce74] px-4 py-2 rounded text-[14px] font-medium hover:bg-[#4fce74]/20 transition-colors cursor-pointer text-center w-auto">
                      Быстрое подключение
                    </div>
                    <div className="bg-[#4f545c] text-white px-4 py-2 rounded text-[14px] font-medium hover:bg-[#5d6269] transition-colors cursor-pointer text-center w-auto">
                      RustMaps Ссылка
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Документация / Справка */}
        <div className="xl:col-span-1 rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-8 flex flex-col gap-6 shadow-lg shadow-black/20 backdrop-blur-md">
          <h3 className="text-sm font-semibold tracking-tight text-primary flex items-center gap-2.5">
            <HelpCircle className="size-4.5" />
            Как работают оповещения
          </h3>
          <p className="text-[13px] text-muted-foreground/90 leading-relaxed">
            Discord Webhook позволяет автоматически отправлять сообщения в текстовый канал при наступлении ключевых событий на сервере:
          </p>
          <ul className="space-y-4 text-[13px] text-foreground/90">
            <li className="flex items-start gap-3">
              <CheckCircle className="size-4 text-success shrink-0 mt-0.5" />
              <span className="leading-relaxed"><strong className="text-foreground">Старт вайпа:</strong> Оповещение игроков о начале процесса Ordinary или Full Wipe.</span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle className="size-4 text-success shrink-0 mt-0.5" />
              <span className="leading-relaxed"><strong className="text-foreground">Новая карта:</strong> Публикация сгенерированного семени (seed) и размера карты.</span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle className="size-4 text-success shrink-0 mt-0.5" />
              <span className="leading-relaxed"><strong className="text-foreground">Готовность сервера:</strong> Уведомление с кнопкой быстрого подключения по IP-адресу.</span>
            </li>
          </ul>
          
          <div className="border-t border-white/5 pt-6 mt-2 flex flex-col gap-3">
            <div className="flex items-center gap-2.5 text-[13px] font-semibold text-primary">
              <Info className="size-4 shrink-0" />
              Инструкция по настройке
            </div>
            <p className="text-[12px] text-foreground/80 bg-primary/5 ring-1 ring-primary/20 rounded-xl p-4 leading-relaxed font-medium">
              Перейдите в настройки сервера в Discord &rarr; Интеграция &rarr; Вебхуки. Создайте новый вебхук и скопируйте его URL-адрес сюда.
            </p>
          </div>
        </div>
      </div>
    </form>
  )
}
