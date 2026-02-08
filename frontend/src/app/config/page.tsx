// frontend/src/app/config/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { configApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { toast } from 'sonner'
import { Eye, EyeOff } from 'lucide-react'

export default function ConfigPage() {
  const router = useRouter()
  const token = useAuthStore((state) => state.token)
  const [loading, setLoading] = useState(false)

  const [llm, setLLM] = useState({ api_key: '', base_url: '', model: '' })
  const [showApiKey, setShowApiKey] = useState(false)
  const [isHydrated, setIsHydrated] = useState(false)

  useEffect(() => {
    setIsHydrated(true)
  }, [])

  useEffect(() => {
    if (isHydrated && !token) {
      router.push('/')
      return
    }
    if (isHydrated && token) {
      loadConfigs()
    }
  }, [isHydrated, token, router])

  if (!isHydrated || !token) {
    return null
  }

  const loadConfigs = async () => {
    try {
      const llmRes = await configApi.getLLM()
      setLLM({
        ...llmRes.data,
        api_key: llmRes.data.has_api_key ? '************' : ''
      })
    } catch (err) {
      console.error('Failed to load configs')
    }
  }

  const handleTestLLM = async () => {
    try {
      const res = await configApi.testLLM(llm)
      if (res.data.success) {
        toast.success('LLM 连接成功')
      } else {
        toast.error(res.data.message)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '连接失败')
    }
  }

  const handleSaveLLM = async () => {
    setLoading(true)
    try {
      await configApi.updateLLM(llm)
      toast.success('LLM 配置已保存')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">配置管理</h1>

        <Tabs defaultValue="llm">
          <TabsList className="grid w-full grid-cols-1">
            <TabsTrigger value="llm">LLM 配置</TabsTrigger>
          </TabsList>

          <TabsContent value="llm">
            <Card>
              <CardHeader>
                <CardTitle>LLM API 配置</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="relative">
                  <Input
                    placeholder="API Key"
                    type={showApiKey ? "text" : "password"}
                    value={llm.api_key}
                    onChange={(e) => setLLM({ ...llm, api_key: e.target.value })}
                    autoComplete="new-password"
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <Input
                  placeholder="Base URL (如 https://api.openai.com/v1)"
                  value={llm.base_url}
                  onChange={(e) => setLLM({ ...llm, base_url: e.target.value })}
                />
                <Input
                  placeholder="Model (如 gpt-4)"
                  value={llm.model}
                  onChange={(e) => setLLM({ ...llm, model: e.target.value })}
                />
                <div className="flex gap-2">
                  <Button onClick={handleSaveLLM} disabled={loading}>
                    保存
                  </Button>
                  <Button variant="outline" onClick={handleTestLLM}>
                    测试连接
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  )
}
