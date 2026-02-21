'use client'

import { useState } from 'react'
import { rolesApi } from '@/lib/api'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'

interface RoleCreateDialogProps {
    roleType: 'system' | 'business'
    onClose: () => void
    onCreated: () => void
}

export function RoleCreateDialog({ roleType, onClose, onCreated }: RoleCreateDialogProps) {
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)

        try {
            await rolesApi.create({ name, description: description || undefined, role_type: roleType })
            toast.success('Role created successfully')
            onCreated()
            onClose()
        } catch (error: unknown) {
            const message = (error as any).response?.data?.detail || 'Failed to create role'
            console.error('Failed to create role:', error)
            toast.error(message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <Dialog open onOpenChange={onClose}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Create New {roleType === 'business' ? 'Business' : 'System'} Role</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-1">Role Name</label>
                        <Input
                            placeholder="e.g., DataScientist"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Description</label>
                        <Input
                            placeholder="Briefly describe the role's purpose"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                        />
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
                        <Button type="submit" disabled={loading}>Create Role</Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    )
}
