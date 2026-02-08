'use client'

import { useState, useEffect, use } from 'react'
import { useRouter } from 'next/navigation'
import {
    ArrowLeft,
    Plus,
    Trash2,
    RefreshCw,
    Link2,
    ChevronDown,
    ChevronRight,
    Server,
    Box,
    ArrowRight,
    Check,
    X
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle
} from '@/components/ui/card'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import {
    dataProductsApi,
    dataMappingsApi,
    graphApi,
    DataProduct,
    EntityMapping,
    PropertyMapping,
    SyncDirection
} from '@/lib/api'

interface OntologyClass {
    name: string
    label: string
    data_properties: string[]
}

export default function DataMappingsPage({ params }: { params: Promise<{ id: string }> }) {
    const resolvedParams = use(params)
    const productId = parseInt(resolvedParams.id)
    const router = useRouter()

    const [product, setProduct] = useState<DataProduct | null>(null)
    const [entityMappings, setEntityMappings] = useState<EntityMapping[]>([])
    const [ontologyClasses, setOntologyClasses] = useState<OntologyClass[]>([])
    const [loading, setLoading] = useState(true)

    // Entity mapping dialog
    const [entityDialogOpen, setEntityDialogOpen] = useState(false)
    const [entityForm, setEntityForm] = useState({
        ontology_class_name: '',
        grpc_message_type: '',
        list_method: '',
        sync_direction: 'pull' as SyncDirection,
    })
    const [creatingEntity, setCreatingEntity] = useState(false)

    // Property mapping state
    const [expandedMapping, setExpandedMapping] = useState<number | null>(null)
    const [propertyMappings, setPropertyMappings] = useState<Record<number, PropertyMapping[]>>({})
    const [loadingProperties, setLoadingProperties] = useState<number | null>(null)

    // Property mapping dialog
    const [propertyDialogOpen, setPropertyDialogOpen] = useState(false)
    const [selectedEntityMapping, setSelectedEntityMapping] = useState<EntityMapping | null>(null)
    const [propertyForm, setPropertyForm] = useState({
        ontology_property: '',
        grpc_field: '',
    })
    const [creatingProperty, setCreatingProperty] = useState(false)

    const loadData = async () => {
        try {
            setLoading(true)

            // Load product info
            const productRes = await dataProductsApi.get(productId)
            setProduct(productRes.data)

            // Load entity mappings
            const mappingsRes = await dataProductsApi.getEntityMappings(productId)
            setEntityMappings(mappingsRes.data.items)

            // Load ontology classes
            const token = localStorage.getItem('auth-storage')
            if (token) {
                const schemaRes = await graphApi.getSchema(JSON.parse(token).state.token)
                const classes = schemaRes.data.nodes
                    ?.filter((n: any) => n.data?.type === 'class')
                    .map((n: any) => ({
                        name: n.data?.name || n.id,
                        label: n.data?.label || n.data?.name || n.id,
                        data_properties: n.data?.data_properties || [],
                    })) || []
                setOntologyClasses(classes)
            }
        } catch (error) {
            toast.error('加载失败', {
                description: '无法加载数据',
            })
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (productId) {
            loadData()
        }
    }, [productId])

    const loadPropertyMappings = async (entityMappingId: number) => {
        try {
            setLoadingProperties(entityMappingId)
            const res = await dataMappingsApi.listPropertyMappings(entityMappingId)
            setPropertyMappings(prev => ({
                ...prev,
                [entityMappingId]: res.data,
            }))
        } catch (error) {
            toast.error('加载失败', {
                description: '无法加载属性映射',
            })
        } finally {
            setLoadingProperties(null)
        }
    }

    const handleExpandMapping = (mappingId: number) => {
        if (expandedMapping === mappingId) {
            setExpandedMapping(null)
        } else {
            setExpandedMapping(mappingId)
            if (!propertyMappings[mappingId]) {
                loadPropertyMappings(mappingId)
            }
        }
    }

    const handleCreateEntityMapping = async () => {
        if (!entityForm.ontology_class_name || !entityForm.grpc_message_type) {
            toast.error('验证失败', {
                description: '请选择 Ontology 类和 gRPC 消息类型',
            })
            return
        }

        try {
            setCreatingEntity(true)
            await dataMappingsApi.createEntityMapping({
                data_product_id: productId,
                ...entityForm,
            })
            toast.success('创建成功', {
                description: '实体映射已创建',
            })
            setEntityDialogOpen(false)
            setEntityForm({
                ontology_class_name: '',
                grpc_message_type: '',
                list_method: '',
                sync_direction: 'pull',
            })
            loadData()
        } catch (error: any) {
            toast.error('创建失败', {
                description: error.response?.data?.detail || '请检查输入',
            })
        } finally {
            setCreatingEntity(false)
        }
    }

    const handleDeleteEntityMapping = async (mappingId: number) => {
        if (!confirm('确定要删除此实体映射吗？所有属性映射也会被删除。')) {
            return
        }

        try {
            await dataMappingsApi.deleteEntityMapping(mappingId)
            toast.success('删除成功', {
                description: '实体映射已删除',
            })
            loadData()
        } catch (error: any) {
            toast.error('删除失败', {
                description: error.response?.data?.detail || '删除出错',
            })
        }
    }

    const handleOpenPropertyDialog = (mapping: EntityMapping) => {
        setSelectedEntityMapping(mapping)
        setPropertyDialogOpen(true)
    }

    const handleCreatePropertyMapping = async () => {
        if (!selectedEntityMapping || !propertyForm.ontology_property || !propertyForm.grpc_field) {
            toast.error('验证失败', {
                description: '请填写必填字段',
            })
            return
        }

        try {
            setCreatingProperty(true)
            await dataMappingsApi.createPropertyMapping(selectedEntityMapping.id, propertyForm)
            toast.success('创建成功', {
                description: '属性映射已创建',
            })
            setPropertyDialogOpen(false)
            setPropertyForm({ ontology_property: '', grpc_field: '' })
            loadPropertyMappings(selectedEntityMapping.id)
            loadData() // Refresh count
        } catch (error: any) {
            toast.error('创建失败', {
                description: error.response?.data?.detail || '请检查输入',
            })
        } finally {
            setCreatingProperty(false)
        }
    }

    const handleDeletePropertyMapping = async (propId: number, entityMappingId: number) => {
        try {
            await dataMappingsApi.deletePropertyMapping(propId)
            toast.success('删除成功', {
                description: '属性映射已删除',
            })
            loadPropertyMappings(entityMappingId)
            loadData()
        } catch (error: any) {
            toast.error('删除失败', {
                description: error.response?.data?.detail || '删除出错',
            })
        }
    }

    const getSelectedClass = () => {
        return ontologyClasses.find(c => c.name === entityForm.ontology_class_name)
    }

    const getSelectedMappingClass = () => {
        if (!selectedEntityMapping) return null
        return ontologyClasses.find(c => c.name === selectedEntityMapping.ontology_class_name)
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
        )
    }

    return (
        <div className="container mx-auto py-8 px-4 max-w-6xl">
            {/* Header */}
            <div className="flex items-center gap-4 mb-8">
                <Button variant="ghost" size="icon" onClick={() => router.push('/data-products')}>
                    <ArrowLeft className="w-5 h-5" />
                </Button>
                <div className="flex-1">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-lg">
                            <Server className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold">{product?.name}</h1>
                            <p className="text-muted-foreground text-sm">
                                {product?.grpc_host}:{product?.grpc_port} / {product?.service_name}
                            </p>
                        </div>
                    </div>
                </div>

                <Dialog open={entityDialogOpen} onOpenChange={setEntityDialogOpen}>
                    <DialogTrigger asChild>
                        <Button>
                            <Plus className="w-4 h-4 mr-2" />
                            添加实体映射
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[500px]">
                        <DialogHeader>
                            <DialogTitle>添加实体映射</DialogTitle>
                            <DialogDescription>
                                将 Ontology 中的类映射到数据产品的 gRPC 消息类型
                            </DialogDescription>
                        </DialogHeader>

                        <div className="grid gap-4 py-4">
                            <div className="grid gap-2">
                                <Label>Ontology 类 *</Label>
                                <Select
                                    value={entityForm.ontology_class_name}
                                    onValueChange={(v: string) => setEntityForm({ ...entityForm, ontology_class_name: v })}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="选择 Ontology 类" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {ontologyClasses.map((cls) => (
                                            <SelectItem key={cls.name} value={cls.name}>
                                                {cls.label || cls.name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="grid gap-2">
                                <Label>gRPC 消息类型 *</Label>
                                <Input
                                    placeholder="例如: erp.Supplier"
                                    value={entityForm.grpc_message_type}
                                    onChange={(e) => setEntityForm({ ...entityForm, grpc_message_type: e.target.value })}
                                />
                            </div>

                            <div className="grid gap-2">
                                <Label>List 方法名称</Label>
                                <Input
                                    placeholder="例如: ListSuppliers"
                                    value={entityForm.list_method}
                                    onChange={(e) => setEntityForm({ ...entityForm, list_method: e.target.value })}
                                />
                            </div>

                            <div className="grid gap-2">
                                <Label>同步方向</Label>
                                <Select
                                    value={entityForm.sync_direction}
                                    onValueChange={(v: SyncDirection) => setEntityForm({ ...entityForm, sync_direction: v })}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="pull">从数据源拉取</SelectItem>
                                        <SelectItem value="push">推送到数据源</SelectItem>
                                        <SelectItem value="bidirectional">双向同步</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <DialogFooter>
                            <Button variant="outline" onClick={() => setEntityDialogOpen(false)}>
                                取消
                            </Button>
                            <Button onClick={handleCreateEntityMapping} disabled={creatingEntity}>
                                {creatingEntity ? '创建中...' : '创建'}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>

            {/* Entity Mappings List */}
            {entityMappings.length === 0 ? (
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-12">
                        <Link2 className="w-12 h-12 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium mb-2">尚未配置映射</h3>
                        <p className="text-muted-foreground text-sm mb-4">
                            添加实体映射以将 Ontology 类关联到 gRPC 消息类型
                        </p>
                        <Button onClick={() => setEntityDialogOpen(true)}>
                            <Plus className="w-4 h-4 mr-2" />
                            添加实体映射
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-4">
                    {entityMappings.map((mapping) => (
                        <Card key={mapping.id}>
                            <CardHeader
                                className="pb-3 cursor-pointer"
                                onClick={() => handleExpandMapping(mapping.id)}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        {expandedMapping === mapping.id ? (
                                            <ChevronDown className="w-5 h-5 text-muted-foreground" />
                                        ) : (
                                            <ChevronRight className="w-5 h-5 text-muted-foreground" />
                                        )}

                                        <div className="flex items-center gap-3">
                                            <div className="p-1.5 bg-blue-500/10 rounded">
                                                <Box className="w-4 h-4 text-blue-500" />
                                            </div>
                                            <span className="font-medium">{mapping.ontology_class_name}</span>
                                        </div>

                                        <ArrowRight className="w-4 h-4 text-muted-foreground" />

                                        <div className="flex items-center gap-3">
                                            <div className="p-1.5 bg-green-500/10 rounded">
                                                <Server className="w-4 h-4 text-green-500" />
                                            </div>
                                            <span className="font-medium">{mapping.grpc_message_type}</span>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3" onClick={(e) => e.stopPropagation()}>
                                        <span className="text-xs text-muted-foreground">
                                            {mapping.property_mapping_count} 属性映射
                                        </span>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="text-red-500 hover:text-red-600"
                                            onClick={() => handleDeleteEntityMapping(mapping.id)}
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>
                            </CardHeader>

                            {expandedMapping === mapping.id && (
                                <CardContent className="pt-0">
                                    <div className="border-t pt-4">
                                        <div className="flex items-center justify-between mb-3">
                                            <h4 className="text-sm font-medium">属性映射</h4>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => handleOpenPropertyDialog(mapping)}
                                            >
                                                <Plus className="w-4 h-4 mr-1" />
                                                添加属性
                                            </Button>
                                        </div>

                                        {loadingProperties === mapping.id ? (
                                            <div className="flex items-center justify-center py-4">
                                                <RefreshCw className="w-4 h-4 animate-spin text-muted-foreground" />
                                            </div>
                                        ) : (propertyMappings[mapping.id]?.length || 0) === 0 ? (
                                            <p className="text-sm text-muted-foreground text-center py-4">
                                                暂无属性映射，点击上方按钮添加
                                            </p>
                                        ) : (
                                            <div className="space-y-2">
                                                {propertyMappings[mapping.id]?.map((prop) => (
                                                    <div
                                                        key={prop.id}
                                                        className="flex items-center justify-between p-2 bg-muted/50 rounded-lg"
                                                    >
                                                        <div className="flex items-center gap-4">
                                                            <span className="text-sm font-mono">{prop.ontology_property}</span>
                                                            <ArrowRight className="w-3 h-3 text-muted-foreground" />
                                                            <span className="text-sm font-mono">{prop.grpc_field}</span>
                                                        </div>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-6 w-6 p-0 text-red-500"
                                                            onClick={() => handleDeletePropertyMapping(prop.id, mapping.id)}
                                                        >
                                                            <X className="w-3 h-3" />
                                                        </Button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </CardContent>
                            )}
                        </Card>
                    ))}
                </div>
            )}

            {/* Property Mapping Dialog */}
            <Dialog open={propertyDialogOpen} onOpenChange={setPropertyDialogOpen}>
                <DialogContent className="sm:max-w-[400px]">
                    <DialogHeader>
                        <DialogTitle>添加属性映射</DialogTitle>
                        <DialogDescription>
                            将 Ontology 属性映射到 gRPC 字段
                        </DialogDescription>
                    </DialogHeader>

                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label>Ontology 属性</Label>
                            {getSelectedMappingClass()?.data_properties?.length ? (
                                <Select
                                    value={propertyForm.ontology_property}
                                    onValueChange={(v: string) => setPropertyForm({ ...propertyForm, ontology_property: v })}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="选择属性" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {getSelectedMappingClass()?.data_properties.map((prop: string) => (
                                            <SelectItem key={prop} value={prop.split(':')[0]}>
                                                {prop}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            ) : (
                                <Input
                                    placeholder="输入属性名称"
                                    value={propertyForm.ontology_property}
                                    onChange={(e) => setPropertyForm({ ...propertyForm, ontology_property: e.target.value })}
                                />
                            )}
                        </div>

                        <div className="grid gap-2">
                            <Label>gRPC 字段</Label>
                            <Input
                                placeholder="输入字段名称"
                                value={propertyForm.grpc_field}
                                onChange={(e) => setPropertyForm({ ...propertyForm, grpc_field: e.target.value })}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setPropertyDialogOpen(false)}>
                            取消
                        </Button>
                        <Button onClick={handleCreatePropertyMapping} disabled={creatingProperty}>
                            {creatingProperty ? '创建中...' : '创建'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}
