// frontend/src/app/dashboard/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { Chat } from '@/components/chat'
import { GraphPreview } from '@/components/graph-preview'
import { useAuthStore } from '@/lib/auth'

export default function DashboardPage() {
  const router = useRouter()
  const token = useAuthStore((state) => state.token)
  const [graphData, setGraphData] = useState<any>(null)

  if (!token) {
    router.push('/')
    return null
  }

  return (
    <AppLayout>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-200px)]">
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-4">问答</h2>
          <Chat onGraphData={setGraphData} />
        </div>
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-4">图谱预览</h2>
          <GraphPreview data={graphData} />
        </div>
      </div>
    </AppLayout>
  )
}
