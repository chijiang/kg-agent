// frontend/src/app/[locale]/admin/users/components/UserEditDialog.tsx
'use client'

import { useState, useEffect } from 'react'
import { usersApi, rolesApi, User, Role } from '@/lib/api'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'

interface UserEditDialogProps {
    user: User
    onClose: () => void
    onUpdated: () => void
}

export function UserEditDialog({ user, onClose, onUpdated }: UserEditDialogProps) {
    const [email, setEmail] = useState(user.email || '')
    const [loading, setLoading] = useState(false)
    const [loadingRoles, setLoadingRoles] = useState(true)
    const [availableRoles, setAvailableRoles] = useState<Role[]>([])
    const [userRoles, setUserRoles] = useState<Role[]>([])

    useEffect(() => {
        async function loadRoles() {
            try {
                const [allRolesRes, userRolesRes] = await Promise.all([
                    rolesApi.list(),
                    usersApi.getRoles(user.id)
                ])
                setAvailableRoles(allRolesRes.data)
                setUserRoles(userRolesRes.data)
            } catch (error) {
                console.error('Failed to load roles:', error)
                toast.error('Failed to load roles')
            } finally {
                setLoadingRoles(false)
            }
        }
        loadRoles()
    }, [user.id])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)

        try {
            await usersApi.update(user.id, { email: email || undefined })
            toast.success('User updated successfully')
            onUpdated()
            onClose()
        } catch (error) {
            console.error('Failed to update user:', error)
            toast.error('Failed to update user')
        } finally {
            setLoading(false)
        }
    }

    const handleToggleRole = async (roleId: number, checked: boolean) => {
        try {
            if (checked) {
                await usersApi.assignRole(user.id, roleId)
                toast.success('Role assigned')
                // Optimistic update
                const role = availableRoles.find(r => r.id === roleId)
                if (role) setUserRoles(prev => [...prev, role])
            } else {
                await usersApi.removeRole(user.id, roleId)
                toast.success('Role removed')
                setUserRoles(prev => prev.filter(r => r.id !== roleId))
            }
        } catch (error) {
            console.error('Failed to update role:', error)
            toast.error('Failed to update role')
        }
    }

    const isAssigned = (roleId: number) => userRoles.some(r => r.id === roleId)

    return (
        <Dialog open onOpenChange={onClose}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>Edit User: {user.username}</DialogTitle>
                </DialogHeader>

                <div className="space-y-6">
                    {/* User Info Form */}
                    <form onSubmit={handleSubmit} className="space-y-4 border-b pb-4">
                        <div>
                            <label className="block text-sm font-medium mb-1">Email</label>
                            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                        </div>
                        <div className="flex justify-end gap-2">
                            <Button type="submit" disabled={loading}>
                                {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                                Save Email
                            </Button>
                        </div>
                    </form>

                    {/* Role Management */}
                    <div className="space-y-3">
                        <h3 className="font-medium">Manage Roles</h3>
                        {loadingRoles ? (
                            <div className="flex items-center text-sm text-gray-500">
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                Loading roles...
                            </div>
                        ) : (
                            <div className="space-y-2 max-h-48 overflow-y-auto border rounded-md p-2">
                                {availableRoles.map(role => (
                                    <div key={role.id} className="flex items-start space-x-2 p-1 hover:bg-gray-50 rounded">
                                        <Checkbox
                                            id={`role-${role.id}`}
                                            checked={isAssigned(role.id)}
                                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleToggleRole(role.id, e.target.checked)}
                                        />
                                        <div className="grid gap-1.5 leading-none">
                                            <label
                                                htmlFor={`role-${role.id}`}
                                                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                                            >
                                                {role.name}
                                                {role.is_system && <span className="ml-2 text-xs text-gray-400 font-normal">(System)</span>}
                                            </label>
                                            {role.description && (
                                                <p className="text-xs text-gray-500">
                                                    {role.description}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex justify-end pt-2">
                    <Button type="button" variant="outline" onClick={onClose}>Close</Button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
