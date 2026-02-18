// frontend/src/lib/auth.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  username: string
  is_admin?: boolean
  approval_status?: 'pending' | 'approved' | 'rejected'
  is_password_changed?: boolean
}

interface AuthState {
  user: User | null
  token: string | null
  permissions: {
    accessible_pages: string[]
    accessible_actions: Record<string, string[]>
    accessible_entities: string[]
    is_admin: boolean
  } | null
  setAuth: (user: User, token: string) => void
  setPermissions: (permissions: AuthState['permissions']) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      permissions: null,
      setAuth: (user, token) => set({ user, token }),
      setPermissions: (permissions) => set({ permissions }),
      logout: () => set({ user: null, token: null, permissions: null }),
    }),
    { name: 'auth-storage' }
  )
)
