// frontend/src/app/[locale]/admin/roles/components/RoleList.tsx
'use client'

import { useEffect, useState } from 'react'
import { rolesApi, Role } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import Link from 'next/link'
import { RoleCreateDialog } from './RoleCreateDialog'
import { toast } from 'sonner'
import { Trash2, Edit, Shield, Briefcase } from 'lucide-react'

export function RoleList() {
  const [systemRoles, setSystemRoles] = useState<Role[]>([])
  const [businessRoles, setBusinessRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [activeTab, setActiveTab] = useState<'system' | 'business'>('system')

  const loadRoles = async () => {
    setLoading(true)
    try {
      const [sysRes, bizRes] = await Promise.all([
        rolesApi.list('system'),
        rolesApi.list('business'),
      ])
      setSystemRoles(sysRes.data)
      setBusinessRoles(bizRes.data)
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

  const renderRoleCards = (roles: Role[]) => (
    <div className="grid gap-3">
      {roles.length === 0 ? (
        <div className="text-center py-12 text-gray-400 border-2 border-dashed rounded-lg">
          <p className="text-sm">No roles yet</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => setShowCreate(true)}>
            Create Role
          </Button>
        </div>
      ) : (
        roles.map((role) => (
          <div key={role.id} className="border rounded-lg p-4 flex justify-between items-center group hover:border-primary/30 transition-colors">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-lg">{role.name}</h3>
                {role.is_system && (
                  <span className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-500 uppercase font-bold tracking-wider">System</span>
                )}
                <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase font-bold tracking-wider ${role.role_type === 'business'
                    ? 'bg-blue-50 text-blue-600'
                    : 'bg-slate-50 text-slate-500'
                  }`}>
                  {role.role_type}
                </span>
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
        ))
      )}
    </div>
  )

  return (
    <div>
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'system' | 'business')}>
        <div className="flex justify-between items-center mb-4">
          <TabsList>
            <TabsTrigger value="system" className="flex items-center gap-1.5">
              <Shield className="w-4 h-4" />
              System Roles ({systemRoles.length})
            </TabsTrigger>
            <TabsTrigger value="business" className="flex items-center gap-1.5">
              <Briefcase className="w-4 h-4" />
              Business Roles ({businessRoles.length})
            </TabsTrigger>
          </TabsList>
          <Button onClick={() => setShowCreate(true)}>
            Create {activeTab === 'business' ? 'Business' : 'System'} Role
          </Button>
        </div>

        <TabsContent value="system">
          <p className="text-sm text-gray-500 mb-4">
            System roles control which pages and features users can access in the application.
          </p>
          {renderRoleCards(systemRoles)}
        </TabsContent>

        <TabsContent value="business">
          <p className="text-sm text-gray-500 mb-4">
            Business roles control which ontology nodes are visible and which actions are executable for users.
          </p>
          {renderRoleCards(businessRoles)}
        </TabsContent>
      </Tabs>

      {showCreate && (
        <RoleCreateDialog
          roleType={activeTab}
          onClose={() => setShowCreate(false)}
          onCreated={loadRoles}
        />
      )}
    </div>
  )
}
