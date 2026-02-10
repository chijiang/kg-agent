// frontend/src/components/layout.tsx
'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useTranslations, useLocale } from 'next-intl'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/lib/auth'
import { LanguageSwitcher } from '@/components/language-switcher'
import { useMemo } from 'react'

export function AppLayout({ children, noPadding = false }: { children: React.ReactNode, noPadding?: boolean }) {
  const pathname = usePathname()
  const router = useRouter()
  const locale = useLocale()
  const { user, logout } = useAuthStore()
  const t = useTranslations()

  const handleLogout = () => {
    logout()
    router.push(`/${locale}`)
  }

  const navItems = useMemo(() => [
    { href: `/${locale}/dashboard`, label: t('nav.qa') },
    { href: `/${locale}/graph/import`, label: t('nav.importGraph') },
    { href: `/${locale}/graph/management`, label: t('nav.ontology') },
    { href: `/${locale}/graph/instances`, label: t('nav.instances') },
    { href: `/${locale}/data-products`, label: t('nav.dataProducts') },
    { href: `/${locale}/rules`, label: t('nav.rules') },
    { href: `/${locale}/config`, label: t('nav.config') },
  ], [locale, t])

  return (
    <div className={`flex flex-col bg-slate-50/50 ${noPadding ? 'h-screen overflow-hidden' : 'min-h-screen'}`}>
      <header className="bg-white/80 backdrop-blur-md border-b border-slate-200/60 flex-shrink-0 sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-4 lg:px-8">
          {/* Top Row: Brand and User Controls */}
          <div className="h-14 flex items-center justify-between border-b border-slate-100/50">
            <h1 className="text-lg font-extrabold tracking-tight text-slate-900 flex items-center gap-2">
              <div className="w-7 h-7 bg-primary rounded-lg flex items-center justify-center text-white text-[10px] font-bold">EP</div>
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/70">
                {t('layout.title')}
              </span>
            </h1>

            <div className="flex items-center gap-4">
              <LanguageSwitcher />

              {user && (
                <div className="flex items-center gap-3 pl-4 border-l border-slate-200">
                  <div className="flex flex-col items-end">
                    <span className="text-[11px] font-semibold text-slate-900">{user.username}</span>
                    <button
                      onClick={handleLogout}
                      className="text-[9px] uppercase tracking-wider font-bold text-slate-400 hover:text-red-500 transition-colors"
                    >
                      {t('auth.logout')}
                    </button>
                  </div>
                  <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center text-slate-500 text-[10px] font-bold border border-white shadow-sm">
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Bottom Row: Navigation */}
          <div className="h-12 flex items-center">
            <nav className="w-full flex items-center justify-between">
              {navItems.map((item) => {
                const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${isActive
                        ? 'bg-primary/5 text-primary'
                        : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
                      }`}
                  >
                    {item.label}
                  </Link>
                )
              })}
            </nav>
          </div>
        </div>
      </header>
      <main className={`flex-1 flex flex-col ${noPadding ? 'min-h-0 overflow-hidden' : 'container mx-auto px-4 py-8'}`}>{children}</main>
    </div>
  )
}
