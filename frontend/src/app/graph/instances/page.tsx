// frontend/src/app/graph/instances/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { InstanceFilter, SearchParams } from '@/components/instance-filter'
import { InstanceGraphViewer } from '@/components/instance-graph-viewer'
import { InstanceDetailPanel } from '@/components/instance-detail-panel'
import { useAuthStore } from '@/lib/auth'

interface InstanceNode {
    id: string
    name: string
    label: string
    nodeLabel: string
    properties?: Record<string, any>
    color?: string
}

export default function InstancesPage() {
    const router = useRouter()
    const token = useAuthStore((state) => state.token)
    const [isHydrated, setIsHydrated] = useState(false)
    const [searchParams, setSearchParams] = useState<SearchParams | null>(null)
    const [selectedNode, setSelectedNode] = useState<InstanceNode | null>(null)
    const [loading, setLoading] = useState(false)
    const [refreshTrigger, setRefreshTrigger] = useState(0)

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

    const handleSearch = (params: SearchParams) => {
        setLoading(true)
        setSearchParams(params)
        setSelectedNode(null)
        // 将在 InstanceGraphViewer 中处理加载
        setTimeout(() => setLoading(false), 100)
    }

    const handleUpdate = () => {
        // 触发图谱刷新
        setRefreshTrigger(prev => prev + 1)
    }

    return (
        <AppLayout>
            <div className="h-[calc(100vh-120px)] flex flex-col gap-4">
                {/* 筛选条件区域 */}
                <InstanceFilter onSearch={handleSearch} loading={loading} />

                {/* 图谱和详情区域 */}
                <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
                    {/* 实例图谱 */}
                    <div className={`bg-white rounded-lg border overflow-hidden ${selectedNode ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
                        <InstanceGraphViewer
                            searchParams={searchParams}
                            onNodeSelect={setSelectedNode}
                            refreshTrigger={refreshTrigger}
                        />
                    </div>

                    {/* 实例详情面板 */}
                    {selectedNode && (
                        <div className="lg:col-span-1">
                            <InstanceDetailPanel
                                node={selectedNode}
                                onClose={() => setSelectedNode(null)}
                                onUpdate={handleUpdate}
                            />
                        </div>
                    )}
                </div>
            </div>
        </AppLayout>
    )
}
