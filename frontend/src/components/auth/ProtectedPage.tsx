// frontend/src/components/auth/ProtectedPage.tsx
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { usePermissions } from '@/hooks/usePermissions'
import { AccessDeniedPage } from './AccessDenied'

interface ProtectedPageProps {
  pageId: string
  children: React.ReactNode
}

export function ProtectedPage({ pageId, children }: ProtectedPageProps) {
  const { hasPageAccess, loading } = usePermissions()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !hasPageAccess(pageId)) {
      router.push('/')
    }
  }, [hasPageAccess, loading, pageId, router])

  if (loading) {
    return <div>Loading...</div>
  }

  if (!hasPageAccess(pageId)) {
    return <AccessDeniedPage />
  }

  return <>{children}</>
}
