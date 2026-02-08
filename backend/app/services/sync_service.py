# backend/app/services/sync_service.py
"""
数据同步服务

负责将外部 gRPC 数据源的数据按映射规则同步到 PostgreSQL 知识图谱中。
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload

from app.models.data_product import (
    DataProduct,
    EntityMapping,
    PropertyMapping,
    RelationshipMapping,
    SyncLog,
)
from app.models.graph import GraphEntity, GraphRelationship
from app.services.grpc_client import DynamicGrpcClient

logger = logging.getLogger(__name__)


class SyncService:
    """数据同步服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_data_product(self, product_id: int) -> Dict[str, Any]:
        """同步整个数据产品"""
        # 1. 加载数据产品和所有映射
        result = await self.db.execute(
            select(DataProduct)
            .options(
                selectinload(DataProduct.entity_mappings).selectinload(
                    EntityMapping.property_mappings
                )
            )
            .where(DataProduct.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise ValueError(f"Data product {product_id} not found")

        # 2. 初始化同步日志
        sync_log = SyncLog(
            data_product_id=product.id,
            sync_type="manual",
            direction="pull",
            status="started",
            started_at=datetime.utcnow(),
        )
        self.db.add(sync_log)
        await self.db.commit()
        await self.db.refresh(sync_log)

        total_processed = 0
        total_created = 0
        total_updated = 0
        total_failed = 0
        error_msgs = []

        try:
            async with DynamicGrpcClient(
                product.grpc_host, product.grpc_port
            ) as client:
                # 3. 遍历每个实体映射进行拉取同步
                mappings = product.entity_mappings
                for mapping in mappings:
                    if (
                        not mapping.sync_enabled
                        or mapping.sync_direction.value != "pull"
                    ):
                        continue

                    if not mapping.list_method:
                        logger.warning(
                            f"No list_method defined for mapping {mapping.id}"
                        )
                        continue

                    try:
                        # a. 调用 gRPC 列表方法
                        # 注意：这里假设 list_method 返回一个包含 repeated 字段的消息，或者本身就是一个列表
                        # 根据之前 ERP 模拟器的经验，通常返回 {'items': [...]}
                        response = await client.call_method(
                            product.service_name, mapping.list_method, {}
                        )
                        items = []
                        if isinstance(response, dict):
                            # 尝试获取 items 字段，如果不在 items 里，则尝试获取第一个 list 类型的字段
                            if "items" in response and isinstance(
                                response["items"], list
                            ):
                                items = response["items"]
                            else:
                                for val in response.values():
                                    if isinstance(val, list):
                                        items = val
                                        break
                        elif isinstance(response, list):
                            items = response

                        if not items:
                            logger.info(f"No items retrieved for mapping {mapping.id}")
                            continue

                        # b. 处理每个条目
                        for item in items:
                            total_processed += 1
                            try:
                                # i. 提取元数据
                                # 使用 id_field_mapping 提取 ID
                                raw_id = item.get(mapping.id_field_mapping)
                                if raw_id is None:
                                    # 尝试从属性中获取
                                    raw_id = item.get("id")

                                # 使用 name_field_mapping 提取名称
                                node_name = item.get(mapping.name_field_mapping)
                                if not node_name:
                                    node_name = (
                                        f"{mapping.ontology_class_name}_{raw_id}"
                                    )

                                # ii. 转换属性
                                properties = {}
                                # 默认保留所有字段
                                for k, v in item.items():
                                    properties[k] = v

                                # 应用特定的属性映射
                                for p_map in mapping.property_mappings:
                                    val = item.get(p_map.grpc_field)
                                    if p_map.transform_expression:
                                        try:
                                            # 安全 eval（仅支持基础运算和 string 转换）
                                            safe_dict = {"value": val, "item": item}
                                            val = eval(
                                                p_map.transform_expression,
                                                {"__builtins__": {}},
                                                safe_dict,
                                            )
                                        except Exception as e:
                                            logger.error(
                                                f"Transform error for {p_map.ontology_property}: {e}"
                                            )

                                    properties[p_map.ontology_property] = val

                                # iii. UPSERT GraphEntity
                                # 检查是否存在
                                ent_result = await self.db.execute(
                                    select(GraphEntity).where(
                                        and_(
                                            GraphEntity.name == str(node_name),
                                            GraphEntity.entity_type
                                            == mapping.ontology_class_name,
                                        )
                                    )
                                )
                                entity = ent_result.scalar_one_or_none()

                                if entity:
                                    # 更新
                                    entity.properties = properties
                                    total_updated += 1
                                else:
                                    # 创建
                                    new_entity = GraphEntity(
                                        name=str(node_name),
                                        entity_type=mapping.ontology_class_name,
                                        is_instance=True,
                                        properties=properties,
                                    )
                                    self.db.add(new_entity)
                                    total_created += 1

                            except Exception as e:
                                logger.error(f"Error processing item: {e}")
                                total_failed += 1
                                error_msgs.append(f"Item error: {str(e)}")

                        # 提交每个映射的处理结果，防止大事务
                        await self.db.commit()

                    except Exception as e:
                        logger.error(f"Error syncing mapping {mapping.id}: {e}")
                        error_msgs.append(
                            f"Mapping {mapping.ontology_class_name} error: {str(e)}"
                        )

                # 4. 同步关系
                logger.info("Starting relationship synchronization...")
                rel_stats = await self._sync_relationships(client, product)
                total_created += rel_stats.get("created", 0)

            # 5. 完成日志
            sync_log.status = "completed"
            sync_log.completed_at = datetime.utcnow()
            sync_log.records_processed = total_processed
            sync_log.records_created = total_created
            sync_log.records_updated = total_updated
            sync_log.records_failed = total_failed
            if error_msgs:
                sync_log.error_message = "\n".join(error_msgs[:10])

            await self.db.commit()

        except Exception as e:
            logger.exception("Global sync error")
            sync_log.status = "failed"
            sync_log.completed_at = datetime.utcnow()
            sync_log.error_message = str(e)
            await self.db.commit()
            raise

        return {
            "status": sync_log.status,
            "processed": total_processed,
            "created": total_created,
            "updated": total_updated,
            "failed": total_failed,
        }

    async def _sync_relationships(
        self, client: DynamicGrpcClient, product: DataProduct
    ) -> Dict[str, int]:
        """根据外键同步实体间的关系"""
        stats = {"created": 0, "failed": 0}

        # 加载所有涉及到该数据产品的关系映射
        mappings_ids = [m.id for m in product.entity_mappings]
        if not mappings_ids:
            return stats

        result = await self.db.execute(
            select(RelationshipMapping)
            .options(selectinload(RelationshipMapping.source_entity_mapping))
            .options(selectinload(RelationshipMapping.target_entity_mapping))
            .where(RelationshipMapping.source_entity_mapping_id.in_(mappings_ids))
        )
        rel_mappings = result.scalars().all()

        for rm in rel_mappings:
            if not rm.sync_enabled:
                continue

            # 为了获取外键信息，我们需要再次拉取源数据
            # 优化点：可以在第一遍扫描时缓存外键数据，这里为了逻辑简单先单独拉取
            source_mapping = rm.source_entity_mapping
            target_mapping = rm.target_entity_mapping

            try:
                response = await client.call_method(
                    product.service_name, source_mapping.list_method, {}
                )
                items = []
                if isinstance(response, dict):
                    items = (
                        response.get("items", [])
                        or [v for v in response.values() if isinstance(v, list)][0]
                    )
                elif isinstance(response, list):
                    items = response

                for item in items:
                    fk_val = item.get(rm.source_fk_field)
                    source_raw_id = item.get(source_mapping.id_field_mapping)

                    if fk_val is None or source_raw_id is None:
                        continue

                    # 查找源节点 ID
                    # 由于我们在第一步可能通过 name_field_mapping 修改了 name，
                    # 查找最稳妥的方式是根据 properties 里的原始 ID 字段。

                    source_ent_res = await self.db.execute(
                        select(GraphEntity.id).where(
                            and_(
                                GraphEntity.entity_type
                                == source_mapping.ontology_class_name,
                                GraphEntity.properties[
                                    source_mapping.id_field_mapping
                                ].astext
                                == str(source_raw_id),
                            )
                        )
                    )
                    source_id = source_ent_res.scalar_one_or_none()

                    # 查找目标节点 ID
                    target_ent_res = await self.db.execute(
                        select(GraphEntity.id).where(
                            and_(
                                GraphEntity.entity_type
                                == target_mapping.ontology_class_name,
                                GraphEntity.properties[rm.target_id_field].astext
                                == str(fk_val),
                            )
                        )
                    )
                    target_id = target_ent_res.scalar_one_or_none()

                    if source_id and target_id:
                        # 插入或更新关系
                        rel_check = await self.db.execute(
                            select(GraphRelationship).where(
                                and_(
                                    GraphRelationship.source_id == source_id,
                                    GraphRelationship.target_id == target_id,
                                    GraphRelationship.relationship_type
                                    == rm.ontology_relationship,
                                )
                            )
                        )
                        if not rel_check.scalar_one_or_none():
                            new_rel = GraphRelationship(
                                source_id=source_id,
                                target_id=target_id,
                                relationship_type=rm.ontology_relationship,
                            )
                            self.db.add(new_rel)
                            stats["created"] += 1

                await self.db.commit()
            except Exception as e:
                logger.error(
                    f"Error syncing relationship {rm.ontology_relationship}: {e}"
                )
                stats["failed"] += 1

        return stats

    async def get_sync_logs(
        self, product_id: Optional[int] = None, limit: int = 20
    ) -> List[SyncLog]:
        """获取同步日志"""
        query = select(SyncLog).order_by(SyncLog.started_at.desc()).limit(limit)
        if product_id:
            query = query.where(SyncLog.data_product_id == product_id)

        result = await self.db.execute(query)
        return result.scalars().all()
