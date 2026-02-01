// frontend/src/components/graph-preview.tsx
'use client'

import { useEffect, useRef, useCallback } from 'react'
import cytoscape, { Core } from 'cytoscape'

interface GraphData {
  nodes: Array<{ id: string; label: string }>
  edges: Array<{ source: string; target: string; label?: string }>
}

export function GraphPreview({ data }: { data: GraphData | null }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const initializedRef = useRef(false)

  const hasData = data && data.nodes && data.nodes.length > 0

  // 初始化或更新图谱
  const initOrUpdateGraph = useCallback(() => {
    if (!containerRef.current || !hasData || !data) return

    // 如果 Cytoscape 未初始化，创建新实例
    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: containerRef.current,
        style: [
          {
            selector: 'node',
            style: {
              'label': 'data(label)',
              'text-valign': 'center',
              'text-halign': 'center',
              'background-color': '#4F46E5',
              'color': '#fff',
              'width': 50,
              'height': 50,
              'font-size': 10,
              'text-wrap': 'wrap',
              'text-max-width': 80,
            },
          },
          {
            selector: 'edge',
            style: {
              'width': 2,
              'line-color': '#94a3b8',
              'target-arrow-color': '#94a3b8',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'label': 'data(label)',
              'font-size': 8,
              'text-rotation': 'autorotate',
            },
          },
        ],
        // 禁用自动 resize
        autoungrabify: false,
        autounselectify: false,
      })
    }

    // 构建元素
    const elements = [
      ...data.nodes.map((n) => ({ data: { id: n.id, label: n.label } })),
      ...(data.edges || []).map((e, i) => ({
        data: { id: `e${i}`, source: e.source, target: e.target, label: e.label },
      })),
    ]

    // 更新图谱
    cyRef.current.json({ elements })
    cyRef.current.layout({
      name: 'cose',
      animate: false,
      fit: true,
      padding: 30,
    }).run()

    initializedRef.current = true
  }, [hasData, data])

  // 当数据变化时更新图谱
  useEffect(() => {
    if (hasData) {
      // 使用 setTimeout 确保 DOM 已渲染
      const timer = setTimeout(() => {
        initOrUpdateGraph()
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [hasData, data, initOrUpdateGraph])

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (cyRef.current) {
        cyRef.current.destroy()
        cyRef.current = null
      }
    }
  }, [])

  return (
    <div className="h-full bg-white rounded-lg border overflow-hidden" style={{ minHeight: '300px' }}>
      {hasData ? (
        <div
          ref={containerRef}
          style={{
            width: '100%',
            height: '100%',
            minHeight: '300px',
            maxHeight: '500px',
          }}
        />
      ) : (
        <div className="flex items-center justify-center h-full text-gray-400" style={{ minHeight: '300px' }}>
          暂无图谱数据
        </div>
      )}
    </div>
  )
}
