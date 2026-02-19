// frontend/src/app/[locale]/admin/roles/components/RoleList.tsx
'use client'

import { useEffect, useState } from 'react'
import { rolesApi, Role } from '@/lib/api'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { RoleCreateDialog } from './RoleCreateDialog'
import { toast } from 'sonner'
import { Trash2, Edit } from 'lucide-react'

export function RoleList() {
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  const loadRoles = async () => {
    setLoading(true)
    try {
      const response = await rolesApi.list()
      setRoles(response.data)
    } catch (error) {
      console.error('Failed to load roles:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRoles()
  }, [])

  const handleDeleteRole = async (roleId: number) => {
    if (!confirm('Are you sure you want to delete this role? This action cannot be undone.')) return

    try {
      await rolesApi.delete(roleId)
      toast.success('Role deleted successfully')
      loadRoles()
    } catch (error: unknown) {
      const message = (error as any).response?.data?.detail || 'Failed to delete role'
      console.error('Failed to delete role:', error)
      toast.error(message)
    }
  }

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl">Roles ({roles.length})</h2>
        <Button onClick={() => setShowCreate(true)}>Create Role</Button>
      </div>

      <div className="grid gap-4">
        {roles.map((role) => (
          <div key={role.id} className="border rounded p-4 flex justify-between items-center group hover:border-accenture-purple transition-colors">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-lg">{role.name}</h3>
                {role.is_system && (
                  <span className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-500 uppercase font-bold tracking-wider">System</span>
                )}
              </div>
              <p className="text-sm text-gray-600">{role.description || 'No description provided'}</p>
            </div>
            <div className="flex items-center gap-2">
              <Link href={`roles/${role.id}`}>
                <Button variant="outline" size="sm" className="flex items-center gap-1.5">
                  <Edit className="w-4 h-4" />
                  Edit Permissions
                </Button>
              </Link>
              {!role.is_system && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-red-500 hover:text-red-700 hover:bg-red-50"
                  onClick={() => handleDeleteRole(role.id)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>

      {showCreate && (
        <RoleCreateDialog
          onClose={() => setShowCreate(false)}
          onCreated={loadRoles}
        />
      )}
    </div>
  )
}
