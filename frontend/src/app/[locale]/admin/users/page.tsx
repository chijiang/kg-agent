// frontend/src/app/[locale]/admin/users/page.tsx
'use client'

import { ProtectedPage } from '@/components/auth/ProtectedPage'
import { AppLayout } from '@/components/layout'
import { UserList } from './components/UserList'

export default function UsersPage() {
  return (
    <AppLayout>
      <ProtectedPage pageId="admin">
        <div className="container mx-auto py-6">
          <h1 className="text-3xl font-bold mb-6">User Management</h1>
          <UserList />
        </div>
      </ProtectedPage>
    </AppLayout>
  )
}
