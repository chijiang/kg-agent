// frontend/src/app/[locale]/admin/roles/[id]/page.tsx
'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import { rolesApi, RoleDetail } from '@/lib/api'
import { ProtectedPage } from '@/components/auth/ProtectedPage'
import { AppLayout } from '@/components/layout'
import { RolePermissionEditor } from '../components/RolePermissionEditor'

export default function RoleDetailPage() {
  const params = useParams()
  const roleId = parseInt(params.id as string)
  const [role, setRole] = useState<RoleDetail | null>(null)
  const [loading, setLoading] = useState(true)

  const loadRole = useCallback(async () => {
    try {
      const response = await rolesApi.get(roleId)
      setRole(response.data)
    } catch (error) {
      console.error('Failed to load role:', error)
    } finally {
      setLoading(false)
    }
  }, [roleId])

  useEffect(() => {
    loadRole()
  }, [loadRole])

  if (loading) return <AppLayout><div className="p-6">Loading...</div></AppLayout>
  if (!role) return <AppLayout><div className="p-6">Role not found</div></AppLayout>

  return (
    <AppLayout>
      <ProtectedPage pageId="admin">
        <div className="container mx-auto py-6">
          <RolePermissionEditor role={role} onUpdated={loadRole} />
        </div>
      </ProtectedPage>
    </AppLayout>
  )
}
