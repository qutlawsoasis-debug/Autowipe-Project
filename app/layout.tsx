import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'

const geistSans = Geist({ subsets: ['latin'], variable: '--font-geist-sans' })
const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
})

export const metadata: Metadata = {
  title: 'Autowipe Control Panel',
  description:
    'Панель управления автоматическими вайпами Rust-сервера: пул карт, голосования, расписание и контроль сервера.',
  generator: 'v0.app',
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#16181d',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="ru"
      className={`dark bg-background ${geistSans.variable} ${geistMono.variable}`}
    >
      <body className="antialiased font-sans min-h-screen relative overflow-x-hidden">
        {/* Refactoring UI / Vercel style subtle radial gradient for depth */}
        <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-white/[0.03] via-background to-background z-0" />
        
        <div className="relative z-10 flex flex-col min-h-screen">
          {children}
        </div>
        
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
