// frontend/src/components/ontology-detail-panel.tsx
'use client'

import { useEffect, useState } from 'react'
import { graphApi, actionsApi, ActionInfo } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { X, Database, ArrowRight, Zap } from 'lucide-react'

interface OntologyNode {
    name: string
    label?: string
    dataProperties?: string[]
}

interface Relationship {
    source: string
    type: string
    target: string
    direction: 'outgoing' | 'incoming'
}

interface OntologyDetailPanelProps {
    node: OntologyNode | null
    onClose: () => void
}

export function OntologyDetailPanel({ node, onClose }: OntologyDetailPanelProps) {
    const token = useAuthStore((state) => state.token)
    const [relationships, setRelationships] = useState<Relationship[]>([])
    const [actions, setActions] = useState<ActionInfo[]>([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (node && token) {
            loadDetails()
        }
    }, [node, token])

    const loadDetails = async () => {
        if (!node || !token) return
        setLoading(true)

        try {
            // 加载关系信息
            const schemaRes = await graphApi.getSchema(token)
            const rels: Relationship[] = []

            schemaRes.data.relationships?.forEach((rel: any) => {
                if (rel.source === node.name) {
                    rels.push({
                        source: rel.source,
                        type: rel.type,
                        target: rel.target,
                        direction: 'outgoing'
                    })
                }
                if (rel.target === node.name) {
                    rels.push({
                        source: rel.source,
                        type: rel.type,
                        target: rel.target,
                        direction: 'incoming'
                    })
                }
            })
            setRelationships(rels)

            // 加载动作信息
            try {
                const actionsRes = await actionsApi.list()
                const relatedActions = actionsRes.data.actions?.filter(
                    (action: ActionInfo) => action.entity_type === node.name
                ) || []
                setActions(relatedActions)
            } catch (err) {
                console.error('Failed to load actions:', err)
                setActions([])
            }
        } catch (err) {
            console.error('Failed to load ontology details:', err)
        } finally {
            setLoading(false)
        }
    }

    if (!node) return null

    return (
        <div className="bg-white rounded-lg shadow-lg border h-full flex flex-col">
            {/* 头部 */}
            <div className="p-4 border-b flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
                        <Database className="h-4 w-4 text-white" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-gray-800">{node.name}</h3>
                        {node.label && <p className="text-xs text-gray-500">{node.label}</p>}
                    </div>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 hover:bg-gray-200 rounded transition-colors"
                >
                    <X className="h-4 w-4 text-gray-500" />
                </button>
            </div>

            {/* 内容 */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
                {loading ? (
                    <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
                    </div>
                ) : (
                    <>
                        {/* 属性 */}
                        <section>
                            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-blue-500" />
                                属性 (Properties)
                            </h4>
                            {node.dataProperties && node.dataProperties.length > 0 ? (
                                <div className="space-y-2">
                                    {node.dataProperties.map((prop, i) => (
                                        <div
                                            key={i}
                                            className="px-3 py-2 bg-gray-50 rounded-lg text-sm text-gray-700 border border-gray-100"
                                        >
                                            {prop}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-gray-400 italic">暂无属性定义</p>
                            )}
                        </section>

                        {/* 关系 */}
                        <section>
                            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-green-500" />
                                关系 (Relationships)
                            </h4>
                            {relationships.length > 0 ? (
                                <div className="space-y-2">
                                    {relationships.map((rel, i) => (
                                        <div
                                            key={i}
                                            className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg text-sm border border-gray-100"
                                        >
                                            {rel.direction === 'outgoing' ? (
                                                <>
                                                    <span className="font-medium text-blue-600">{rel.source}</span>
                                                    <ArrowRight className="h-3 w-3 text-gray-400" />
                                                    <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                                                        {rel.type}
                                                    </span>
                                                    <ArrowRight className="h-3 w-3 text-gray-400" />
                                                    <span className="text-gray-600">{rel.target}</span>
                                                </>
                                            ) : (
                                                <>
                                                    <span className="text-gray-600">{rel.source}</span>
                                                    <ArrowRight className="h-3 w-3 text-gray-400" />
                                                    <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs">
                                                        {rel.type}
                                                    </span>
                                                    <ArrowRight className="h-3 w-3 text-gray-400" />
                                                    <span className="font-medium text-blue-600">{rel.target}</span>
                                                </>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-gray-400 italic">暂无关系定义</p>
                            )}
                        </section>

                        {/* 动作 */}
                        <section>
                            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-purple-500" />
                                动作 (Actions)
                            </h4>
                            {actions.length > 0 ? (
                                <div className="space-y-2">
                                    {actions.map((action) => (
                                        <div
                                            key={action.id}
                                            className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg text-sm border border-gray-100"
                                        >
                                            <div className="flex items-center gap-2">
                                                <Zap className="h-4 w-4 text-purple-500" />
                                                <span className="font-medium text-gray-700">{action.name}</span>
                                            </div>
                                            <span className={`px-2 py-0.5 rounded text-xs ${action.is_active
                                                    ? 'bg-green-100 text-green-700'
                                                    : 'bg-gray-100 text-gray-500'
                                                }`}>
                                                {action.is_active ? '已启用' : '未启用'}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-gray-400 italic">暂无关联动作</p>
                            )}
                        </section>
                    </>
                )}
            </div>
        </div>
    )
}
