// frontend/src/app/dashboard/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { Chat } from '@/components/chat'
import { GraphPreview } from '@/components/graph-preview'
import { useAuthStore } from '@/lib/auth'
import { MessageSquare, Network } from 'lucide-react'

export default function DashboardPage() {
  const router = useRouter()
  const token = useAuthStore((state) => state.token)
  const [graphData, setGraphData] = useState<any>(null)
  const [isHydrated, setIsHydrated] = useState(false)

  useEffect(() => {
    setIsHydrated(true)
  }, [])

  useEffect(() => {
    if (isHydrated && !token) {
      router.push('/')
    }
  }, [isHydrated, token, router])

  if (!isHydrated || !token) {
    return null
  }

  return (
    <AppLayout>
      <div className="h-[calc(100vh-100px)] p-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">
          {/* 问答区域 */}
          <div className="flex flex-col bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-100 bg-slate-50">
              <div className="p-2 rounded-lg bg-indigo-600">
                <MessageSquare className="h-5 w-5 text-white" />
              </div>
              <h2 className="text-lg font-semibold text-slate-800">智能问答</h2>
            </div>
            <div className="flex-1 overflow-hidden">
              <Chat onGraphData={setGraphData} />
            </div>
          </div>

          {/* 图谱区域 */}
          <div className="flex flex-col bg-slate-900 rounded-2xl shadow-lg overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-700">
              <div className="p-2 rounded-lg bg-emerald-600">
                <Network className="h-5 w-5 text-white" />
              </div>
              <h2 className="text-lg font-semibold text-white">知识图谱</h2>
            </div>
            <div className="flex-1 overflow-hidden">
              <GraphPreview data={graphData} />
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
