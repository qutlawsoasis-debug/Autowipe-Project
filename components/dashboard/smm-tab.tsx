'use client'

import { useState, useEffect } from 'react'
import { Save, Send, Loader2 } from 'lucide-react'

export function SmmTab({
  systemState,
  onSaveSettings,
}: {
  systemState: any
  onSaveSettings: (settings: any) => void
}) {
  const [enabled, setEnabled] = useState(false)
  const [postTime, setPostTime] = useState('16:00')
  const [channelId, setChannelId] = useState('')
  const [templates, setTemplates] = useState<Record<string, string>>({
    monday: '',
    tuesday: '',
    wednesday: '',
    thursday: '',
    friday: '',
    saturday: '',
    sunday: '',
  })

  // Test states
  const [testLoading, setTestLoading] = useState<Record<string, boolean>>({})

  useEffect(() => {
    const smm = systemState?.settings?.smm
    if (smm) {
      setEnabled(smm.enabled ?? false)
      setPostTime(smm.post_time ?? '16:00')
      setChannelId(smm.channel_id ?? '')
      if (smm.templates) {
        setTemplates(smm.templates)
      }
    }
  }, [systemState])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload = {
      smm: {
        enabled,
        post_time: postTime,
        channel_id: channelId,
        templates,
      },
    }
    onSaveSettings(payload)
  }

  const handleTemplateChange = (day: string, value: string) => {
    setTemplates((prev) => ({
      ...prev,
      [day]: value,
    }))
  }

  const handleTestSmm = async (day: string) => {
    try {
      setTestLoading((prev) => ({ ...prev, [day]: true }))
      const r = await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'smm_post_test', day }),
      })
      const res = await r.json()
      alert(res.message || 'Тестовое сообщение отправлено.')
    } catch (err) {
      alert('Ошибка при отправке тестового сообщения.')
    } finally {
      setTestLoading((prev) => ({ ...prev, [day]: false }))
    }
  }

  const weekdays = [
    { id: 'monday', label: 'Понедельник' },
    { id: 'tuesday', label: 'Вторник' },
    { id: 'wednesday', label: 'Среда' },
    { id: 'thursday', label: 'Четверг' },
    { id: 'friday', label: 'Пятница' },
    { id: 'saturday', label: 'Суббота' },
    { id: 'sunday', label: 'Воскресенье' },
  ]

  return (
    <form className="flex w-full flex-col gap-10" onSubmit={handleSubmit}>
      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold tracking-tight text-foreground">
          SMM Автопубликации
        </h2>
        <div className="grid gap-6 rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-8 shadow-lg shadow-black/20 backdrop-blur-md sm:grid-cols-2 lg:grid-cols-3">
          <div className="flex items-center gap-3 sm:col-span-2 lg:col-span-3">
            <input
              id="smmEnabled"
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="size-4.5 rounded ring-1 ring-white/10 bg-black/50 accent-primary cursor-pointer transition-all"
            />
            <label htmlFor="smmEnabled" className="text-sm font-medium text-foreground cursor-pointer select-none">
              Включить автоматические посты
            </label>
          </div>

          <div className="flex flex-col gap-1.5 mt-2">
            <label htmlFor="postTime" className="text-xs font-medium text-muted-foreground">
              Время автопостинга (по серверу)
            </label>
            <input
              id="postTime"
              type="text"
              placeholder="16:00"
              value={postTime}
              onChange={(e) => setPostTime(e.target.value)}
              className="rounded-xl ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-primary transition-all"
            />
          </div>

          <div className="flex flex-col gap-1.5 mt-2 lg:col-span-2">
            <label htmlFor="channelId" className="text-xs font-medium text-muted-foreground">
              ID Канала публикаций (Telegram/Discord)
            </label>
            <input
              id="channelId"
              type="text"
              placeholder="Введите ID канала"
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              className="rounded-xl ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-primary transition-all"
            />
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold tracking-tight text-foreground">
          Шаблоны постов по дням недели
        </h2>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {weekdays.map((day) => (
            <div key={day.id} className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-6 flex flex-col gap-4 shadow-lg shadow-black/20">
              <div className="flex items-center justify-between border-b border-white/5 pb-4">
                <label htmlFor={`template-${day.id}`} className="text-sm font-semibold tracking-tight text-primary">
                  {day.label}
                </label>
                <button
                  type="button"
                  disabled={testLoading[day.id]}
                  onClick={() => handleTestSmm(day.id)}
                  className="text-[10px] font-semibold text-primary hover:underline flex items-center gap-1 disabled:opacity-50"
                >
                  {testLoading[day.id] ? (
                    <Loader2 className="size-3 animate-spin" />
                  ) : (
                    <Send className="size-3" />
                  )}
                  Тест
                </button>
              </div>
              <textarea
                id={`template-${day.id}`}
                rows={6}
                value={templates[day.id] || ''}
                onChange={(e) => handleTemplateChange(day.id, e.target.value)}
                placeholder="Шаблон сообщения не задан"
                className="w-full rounded-xl ring-1 ring-white/10 bg-black/40 px-4 py-3 font-mono text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none transition-all placeholder:text-muted-foreground/50"
              />
            </div>
          ))}
        </div>
      </section>

      <div className="flex justify-end pt-2 pb-6">
        <button
          type="submit"
          className="flex items-center gap-2.5 rounded-xl ring-1 ring-primary/50 bg-primary/20 px-8 py-3 text-sm font-semibold text-primary transition-all hover:bg-primary hover:text-white hover:ring-primary shadow-[0_0_15px_rgba(var(--primary),0.2)]"
        >
          <Save className="size-4" aria-hidden="true" />
          Сохранить расписание постов
        </button>
      </div>
    </form>
  )
}
