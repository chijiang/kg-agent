// frontend/src/app/graph/ontology/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { SchemaViewer } from '@/components/schema-viewer'
import { OntologyDetailPanel } from '@/components/ontology-detail-panel'
import { useAuthStore } from '@/lib/auth'

interface OntologyNode {
    name: string
    label?: string
    dataProperties?: string[]
}

export default function OntologyPage() {
    const router = useRouter()
    const token = useAuthStore((state) => state.token)
    const [isHydrated, setIsHydrated] = useState(false)
    const [selectedNode, setSelectedNode] = useState<OntologyNode | null>(null)

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
            <div className="h-[calc(100vh-120px)]">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-full">
                    {/* 左侧：本体图谱 */}
                    <div className={`bg-white rounded-lg border overflow-hidden ${selectedNode ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
                        <SchemaViewer onNodeSelect={setSelectedNode} />
                    </div>

                    {/* 右侧：本体详情面板 */}
                    {selectedNode && (
                        <div className="lg:col-span-1">
                            <OntologyDetailPanel
                                node={selectedNode}
                                onClose={() => setSelectedNode(null)}
                            />
                        </div>
                    )}
                </div>
            </div>
        </AppLayout>
    )
}
