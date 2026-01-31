// frontend/src/components/graph-preview.tsx
'use client'

import { useEffect, useRef } from 'react'
import cytoscape, { Core } from 'cytoscape'

interface GraphData {
  nodes: Array<{ id: string; label: string }>
  edges: Array<{ source: string; target: string; label?: string }>
}

export function GraphPreview({ data }: { data: GraphData | null }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

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
              'width': '40px',
              'height': '40px',
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
            },
          },
        ],
        layout: {
          name: 'breadthfirst',
          directed: true,
        },
      })
    }

    return () => {
      cyRef.current?.destroy()
      cyRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!cyRef.current || !data) return

    const elements = [
      ...data.nodes.map((n) => ({ data: { id: n.id, label: n.label } })),
      ...data.edges.map((e, i) => ({
        data: { id: `e${i}`, source: e.source, target: e.target, label: e.label },
      })),
    ]

    cyRef.current.json({ elements })
    cyRef.current.layout({ name: 'breadthfirst' }).run()
    cyRef.current.fit()
  }, [data])

  return (
    <div className="h-full bg-white rounded-lg border overflow-hidden">
      {data ? (
        <div ref={containerRef} className="w-full h-full" />
      ) : (
        <div className="flex items-center justify-center h-full text-gray-400">
          暂无图谱数据
        </div>
      )}
    </div>
  )
}
