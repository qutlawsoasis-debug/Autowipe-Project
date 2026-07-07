'use client'

import {
  LayoutDashboard,
  Map,
  Vote,
  CalendarClock,
  ServerCog,
  Settings,
  Zap,
  FileCode,
  Network,
  History,
  Send,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { TabId } from '@/lib/data'

const navItems: { id: TabId; label: string; icon: typeof Map }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'pool', label: 'Map Pool', icon: Map },
  { id: 'vote', label: 'Vote', icon: Vote },
  { id: 'schedule', label: 'Schedule', icon: CalendarClock },
  { id: 'server', label: 'Server Control', icon: ServerCog },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'wipefiles', label: 'Wipe Files', icon: FileCode },
  { id: 'integrations', label: 'Integrations', icon: Network },
  { id: 'commits', label: 'Commits', icon: History },
  { id: 'smm', label: 'SMM Posts', icon: Send },
]

export function Sidebar({
  activeTab,
  onTabChange,
}: {
  activeTab: TabId
  onTabChange: (tab: TabId) => void
}) {
  return (
    <aside className="flex shrink-0 flex-col border-border bg-sidebar max-md:border-b md:w-56 md:border-r lg:w-60">
      <div className="flex items-center gap-2 px-4 py-4 md:px-5 md:py-6">
        <div className="flex size-7 items-center justify-center rounded-md bg-primary/15 text-primary">
          <Zap className="size-4" aria-hidden="true" />
        </div>
        <div className="leading-tight">
          <div className="font-mono text-sm font-semibold tracking-widest text-foreground">
            AUTOWIPE
          </div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Control Panel
          </div>
        </div>
      </div>

      <nav
        aria-label="Основная навигация"
        className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-1 md:flex-col md:px-3 md:pb-4"
      >
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeTab === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onTabChange(item.id)}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'flex shrink-0 items-center gap-2.5 px-3 py-2 text-[13px] font-medium transition-all border-l-2',
                isActive
                  ? 'bg-secondary text-foreground border-primary rounded-r-md'
                  : 'text-muted-foreground border-transparent hover:bg-secondary/40 hover:text-foreground rounded-md'
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
              {item.label}
            </button>
          )
        })}
      </nav>

      <div className="hidden border-t border-border px-5 py-4 md:block">
        <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          autowipe.py — v2.4.1
        </div>
      </div>
    </aside>
  )
}
