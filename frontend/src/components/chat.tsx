// frontend/src/components/chat.tsx
'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { chatApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { Send } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  graphData?: any
}

export function Chat({ onGraphData }: { onGraphData: (data: any) => void }) {
  const token = useAuthStore((state) => state.token)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const response = await chatApi.stream(userMessage, token!)
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()

      let assistantMessage = ''
      let thinking = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n').filter(Boolean)

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))

            if (data.type === 'thinking') {
              thinking = data.content
              setMessages((prev) => {
                const newMsgs = [...prev]
                const last = newMsgs[newMsgs.length - 1]
                if (last?.role === 'assistant') {
                  last.thinking = thinking
                } else {
                  newMsgs.push({ role: 'assistant', content: '', thinking })
                }
                return newMsgs
              })
            } else if (data.type === 'content') {
              assistantMessage += data.content
              setMessages((prev) => {
                const newMsgs = [...prev]
                const last = newMsgs[newMsgs.length - 1]
                if (last?.role === 'assistant') {
                  last.content = assistantMessage
                } else {
                  newMsgs.push({ role: 'assistant', content: assistantMessage })
                }
                return newMsgs
              })
            } else if (data.type === 'graph_data') {
              const graphData = { nodes: data.nodes || [], edges: data.edges || [] }
              onGraphData(graphData)
              setMessages((prev) => {
                const newMsgs = [...prev]
                const last = newMsgs[newMsgs.length - 1]
                if (last) {
                  last.graphData = graphData
                }
                return newMsgs
              })
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    } catch (err) {
      console.error('Chat error:', err)
      setMessages((prev) => [...prev, { role: 'assistant', content: '抱歉，发生了错误。' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-20">
            <p>开始提问吧！例如：</p>
            <p className="mt-2">"PO_2024_001 是向哪个供应商订购的？"</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <Card
              className={`max-w-[80%] p-3 ${msg.role === 'user' ? 'bg-blue-50' : 'bg-gray-50'
                }`}
            >
              {msg.thinking && (
                <p className="text-xs text-gray-500 mb-2">💭 {msg.thinking}</p>
              )}
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.graphData && (
                <p className="text-xs text-green-600 mt-2">📊 相关图谱已显示</p>
              )}
            </Card>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <Card className="bg-gray-50 p-3">
              <p className="text-gray-500">正在思考...</p>
            </Card>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入你的问题..."
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  )
}
