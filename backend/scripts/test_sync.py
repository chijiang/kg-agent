# backend/scripts/test_sync.py
import asyncio
import sys
import os

# 将 backend 目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from app.core.database import async_session
from app.services.sync_service import SyncService
from app.models.graph import GraphEntity, GraphRelationship


async def test_sync(product_id: int):
    async with async_session() as db:
        service = SyncService(db)
        print(f"Starting sync for product {product_id}...")
        result = await service.sync_data_product(product_id)
        print(f"Sync Result: {result}")

        # 检查图数据库 - 节点
        entity_res = await db.execute(
            select(func.count(GraphEntity.id)).where(
                GraphEntity.entity_type == "PurchaseOrder"
            )
        )
        count = entity_res.scalar()
        print(f"Total PurchaseOrder entities in KG: {count}")

        # 检查图数据库 - 关系
        rel_res = await db.execute(
            select(func.count(GraphRelationship.id)).where(
                GraphRelationship.relationship_type == "orderedFrom"
            )
        )
        rel_count = rel_res.scalar()
        print(f"Total 'orderedFrom' relationships in KG: {rel_count}")

        # 打印关系样本
        sample_rel_res = await db.execute(
            select(GraphRelationship)
            .where(GraphRelationship.relationship_type == "orderedFrom")
            .limit(5)
        )
        sample_rels = sample_rel_res.scalars().all()
        for r in sample_rels:
            # 这里的 r.source_entity 和 target_entity 可能没加载，我们可以手动查
            print(f"Rel: SourceID={r.source_id} -> TargetID={r.target_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_sync.py <product_id>")
        sys.exit(1)

    pid = int(sys.argv[1])
    asyncio.run(test_sync(pid))
