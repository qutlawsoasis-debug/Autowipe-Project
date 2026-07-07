export type MapStatus = 'ready' | 'generating'

export interface PoolMap {
  id: number
  seed: number
  size: string
  status: MapStatus
  preview: string
}

export interface VoteCandidate {
  id: number
  seed: number
  size: string
  votes: number
  preview: string
}

export interface WipeRecord {
  date: string
  type: 'Ordinary' | 'Full'
  seed: number
  size: string
  success: boolean
}

export interface LogEntry {
  time: string
  message: string
  level: 'info' | 'success' | 'warning' | 'error'
}

export const initialMaps: PoolMap[] = [
  { id: 1, seed: 45621, size: '4000x4000', status: 'ready', preview: '/maps/map-1.png' },
  { id: 2, seed: 82193, size: '3500x3500', status: 'generating', preview: '/maps/map-2.png' },
  { id: 3, seed: 19456, size: '4000x4000', status: 'ready', preview: '/maps/map-3.png' },
  { id: 4, seed: 72834, size: '3000x3000', status: 'generating', preview: '/maps/map-1.png' },
  { id: 5, seed: 56127, size: '4000x4000', status: 'ready', preview: '/maps/map-2.png' },
  { id: 6, seed: 91283, size: '3500x3500', status: 'ready', preview: '/maps/map-3.png' },
  { id: 7, seed: 34782, size: '4000x4000', status: 'generating', preview: '/maps/map-1.png' },
]

export const initialVotes: VoteCandidate[] = [
  { id: 1, seed: 45621, size: '4000x4000', votes: 67, preview: '/maps/map-1.png' },
  { id: 2, seed: 82193, size: '3500x3500', votes: 42, preview: '/maps/map-2.png' },
  { id: 3, seed: 19456, size: '4000x4000', votes: 23, preview: '/maps/map-3.png' },
  { id: 4, seed: 72834, size: '3000x3000', votes: 14, preview: '/maps/map-1.png' },
  { id: 5, seed: 56127, size: '4000x4000', votes: 0, preview: '/maps/map-2.png' },
]

export const wipeHistory: WipeRecord[] = [
  { date: '07 июля 2026, 20:00 UTC', type: 'Ordinary', seed: 45621, size: '3500x3500', success: true },
  { date: '30 июня 2026, 20:00 UTC', type: 'Full', seed: 28456, size: '4000x4000', success: true },
  { date: '23 июня 2026, 20:00 UTC', type: 'Ordinary', seed: 91234, size: '3500x3500', success: false },
]

export const recentLogs: LogEntry[] = [
  { time: '14:32:18', message: 'Карта #5 успешно загенерирована (seed: 45621, 4000x4000)', level: 'success' },
  { time: '14:28:45', message: 'Голосование опубликовано в Discord (5 кандидатов)', level: 'info' },
  { time: '14:25:12', message: 'Пул пополнен на 2 карты', level: 'info' },
  { time: '14:20:33', message: 'Карта #4 начала генерацию (seed: 82193)', level: 'info' },
  { time: '14:15:01', message: 'Соединение с RustMaps временно потеряно, переподключение...', level: 'warning' },
]

export type TabId =
  | 'dashboard'
  | 'pool'
  | 'vote'
  | 'schedule'
  | 'server'
  | 'settings'
  | 'wipefiles'
  | 'integrations'
  | 'commits'
  | 'smm'

export const tabTitles: Record<TabId, string> = {
  dashboard: 'Dashboard',
  pool: 'Map Pool',
  vote: 'Vote',
  schedule: 'Schedule',
  server: 'Server Control',
  settings: 'Settings',
  wipefiles: 'Wipe Files',
  integrations: 'Integrations',
  commits: 'Commits',
  smm: 'SMM Posts',
}
