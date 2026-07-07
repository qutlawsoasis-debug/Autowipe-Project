'use client'

import { useCallback, useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Sidebar } from '@/components/dashboard/sidebar'
import { Header } from '@/components/dashboard/header'
import { OverviewTab } from '@/components/dashboard/overview-tab'
import { MapPoolTab } from '@/components/dashboard/map-pool-tab'
import { VoteTab } from '@/components/dashboard/vote-tab'
import { ScheduleTab } from '@/components/dashboard/schedule-tab'
import { ServerTab } from '@/components/dashboard/server-tab'
import { SettingsTab } from '@/components/dashboard/settings-tab'
import { WipeFilesTab } from '@/components/dashboard/wipefiles-tab'
import { IntegrationsTab } from '@/components/dashboard/integrations-tab'
import { CommitsTab } from '@/components/dashboard/commits-tab'
import { SmmTab } from '@/components/dashboard/smm-tab'
import {
  ConfirmDialog,
  type ConfirmState,
} from '@/components/dashboard/confirm-dialog'
import { Toaster, type Toast } from '@/components/dashboard/toaster'
import { tabTitles, type PoolMap, type TabId } from '@/lib/data'

export default function Page() {
  const [activeTab, setActiveTab] = useState<TabId>('dashboard')
  const [systemState, setSystemState] = useState<any>(null)
  const [maps, setMaps] = useState<PoolMap[]>([])
  const [confirm, setConfirm] = useState<ConfirmState | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])

  const toast = useCallback(
    (message: string, type: Toast['type'] = 'success') => {
      const id = Date.now() + Math.random()
      setToasts((prev) => [...prev, { id, message, type }])
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
      }, 3000)
    },
    []
  )

  const ask = useCallback(
    (
      title: string,
      message: string,
      onConfirm: () => void,
      destructive = false
    ) => {
      setConfirm({ title, message, onConfirm, destructive })
    },
    []
  )

  const fetchStatus = async () => {
    try {
      const r = await fetch('/api/status')
      const data = await r.json()
      setSystemState(data)
      if (data.maps) {
        const mappedMaps = data.maps.map((m: any, idx: number) => ({
          id: idx + 1,
          seed: m.seed,
          size: `${m.size}x${m.size}`,
          status: m.status === 'ready' ? 'ready' : 'generating',
          preview: m.preview_url ? `/media?path=${encodeURIComponent(m.map_path)}` : '',
          map_path: m.map_path,
        }))
        setMaps(mappedMaps)
      }
    } catch (err) {
      console.error('Error fetching backend status:', err)
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 4000)
    return () => clearInterval(interval)
  }, [])

  const handleAction = async (action: string) => {
    try {
      const r = await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      const res = await r.json()
      if (res.ok) {
        toast(`Команда ${action} успешно выполнена.`)
        fetchStatus()
      } else {
        toast(res.message || 'Ошибка выполнения действия', 'danger')
      }
    } catch (err) {
      toast('Не удалось отправить команду на бэкенд.', 'danger')
    }
  }

  const handleSaveSettings = async (settingsPayload: any) => {
    try {
      const r = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsPayload),
      })
      const res = await r.json()
      if (res.ok) {
        toast('Настройки успешно обновлены.')
        fetchStatus()
      } else {
        toast(res.message || 'Ошибка сохранения настроек', 'danger')
      }
    } catch (err) {
      toast('Не удалось отправить настройки.', 'danger')
    }
  }

  return (
    <div className="flex min-h-svh flex-col bg-background md:h-svh md:flex-row md:overflow-hidden">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header title={tabTitles[activeTab]} />

        <main className="flex-1 overflow-y-auto px-5 py-6 md:px-8 md:py-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className="w-full h-full flex flex-col"
            >
              {activeTab === 'dashboard' && (
            <OverviewTab maps={maps} systemState={systemState} />
          )}

          {activeTab === 'pool' && (
            <MapPoolTab
              maps={maps}
              onFillPool={() =>
                ask(
                  'Заполнить пул',
                  'Начать генерацию новых карт в пуле?',
                  () => handleAction('fill_pool')
                )
              }
              onClearPool={() =>
                ask(
                  'Очистить пул',
                  'Вы уверены? Это удалит все карты из пула.',
                  () => handleAction('clear_pool'),
                  true
                )
              }
              onDeleteMap={async (mapPath) => {
                try {
                  const r = await fetch('/api/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'delete_map', map_path: mapPath }),
                  })
                  const res = await r.json()
                  if (res.ok) {
                    toast(res.message || 'Карта удалена.')
                    fetchStatus()
                  } else {
                    toast(res.message || 'Не удалось удалить карту.', 'danger')
                  }
                } catch {
                  toast('Ошибка связи с сервером при удалении.', 'danger')
                }
              }}
              onGenerateBatch={async (count) => {
                try {
                  const r = await fetch('/api/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'generate_batch', count }),
                  })
                  const res = await r.json()
                  if (res.ok) {
                    toast(res.message || 'Генерация пачки запущена.')
                    fetchStatus()
                  } else {
                    toast(res.message || 'Не удалось запустить генерацию.', 'danger')
                  }
                } catch {
                  toast('Ошибка связи с сервером.', 'danger')
                }
              }}
              onCleanupStale={async () => {
                try {
                  const r = await fetch('/api/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'cleanup_stale' }),
                  })
                  const res = await r.json()
                  if (res.ok) {
                    toast(res.message || 'Очистка мусора запущена.')
                    fetchStatus()
                  } else {
                    toast(res.message || 'Ошибка запуска очистки.', 'danger')
                  }
                } catch {
                  toast('Ошибка связи с сервером.', 'danger')
                }
              }}
            />
          )}

          {activeTab === 'vote' && (
            <VoteTab
              systemState={systemState}
              onPublishVote={() =>
                ask(
                  'Опубликовать голосование',
                  'Опубликовать новое голосование в Discord?',
                  () => handleAction('publish_vote')
                )
              }
              onCancelVote={() =>
                ask(
                  'Отменить голосование',
                  'Прекратить текущее голосование в Discord?',
                  () => handleAction('cancel_vote'),
                  true
                )
              }
            />
          )}

          {activeTab === 'schedule' && (
            <ScheduleTab
              systemState={systemState}
              onWipeOrdinary={() =>
                ask(
                  'Ordinary Wipe (сейчас)',
                  'Начать обычный вайп сервера прямо сейчас?',
                  () => handleAction('wipe_ordinary'),
                  true
                )
              }
              onWipeFull={() =>
                ask(
                  'Full Wipe (сейчас)',
                  'Начать полный вайп сервера прямо сейчас?',
                  () => handleAction('wipe_full'),
                  true
                )
              }
              onClearError={() =>
                ask(
                  'Clear Wipe Error',
                  'Сбросить флаг критической ошибки?',
                  () => handleAction('clear_wipe_error')
                )
              }
            />
          )}

          {activeTab === 'server' && (
            <ServerTab
              systemState={systemState}
              onStart={() =>
                ask('Запустить сервер', 'Начать сервер Rust?', () =>
                  handleAction('start_server')
                )
              }
              onStop={() =>
                ask(
                  'Остановить сервер',
                  'Выключить сервер Rust?',
                  () => handleAction('stop_server'),
                  true
                )
              }
              onRestart={() =>
                ask('Перезагрузить сервер', 'Перезагрузить сервер Rust?', () =>
                  handleAction('restart_server')
                )
              }
            />
          )}

          {activeTab === 'settings' && (
            <SettingsTab
              systemState={systemState}
              onSaveSettings={handleSaveSettings}
            />
          )}

          {activeTab === 'wipefiles' && (
            <WipeFilesTab
              systemState={systemState}
              onWipeAction={handleAction}
              onSaveSettings={handleSaveSettings}
              ask={ask}
            />
          )}

          {activeTab === 'integrations' && (
            <IntegrationsTab
              systemState={systemState}
              onSaveSettings={handleSaveSettings}
            />
          )}

          {activeTab === 'commits' && (
            <CommitsTab
              systemState={systemState}
              onDiscordAnnounce={() => handleAction('discord_commits_announce')}
            />
          )}

          {activeTab === 'smm' && (
              <SmmTab
                systemState={systemState}
                onSaveSettings={handleSaveSettings}
              />
            )}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      <ConfirmDialog state={confirm} onClose={() => setConfirm(null)} />
      <Toaster toasts={toasts} />
    </div>
  )
}
