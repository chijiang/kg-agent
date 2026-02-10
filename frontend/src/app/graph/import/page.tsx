// frontend/src/app/graph/import/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { graphApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { toast } from 'sonner'
import { Upload, Trash2, AlertTriangle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

export default function ImportPage() {
  const router = useRouter()
  const token = useAuthStore((state) => state.token)
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [isHydrated, setIsHydrated] = useState(false)
  const [showClearDialog, setShowClearDialog] = useState(false)

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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleImport = async () => {
    if (!file) return

    setLoading(true)
    try {
      const res = await graphApi.import(file, token)
      setResult(res.data)
      toast.success('图谱导入成功！')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '导入失败')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = async (clearOntology: boolean) => {
    setLoading(true)
    try {
      await graphApi.clear(clearOntology)
      setResult(null)
      toast.success(clearOntology ? '图谱（本体+实例）已清空' : '实例数据已清空')
      setShowClearDialog(false)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '清空失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">导入 OWL 图谱</h1>

        <Card>
          <CardHeader>
            <CardTitle>上传文件</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="border-2 border-dashed rounded-lg p-8 text-center">
              <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <input
                type="file"
                accept=".ttl,.owl,.rdf"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                <span className="text-primary hover:underline">
                  点击选择文件
                </span>
                <span className="text-gray-400 ml-2">或拖拽文件到此处</span>
              </label>
              {file && (
                <p className="mt-2 text-sm text-gray-600">已选择: {file.name}</p>
              )}
            </div>

            <Button onClick={handleImport} disabled={!file || loading} className="w-full bg-primary hover:opacity-90">
              {loading ? '处理中...' : '开始导入'}
            </Button>

            <Dialog open={showClearDialog} onOpenChange={setShowClearDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" disabled={loading} className="w-full text-red-500 hover:text-red-600 hover:bg-red-50">
                  <Trash2 className="w-4 h-4 mr-2" />
                  清空当前图谱
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px] justify-items-center">
                <DialogHeader className="flex flex-col items-center text-center sm:text-center w-full">
                  <DialogTitle className="flex items-center justify-center text-red-600 w-full text-center">
                    <AlertTriangle className="w-5 h-5 mr-2" />
                    清空图谱确认
                  </DialogTitle>
                  <DialogDescription className="text-center w-full">
                    请选择您要执行的清空操作。此操作不可恢复。
                  </DialogDescription>
                </DialogHeader>
                <div className="flex flex-col gap-4 py-4 w-full items-center">
                  <Button
                    variant="outline"
                    className="w-full flex h-auto py-4 px-4 border border-gray-300 hover:bg-red-50 hover:text-red-600 hover:border-red-300 justify-center text-center"
                    onClick={() => handleClear(false)}
                    disabled={loading}
                  >
                    <div className="flex flex-col items-center justify-center gap-1 text-center w-full">
                      <span className="font-bold text-base text-center">仅删除全部实例图谱</span>
                      <span className="text-sm opacity-80 font-normal text-center">保留本体（Ontology）定义，仅删除所有节点和关系实例。</span>
                    </div>
                  </Button>
                  <Button
                    variant="destructive"
                    className="w-full flex h-auto py-4 px-4 justify-center text-center"
                    onClick={() => handleClear(true)}
                    disabled={loading}
                  >
                    <div className="flex flex-col items-center justify-center gap-1 text-center w-full">
                      <span className="font-bold text-base text-center">删除全部（本体+实例）</span>
                      <span className="text-sm opacity-90 font-normal text-center">彻底清空图谱，包括所有类定义、关系定义及其所有实例。</span>
                    </div>
                  </Button>
                </div>
                <DialogFooter className="flex justify-center sm:justify-center w-full">
                  <Button variant="ghost" onClick={() => setShowClearDialog(false)} disabled={loading} className="mx-auto">
                    取消
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {result && (
              <div className="mt-4 p-4 bg-primary/5 border border-primary/20 rounded-lg">
                <h3 className="font-semibold text-primary">导入成功！</h3>
                <p className="text-sm text-slate-700">
                  Schema: {result.schema_stats.classes} 个类,
                  {result.schema_stats.properties} 个属性
                </p>
                <p className="text-sm text-slate-700">
                  Instance: {result.instance_stats.nodes} 个节点,
                  {result.instance_stats.relationships} 个关系
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
