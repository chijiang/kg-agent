// frontend/src/components/auth/ProtectedPage.tsx
'use client'

import { useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { usePermissions } from '@/hooks/usePermissions'
import { AccessDeniedPage } from './AccessDenied'

interface ProtectedPageProps {
  pageId: string
  children: React.ReactNode
}

export function ProtectedPage({ pageId, children }: ProtectedPageProps) {
  const { hasPageAccess, loading } = usePermissions()
  const router = useRouter()
  const params = useParams()

  useEffect(() => {
    if (!loading && !hasPageAccess(pageId)) {
      const locale = params?.locale || 'en'
      router.push(`/${locale}/login`)
    }
  }, [hasPageAccess, loading, pageId, router, params])

  if (loading) {
    return <div>Loading...</div>
  }

  if (!hasPageAccess(pageId)) {
    return <AccessDeniedPage />
  }

  return <>{children}</>
}
