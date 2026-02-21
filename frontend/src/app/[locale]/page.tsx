'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale } from 'next-intl'
import { useAuthStore } from '@/lib/auth'

export default function RootPage() {
  const router = useRouter()
  const locale = useLocale()
  const { token } = useAuthStore()

  useEffect(() => {
    if (token) {
      router.replace(`/${locale}/dashboard`)
    } else {
      router.replace(`/${locale}/login`)
    }
  }, [token, locale, router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>
  )
}
