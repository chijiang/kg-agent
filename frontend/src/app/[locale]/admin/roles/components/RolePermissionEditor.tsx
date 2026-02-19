// frontend/src/app/[locale]/admin/roles/components/RolePermissionEditor.tsx
'use client'

import { useState } from 'react'
import { RoleDetail, rolesApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import {
  Sparkles,
  Network,
  CircleDot,
  Package,
  Scale,
  Database,
  Settings,
  Shield,
  ArrowLeft,
  Check,
  X,
} from 'lucide-react'
import Link from 'next/link'
import { useLocale } from 'next-intl'

interface RolePermissionEditorProps {
  role: RoleDetail
  onUpdated: () => void
}

const PAGE_DEFINITIONS = [
  { id: 'chat', label: 'AI Chat / Dashboard', description: 'Access to AI assistant and conversational analytics', icon: Sparkles },
  { id: 'ontology', label: 'Ontology Management', description: 'View and manage knowledge graph schema definitions', icon: Network },
  { id: 'instances', label: 'Instance Explorer', description: 'Browse and manage entity instances in the knowledge graph', icon: CircleDot },
  { id: 'data-products', label: 'Data Products', description: 'Configure and manage data source integrations', icon: Package },
  { id: 'rules', label: 'Rules Engine', description: 'Create and manage business rules for data processing', icon: Scale },
  { id: 'import', label: 'Graph Import', description: 'Import data into the knowledge graph', icon: Database },
  { id: 'config', label: 'System Configuration', description: 'Manage application-level settings', icon: Settings },
]

const ADMIN_PAGE = {
  id: 'admin',
  label: 'Administrator',
  description: 'Full admin access: manage users, assign roles, and configure system permissions',
  icon: Shield,
}

export function RolePermissionEditor({ role, onUpdated }: RolePermissionEditorProps) {
  const [loading, setLoading] = useState<string | null>(null)
  const locale = useLocale()
  const pagePermissions = role.page_permissions || []

  const handleTogglePage = async (pageId: string) => {
    setLoading(pageId)
    try {
      if (pagePermissions.includes(pageId)) {
        await rolesApi.removePagePermission(role.id, pageId)
        toast.success(`Permission revoked: ${pageId}`)
      } else {
        await rolesApi.addPagePermission(role.id, pageId)
        toast.success(`Permission granted: ${pageId}`)
      }
      onUpdated()
    } catch (error) {
      console.error('Failed to toggle page permission:', error)
      toast.error('Failed to update permission')
    } finally {
      setLoading(null)
    }
  }

  const isGranted = (pageId: string) => pagePermissions.includes(pageId)
  const isAdminGranted = isGranted('admin')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href={`/${locale}/admin/roles`}>
          <Button variant="ghost" size="sm" className="flex items-center gap-1.5">
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            {role.name}
            {role.is_system && (
              <span className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-500 uppercase font-bold tracking-wider">System</span>
            )}
          </h1>
          <p className="text-sm text-gray-500">{role.description || 'No description'}</p>
        </div>
      </div>

      {/* Admin Privilege Section */}
      <div className={`border-2 rounded-lg p-4 transition-colors ${isAdminGranted ? 'border-purple-300 bg-purple-50/50' : 'border-dashed border-gray-200'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isAdminGranted ? 'bg-purple-100 text-purple-600' : 'bg-gray-100 text-gray-400'}`}>
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-base">{ADMIN_PAGE.label}</h3>
              <p className="text-xs text-gray-500 max-w-md">{ADMIN_PAGE.description}</p>
            </div>
          </div>
          <Button
            variant={isAdminGranted ? 'default' : 'outline'}
            size="sm"
            className={isAdminGranted ? 'bg-purple-600 hover:bg-purple-700' : ''}
            onClick={() => handleTogglePage('admin')}
            disabled={loading === 'admin'}
          >
            {loading === 'admin' ? '...' : isAdminGranted ? (
              <span className="flex items-center gap-1"><Check className="w-3.5 h-3.5" /> Granted</span>
            ) : (
              <span className="flex items-center gap-1"><X className="w-3.5 h-3.5" /> Not Granted</span>
            )}
          </Button>
        </div>
      </div>

      {/* Page Permissions Section */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Page Access Permissions</h2>
        <div className="space-y-2">
          {PAGE_DEFINITIONS.map((page) => {
            const granted = isGranted(page.id)
            const Icon = page.icon
            return (
              <div
                key={page.id}
                className={`flex items-center justify-between border rounded-lg p-3 transition-colors ${granted ? 'border-green-200 bg-green-50/30' : 'border-gray-100 hover:border-gray-200'}`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-md flex items-center justify-center ${granted ? 'bg-green-100 text-green-600' : 'bg-gray-50 text-gray-400'}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-medium text-sm">{page.label}</h4>
                    <p className="text-xs text-gray-400">{page.description}</p>
                  </div>
                </div>
                <Button
                  variant={granted ? 'default' : 'outline'}
                  size="sm"
                  className={granted ? 'bg-green-600 hover:bg-green-700' : ''}
                  onClick={() => handleTogglePage(page.id)}
                  disabled={loading === page.id}
                >
                  {loading === page.id ? '...' : granted ? (
                    <span className="flex items-center gap-1"><Check className="w-3.5 h-3.5" /> Granted</span>
                  ) : 'Grant'}
                </Button>
              </div>
            )
          })}
        </div>
      </div>

      {role.is_system && (
        <p className="text-xs text-gray-400 italic mt-2">
          This is a system role. Its name and description cannot be modified, but you can configure its permissions.
        </p>
      )}
    </div>
  )
}
