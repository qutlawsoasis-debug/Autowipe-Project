'use client'

import { useState, useEffect } from 'react'
import { FileCode, ShieldAlert, Trash2, ShieldCheck, Save, HelpCircle } from 'lucide-react'

interface WipeProfile {
  name: string
  paths: string[]
  locked?: boolean
}

export function WipeFilesTab({
  systemState,
  onWipeAction,
  onSaveSettings,
  ask,
}: {
  systemState: any
  onWipeAction: (action: string) => void
  onSaveSettings: (settings: any) => void
  ask: (title: string, message: string, onConfirm: () => void, destructive?: boolean) => void
}) {
  const [isProtectionDisabled, setIsProtectionDisabled] = useState(false)

  // Ordinary profile checkbox states
  const [ordMap, setOrdMap] = useState(true)
  const [ordSav, setOrdSav] = useState(true)
  const [ordOccl, setOrdOccl] = useState(true)
  const [ordBp, setOrdBp] = useState(false)
  const [ordPlayer, setOrdPlayer] = useState(false)

  // Blueprint profile checkbox states
  const [bpMap, setBpMap] = useState(true)
  const [bpSav, setBpSav] = useState(true)
  const [bpOccl, setBpOccl] = useState(true)
  const [bpBp, setBpBp] = useState(true)
  const [bpPlayer, setBpPlayer] = useState(false)

  // Parse path arrays from settings
  const getCheckedStates = (paths: string[] = []) => {
    const hasPath = (pattern: string) => paths.some((p) => p.includes(pattern))
    return {
      map: hasPath('*.map'),
      sav: hasPath('*.sav'),
      occlusion: hasPath('_occlusion_'),
      bp: hasPath('player.blueprints'),
      player: hasPath('player.identities') || hasPath('player.states'),
    }
  }

  useEffect(() => {
    const ordinaryPaths = systemState?.settings?.wipe_profiles?.ordinary?.paths
    if (ordinaryPaths) {
      const states = getCheckedStates(ordinaryPaths)
      setOrdMap(states.map)
      setOrdSav(states.sav)
      setOrdOccl(states.occlusion)
      setOrdBp(states.bp)
      setOrdPlayer(states.player)
    }

    const blueprintPaths = systemState?.settings?.wipe_profiles?.blueprint?.paths
    if (blueprintPaths) {
      const states = getCheckedStates(blueprintPaths)
      setBpMap(states.map)
      setBpSav(states.sav)
      setBpOccl(states.occlusion)
      setBpBp(states.bp)
      setBpPlayer(states.player)
    }
  }, [systemState])

  const handleToggleProtection = () => {
    if (!isProtectionDisabled) {
      ask(
        'Отключить защиту от удаления?',
        'Внимание! Отключение защиты позволит вручную очищать файлы профилей вайпа и разблокирует форму редактирования списков удаляемых файлов.',
        () => setIsProtectionDisabled(true),
        true
      )
    } else {
      setIsProtectionDisabled(false)
    }
  }

  const compilePaths = (states: {
    map: boolean
    sav: boolean
    occlusion: boolean
    bp: boolean
    player: boolean
  }) => {
    const paths: string[] = []
    if (states.map) paths.push('server/rust/*.map')
    if (states.sav) {
      paths.push('server/rust/*.sav')
      paths.push('server/rust/*.sav.1')
      paths.push('server/rust/*.sav.2')
    }
    if (states.occlusion) paths.push('server/rust/*_occlusion_*.dat')
    if (states.bp) {
      paths.push('server/rust/player.blueprints*.db')
      paths.push('server/rust/player.blueprints*.db-wal')
    }
    if (states.player) {
      paths.push('server/rust/player.identities*.db')
      paths.push('server/rust/player.states*.db')
      paths.push('server/rust/player.tokens*.db')
      paths.push('server/rust/player.deaths*.db')
    }
    return paths
  }

  const handleSaveWipeSettings = (e: React.FormEvent) => {
    e.preventDefault()
    const payload = {
      wipe_profiles: {
        ordinary: {
          locked: true,
          paths: compilePaths({
            map: ordMap,
            sav: ordSav,
            occlusion: ordOccl,
            bp: ordBp,
            player: ordPlayer,
          }),
        },
        blueprint: {
          locked: true,
          paths: compilePaths({
            map: bpMap,
            sav: bpSav,
            occlusion: bpOccl,
            bp: bpBp,
            player: bpPlayer,
          }),
        },
      },
    }
    onSaveSettings(payload)
  }

  const profiles: WipeProfile[] = []
  const wipeProfiles = systemState?.settings?.wipe_profiles

  if (wipeProfiles) {
    Object.entries(wipeProfiles).forEach(([name, val]: [string, any]) => {
      profiles.push({
        name: name.toUpperCase(),
        paths: val.paths || [],
        locked: !isProtectionDisabled,
      })
    })
  } else {
    profiles.push({
      name: 'ORDINARY WIPE',
      paths: compilePaths({ map: ordMap, sav: ordSav, occlusion: ordOccl, bp: ordBp, player: ordPlayer }),
      locked: !isProtectionDisabled,
    })
    profiles.push({
      name: 'BLUEPRINT WIPE',
      paths: compilePaths({ map: bpMap, sav: bpSav, occlusion: bpOccl, bp: bpBp, player: bpPlayer }),
      locked: !isProtectionDisabled,
    })
  }

  return (
    <div className="flex flex-col gap-8 w-full">
      {/* Help Banner */}
      <div className="rounded-lg border border-border bg-card p-5 flex items-start gap-4">
        <div className="rounded-md bg-primary/10 p-2 text-primary">
          <HelpCircle className="size-5" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-foreground">Как устроена очистка файлов при вайпе?</h3>
          <p className="mt-1 text-sm text-muted-foreground leading-relaxed">
            В зависимости от типа запускаемого вайпа скрипт удаляет указанные пути.
            Обычный вайп (<strong>Ordinary</strong>) сбрасывает постройки на карте, сохраняя чертежи игроков.
            Полный вайп (<strong>Blueprint/Full</strong>) производит тотальный сброс сервера с удалением изученных рецептов.
          </p>
        </div>
      </div>

      {/* Protection Switch Card */}
      <div className="rounded-lg border border-border bg-card p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className={`rounded-md p-2 ${isProtectionDisabled ? 'bg-warning/10 text-warning' : 'bg-success/10 text-success'}`}>
            {isProtectionDisabled ? (
              <ShieldAlert className="size-5" />
            ) : (
              <ShieldCheck className="size-5" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              {isProtectionDisabled ? 'Защита от изменений отключена' : 'Защита от случайных изменений активна'}
            </h3>
            <p className="mt-1 text-sm text-muted-foreground leading-relaxed">
              Включение режима разработчика разблокирует кнопки немедленной очистки файлов профилей и форму изменения их конфигурации.
            </p>
          </div>
        </div>
        <div>
          <button
            type="button"
            onClick={handleToggleProtection}
            className={`rounded-md px-4 py-2.5 text-xs font-bold uppercase tracking-wider transition-colors border ${
              isProtectionDisabled
                ? 'border-success/30 bg-success/5 text-success hover:bg-success/15'
                : 'border-warning/30 bg-warning/5 text-warning hover:bg-warning/15'
            }`}
          >
            {isProtectionDisabled ? '🔒 Включить защиту' : '🔓 Отключить защиту'}
          </button>
        </div>
      </div>

      {/* Wipe Profiles List */}
      <div className="grid gap-6 md:grid-cols-2">
        {profiles.map((profile) => (
          <div key={profile.name} className="rounded-lg border border-border bg-card p-6 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-border pb-3 mb-4">
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-primary">
                  {profile.name}
                </span>
                <span className={`text-[10px] uppercase font-mono px-2.5 py-0.5 rounded font-bold ${profile.locked ? 'bg-secondary text-muted-foreground' : 'bg-destructive/15 text-destructive'}`}>
                  {profile.locked ? '🔒 locked' : '🔓 unlocked'}
                </span>
              </div>
              <ul className="space-y-2 mb-6">
                {profile.paths.map((p, idx) => (
                  <li key={idx} className="flex items-center gap-2 font-mono text-xs text-foreground">
                    <FileCode className="size-3.5 text-muted-foreground" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
            
            <div>
              <button
                type="button"
                disabled={profile.locked}
                onClick={() =>
                  ask(
                    `Очистить профиль ${profile.name}?`,
                    'Внимание! Это немедленно удалит выбранные файлы с диска сервера. Игроки потеряют часть прогресса.',
                    () => onWipeAction(profile.name.toLowerCase().includes('blue') || profile.name.toLowerCase().includes('full') ? 'wipe_full' : 'wipe_ordinary'),
                    true
                  )
                }
                className={`w-full flex items-center justify-center gap-2 rounded-md border px-4 py-2.5 text-xs font-bold uppercase tracking-wider transition-colors ${
                  profile.locked
                    ? 'border-border bg-secondary/50 text-muted-foreground/30 cursor-not-allowed'
                    : 'border-destructive/20 bg-destructive/5 text-destructive hover:bg-destructive hover:text-white'
                }`}
              >
                <Trash2 className="size-3.5" />
                Очистить файлы профиля
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Settings Panel split by profile */}
      {isProtectionDisabled && (
        <section className="mt-4 border-t border-border pt-6 animate-in fade-in duration-300">
          <h2 className="mb-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Детальная конфигурация файлов профилей вайпа
          </h2>
          <form onSubmit={handleSaveWipeSettings} className="flex flex-col gap-6">
            <div className="grid gap-6 md:grid-cols-2">
              {/* Ordinary Wipe Config */}
              <div className="rounded-lg border border-border bg-card p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4 pb-2 border-b border-border">
                  Файлы для ORDINARY WIPE (Обычный вайп)
                </h3>
                <div className="flex flex-col gap-3">
                  <div className="flex items-center gap-3">
                    <input
                      id="ordMap"
                      type="checkbox"
                      checked={ordMap}
                      onChange={(e) => setOrdMap(e.target.checked)}
                      className="size-4 rounded border-input bg-background accent-primary"
                    />
                    <label htmlFor="ordMap" className="text-sm font-medium text-foreground cursor-pointer">
                      Удалять файл карты (.map)
                    </label>
                  </div>
                  <div className="flex items-center gap-3">
                    <input
                      id="ordSav"
                      type="checkbox"
                      checked={ordSav}
                      onChange={(e) => setOrdSav(e.target.checked)}
                      className="size-4 rounded border-input bg-background accent-primary"
                    />
                    <label htmlFor="ordSav" className="text-sm font-medium text-foreground cursor-pointer">
                      Удалять файлы сохранений (.sav)
                    </label>
                  </div>
                  <div className="flex items-center gap-3">
                    <input
                      id="ordOccl"
                      type="checkbox"
                      checked={ordOccl}
                      onChange={(e) => setOrdOccl(e.target.checked)}
                      className="size-4 rounded border-input bg-background accent-primary"
                    />
                    <label htmlFor="ordOccl" className="text-sm font-medium text-foreground cursor-pointer">
                      Удалять Occlusion файлы
                    </label>
                  </div>
                  <div className="flex items-center gap-3">
                    <input
                      id="ordBp"
                      type="checkbox"
                      checked={ordBp}
                      onChange={(e) => setOrdBp(e.target.checked)}
                      className="size-4 rounded border-input bg-background accent-primary"
                    />
                    <label htmlFor="ordBp" className="text-sm font-medium text-foreground cursor-pointer">
                      Удалять Базу Чертежей (Blueprints)
                    </label>
                  </div>
                  <div className="flex items-center gap-3">
                    <input
                      id="ordPlayer"
                      type="checkbox"
                      checked={ordPlayer}
                      onChange={(e) => setOrdPlayer(e.target.checked)}
                      className="size-4 rounded border-input bg-background accent-primary"
                    />
                    <label htmlFor="ordPlayer" className="text-sm font-medium text-foreground cursor-pointer">
                      Удалять базы данных игроков (прогресс/states)
                    </label>
                  </div>
                </div>
              </div>

              {/* Blueprint/Full Wipe Config */}
              <div className="rounded-lg border border-border bg-card p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4 pb-2 border-b border-border">
                  Файлы для BLUEPRINT WIPE (Полный вайп)
                </h3>
                <div className="flex flex-col gap-3">
                  <div className="flex items-center gap-3">
                    <input
                      id="bpMap"
                      type="checkbox"
                      checked={bpMap}
                      onChange={(e) => setBpMap(e.target.checked)}
                      className="size-4 rounded border-input bg-background accent-primary"
                    />
                    <label htmlFor="bpMap" className="text-sm font-medium text-foreground cursor-pointer">
                      Удалять файл карты (.map)
                    </label>
                  </div>
                  <div className="flex items-center gap-3">
                    <input
                      id="bpSav"
                      type="checkbox"
                      checked={bpSav}
                      onChange={(e) => setBpSav(e.target.checked)}
                      className="size-4 rounded border-input bg-background accent-primary"
                    />
                    <label htmlFor="bpSav" className="text-sm font-medium text-foreground cursor-pointer">
                      Удалять файлы сохранений (.sav)
                    </label>
                  </div>
                  <div className="flex items-center gap-3">
                    <input
                      id="bpOccl"
                      type="checkbox"
                      checked={bpOccl}
                      onChange={(e) => setBpOccl(e.target.checked)}
                      className="size-4 rounded border-input bg-background accent-primary"
                    />
                    <label htmlFor="bpOccl" className="text-sm font-medium text-foreground cursor-pointer">
                      Удалять Occlusion файлы
                    </label>
                  </div>
                  <div className="flex items-center gap-3">
                    <input
                      id="bpBp"
                      type="checkbox"
                      checked={bpBp}
                      onChange={(e) => setBpBp(e.target.checked)}
                      className="size-4 rounded border-input bg-background accent-primary"
                    />
                    <label htmlFor="bpBp" className="text-sm font-medium text-foreground cursor-pointer">
                      Удалять Базу Чертежей (Blueprints)
                    </label>
                  </div>
                  <div className="flex items-center gap-3">
                    <input
                      id="bpPlayer"
                      type="checkbox"
                      checked={bpPlayer}
                      onChange={(e) => setBpPlayer(e.target.checked)}
                      className="size-4 rounded border-input bg-background accent-primary"
                    />
                    <label htmlFor="bpPlayer" className="text-sm font-medium text-foreground cursor-pointer">
                      Удалять базы данных игроков (прогресс/states)
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end border-t border-border pt-4">
              <button
                type="submit"
                className="flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
              >
                <Save className="size-4" />
                Сохранить профили вайпа
              </button>
            </div>
          </form>
        </section>
      )}
    </div>
  )
}
