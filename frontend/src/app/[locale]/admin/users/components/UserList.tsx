// frontend/src/app/[locale]/admin/users/components/UserList.tsx
'use client'

import { useEffect, useState } from 'react'
import { usersApi, User } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { UserCreateDialog } from './UserCreateDialog'
import { UserEditDialog } from './UserEditDialog'
import { toast } from 'sonner'

export function UserList() {
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)

  const loadUsers = async () => {
    setLoading(true)
    try {
      const response = await usersApi.list()
      setUsers(response.data.items)
      setTotal(response.data.total)
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleResetPassword = async (userId: number) => {
    try {
      const response = await usersApi.resetPassword(userId)
      toast.success(`${response.data.message}. Default password: ${response.data.default_password}`)
    } catch (error) {
      console.error('Failed to reset password:', error)
      toast.error('Failed to reset password')
    }
  }

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) return

    try {
      await usersApi.delete(userId)
      toast.success('User deleted successfully')
      loadUsers()
    } catch (error: unknown) {
      console.error('Failed to delete user:', error)
      toast.error('Failed to delete user')
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl">Users ({total})</h2>
        <Button onClick={() => setShowCreate(true)}>Create User</Button>
      </div>

      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th className="text-left p-2">Username</th>
            <th className="text-left p-2">Email</th>
            <th className="text-left p-2">Status</th>
            <th className="text-left p-2">Admin</th>
            <th className="text-left p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className="border-b">
              <td className="p-2">{user.username}</td>
              <td className="p-2">{user.email || '-'}</td>
              <td className="p-2">
                <span className={`px-2 py-1 rounded text-sm ${user.approval_status === 'approved' ? 'bg-green-100 text-green-800' :
                  user.approval_status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                  {user.approval_status}
                </span>
              </td>
              <td className="p-2">{user.is_admin ? 'Yes' : 'No'}</td>
              <td className="p-2 space-x-2">
                <Button variant="outline" size="sm" onClick={() => setEditingUser(user)}>Edit</Button>
                <Button variant="outline" size="sm" onClick={() => handleResetPassword(user.id)}>Reset Password</Button>
                <Button variant="destructive" size="sm" onClick={() => handleDeleteUser(user.id)}>Delete</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showCreate && (
        <UserCreateDialog
          onClose={() => setShowCreate(false)}
          onCreated={loadUsers}
        />
      )}

      {editingUser && (
        <UserEditDialog
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onUpdated={loadUsers}
        />
      )}
    </div>
  )
}
