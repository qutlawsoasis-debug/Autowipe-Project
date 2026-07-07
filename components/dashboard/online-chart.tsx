'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid
} from 'recharts'

const data24h = [
  { time: '00:00', players: 85 },
  { time: '04:00', players: 40 },
  { time: '08:00', players: 65 },
  { time: '12:00', players: 120 },
  { time: '16:00', players: 190 },
  { time: '20:00', players: 245 },
  { time: '23:59', players: 170 },
]

const dataUnique = [
  { time: '24 Июн', players: 410 },
  { time: '25 Июн', players: 450 },
  { time: '26 Июн', players: 480 },
  { time: '27 Июн', players: 510 },
  { time: '28 Июн', players: 600 },
  { time: '29 Июн', players: 750 },
  { time: '30 Июн', players: 810 },
  { time: '1 Июл', players: 420 },
  { time: '2 Июл', players: 460 },
  { time: '3 Июл', players: 500 },
  { time: '4 Июл', players: 530 },
  { time: '5 Июл', players: 620 },
  { time: '6 Июл', players: 800 },
  { time: '7 Июл', players: 850 },
]

export function OnlineChart() {
  const [period, setPeriod] = useState<'online' | 'unique'>('online')
  const currentData = period === 'online' ? data24h : dataUnique

  return (
    <div className="flex flex-col w-full">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold tracking-tight text-foreground">
          Активность игроков
        </h2>
        <div className="flex items-center gap-1 bg-black/40 p-1 rounded-lg ring-1 ring-white/10">
          <button 
            onClick={() => setPeriod('online')}
            className={cn(
              "px-3 py-1.5 rounded-md text-[11px] font-semibold tracking-wide transition-all",
              period === 'online' ? "bg-white/15 text-white shadow-sm ring-1 ring-white/20" : "text-muted-foreground hover:text-white"
            )}
          >
            ОНЛАЙН (24Ч)
          </button>
          <button 
            onClick={() => setPeriod('unique')}
            className={cn(
              "px-3 py-1.5 rounded-md text-[11px] font-semibold tracking-wide transition-all",
              period === 'unique' ? "bg-white/15 text-white shadow-sm ring-1 ring-white/20" : "text-muted-foreground hover:text-white"
            )}
          >
            УНИКАЛЬНЫЕ ВХОДЫ (14 ДНЕЙ)
          </button>
        </div>
      </div>

      <div className="h-[240px] w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={currentData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorPlayers" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="oklch(0.65 0.25 260)" stopOpacity={0.4} />
              <stop offset="95%" stopColor="oklch(0.65 0.25 260)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis 
            dataKey="time" 
            stroke="rgba(255,255,255,0.3)" 
            fontSize={12} 
            tickLine={false} 
            axisLine={false} 
          />
          <YAxis 
            stroke="rgba(255,255,255,0.3)" 
            fontSize={12} 
            tickLine={false} 
            axisLine={false} 
            tickFormatter={(value) => `${value}`}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'rgba(0,0,0,0.6)', 
              backdropFilter: 'blur(12px)',
              borderColor: 'rgba(255,255,255,0.1)',
              borderRadius: '12px',
              color: '#fff',
              fontSize: '13px',
              boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)'
            }}
            itemStyle={{ color: 'oklch(0.65 0.25 260)' }}
            labelStyle={{ color: 'rgba(255,255,255,0.7)', marginBottom: '4px' }}
          />
          <Area
            type="monotone"
            dataKey="players"
            stroke="oklch(0.65 0.25 260)"
            strokeWidth={3}
            fillOpacity={1}
            fill="url(#colorPlayers)"
            animationDuration={1500}
            animationEasing="ease-out"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
    </div>
  )
}
