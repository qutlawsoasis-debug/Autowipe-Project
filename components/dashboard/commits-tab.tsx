'use client'

import { useState, useEffect } from 'react'
import { Send, Plus, History, Check, Loader2, MessageSquareCode } from 'lucide-react'

interface Commit {
  id: string
  message: string
  author: string
  type: string
  created_at: string
  sent_to_discord: boolean
}

export function CommitsTab({
  systemState,
  onDiscordAnnounce,
}: {
  systemState: any
  onDiscordAnnounce: () => void
}) {
  const [commits, setCommits] = useState<Commit[]>([])
  const [message, setMessage] = useState('')
  const [author, setAuthor] = useState('Admin')
  const [type, setType] = useState('feat')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [sendingId, setSendingId] = useState<string | null>(null)

  const fetchCommits = async () => {
    try {
      setLoading(true)
      const r = await fetch('/api/commits')
      const data = await r.json()
      if (data.ok) {
        setCommits(data.commits || [])
      } else {
        setError(data.message || 'Ошибка загрузки истории изменений.')
      }
    } catch (err) {
      setError('Не удалось загрузить лог изменений с бэкенда.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCommits()
  }, [])

  const handleCreateCommit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim()) return
    try {
      setIsSubmitting(true)
      const r = await fetch('/api/commits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: message,
          author,
          type,
          send: false,
        }),
      })
      const res = await r.json()
      if (res.ok) {
        setMessage('')
        fetchCommits()
      } else {
        alert(res.message || 'Не удалось сохранить запись.')
      }
    } catch (err) {
      alert('Ошибка соединения с бэкендом при сохранении записи.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSendCommit = async (commitId: string) => {
    try {
      setSendingId(commitId)
      const r = await fetch(`/api/commits/${commitId}/send`, {
        method: 'POST',
      })
      const res = await r.json()
      if (res.ok) {
        alert('Коммит отправлен в Discord!')
        fetchCommits()
      } else {
        alert(res.message || 'Ошибка отправки коммита.')
      }
    } catch (err) {
      alert('Ошибка связи с бэкендом при отправке.')
    } finally {
      setSendingId(null)
    }
  }

  return (
    <div className="flex flex-col gap-8 w-full">
      {/* Top action block */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          Лог обновлений
        </h2>
        <button
          type="button"
          onClick={onDiscordAnnounce}
          className="flex items-center gap-2 rounded-xl ring-1 ring-white/10 bg-white/5 px-5 py-2.5 text-sm font-medium text-foreground hover:bg-white/10 transition-all shadow-sm"
        >
          <Send className="size-4" />
          Синхронизировать лог с Discord
        </button>
      </div>

      <div className="grid gap-8 lg:grid-cols-3 items-start">
        {/* Form to create a commit */}
        <div className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-8 shadow-lg shadow-black/20 backdrop-blur-md h-fit lg:col-span-1">
          <h3 className="text-sm font-semibold mb-6 text-foreground flex items-center gap-2.5">
            <Plus className="size-4.5 text-primary" />
            Добавить запись вручную
          </h3>
          <form onSubmit={handleCreateCommit} className="flex flex-col gap-5">
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-muted-foreground">Сообщение</label>
              <textarea
                rows={3}
                required
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="style: redesign layouts..."
                className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 text-[13px] text-foreground placeholder:text-muted-foreground/40 focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner resize-none"
              />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-muted-foreground">Автор</label>
              <input
                type="text"
                required
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="Admin"
                className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 text-[13px] text-foreground placeholder:text-muted-foreground/40 focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner"
              />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-muted-foreground">Тип коммита</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="rounded-xl border-none ring-1 ring-white/10 bg-black/40 px-4 py-3 text-[13px] text-foreground focus:ring-2 focus:ring-primary/50 transition-shadow shadow-inner cursor-pointer"
              >
                <option value="feat">feat (Новая функция)</option>
                <option value="fix">fix (Исправление бага)</option>
                <option value="style">style (Дизайн / Стили)</option>
                <option value="docs">docs (Документация)</option>
                <option value="refactor">refactor (Рефакторинг)</option>
                <option value="chore">chore (Сборка / Зависимости)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="mt-4 w-full flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white transition-all hover:opacity-90 hover:drop-shadow-[0_0_12px_rgba(var(--primary),0.4)] disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                'Добавить запись'
              )}
            </button>
          </form>
        </div>

        {/* List of commits */}
        <div className="lg:col-span-2">
          {loading ? (
            <div className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 p-16 text-center text-sm font-medium text-muted-foreground flex items-center justify-center gap-3 backdrop-blur-md">
              <Loader2 className="size-5 animate-spin text-primary" />
              Загрузка коммитов с сервера...
            </div>
          ) : error ? (
            <div className="rounded-2xl bg-destructive/5 ring-1 ring-destructive/20 p-8 text-center text-sm text-destructive font-semibold backdrop-blur-md">
              {error}
            </div>
          ) : commits.length === 0 ? (
            <div className="rounded-2xl border-2 border-dashed border-white/10 py-20 text-center text-sm text-muted-foreground font-medium backdrop-blur-sm">
              Лог обновлений пуст.
            </div>
          ) : (
            <div className="rounded-2xl bg-white/[0.02] ring-1 ring-white/5 overflow-hidden shadow-lg shadow-black/20 backdrop-blur-md">
              <div className="divide-y divide-white/5">
                {commits.map((commit) => (
                  <div key={commit.id} className="p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6 transition-colors hover:bg-white/[0.02]">
                    <div className="flex items-start gap-4">
                      <div className="mt-1 rounded-xl bg-white/5 ring-1 ring-white/10 p-2 text-muted-foreground shrink-0 shadow-inner">
                        <History className="size-4" />
                      </div>
                      <div className="flex flex-col gap-2">
                        <div className="text-[15px] font-semibold text-foreground tracking-tight leading-snug">{commit.message}</div>
                        <div className="text-[13px] text-muted-foreground flex flex-wrap gap-x-4 gap-y-2 items-center font-medium">
                          <span className="flex items-center gap-1.5">ID: <code className="font-mono text-[11px] bg-black/40 px-1.5 py-0.5 rounded flex items-center">{commit.id}</code></span>
                          <span>Автор: <strong className="text-foreground/90">{commit.author}</strong></span>
                          {commit.sent_to_discord ? (
                            <span className="flex items-center gap-1.5 text-success text-[11px] font-bold uppercase tracking-wider">
                              <Check className="size-3.5" />
                              В Discord
                            </span>
                          ) : (
                            <span className="text-muted-foreground/60 text-[11px] font-bold uppercase tracking-wider">
                              Черновик
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {!commit.sent_to_discord && (
                      <button
                        type="button"
                        disabled={sendingId === commit.id}
                        onClick={() => handleSendCommit(commit.id)}
                        className="rounded-xl ring-1 ring-[#2fd4ec]/30 bg-[#2fd4ec]/10 px-5 py-2.5 text-sm font-semibold text-[#2fd4ec] transition-all hover:bg-[#2fd4ec] hover:text-white hover:ring-[#2fd4ec] hover:drop-shadow-[0_0_12px_rgba(47,212,236,0.4)] shrink-0"
                      >
                        {sendingId === commit.id ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          'Отправить'
                        )}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
