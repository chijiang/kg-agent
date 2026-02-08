# backend/scripts/setup_erp_sync.py
import asyncio
import sys
import os

# 将 backend 目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from app.core.database import async_session as AsyncSessionLocal
from app.models.data_product import (
    DataProduct,
    EntityMapping,
    PropertyMapping,
    RelationshipMapping,
    ConnectionStatus,
    SyncDirection,
)
from app.models.graph import GraphEntity, GraphRelationship


async def setup():
    async with AsyncSessionLocal() as db:
        # 1. 清理旧数据（可选）
        print("Cleaning old test data...")
        # await db.execute(delete(PropertyMapping))
        # await db.execute(delete(EntityMapping))
        # await db.execute(delete(DataProduct))
        # await db.commit()

        # 2. 创建 DataProduct
        result = await db.execute(
            select(DataProduct).where(DataProduct.name == "ERP Emulator")
        )
        product = result.scalar_one_or_none()

        if not product:
            product = DataProduct(
                name="ERP Emulator",
                description="Test ERP System with gRPC Reflection",
                grpc_host="localhost",
                grpc_port=6689,
                service_name="erp.SupplierService",
                connection_status=ConnectionStatus.CONNECTED,
            )
            db.add(product)
            await db.commit()
            await db.refresh(product)
            print(f"Created product: {product.id}")
        else:
            print(f"Product exists: {product.id}")

        # 3. 创建 EntityMapping (Supplier)
        mapping_res = await db.execute(
            select(EntityMapping).where(
                EntityMapping.data_product_id == product.id,
                EntityMapping.ontology_class_name == "Supplier",
            )
        )
        mapping = mapping_res.scalar_one_or_none()

        if not mapping:
            mapping = EntityMapping(
                data_product_id=product.id,
                ontology_class_name="Supplier",
                grpc_message_type="erp.Supplier",
                list_method="ListSuppliers",
                id_field_mapping="id",
                name_field_mapping="name",
            )
            db.add(mapping)
            await db.commit()
            await db.refresh(mapping)
            print(f"Created mapping: {mapping.id}")

        # 4. 创建 PropertyMapping
        props = [
            ("name", "name"),
            ("code", "code"),
            ("email", "email"),
            ("phone", "phone"),
        ]

        for ont_p, grpc_f in props:
            p_check = await db.execute(
                select(PropertyMapping).where(
                    PropertyMapping.entity_mapping_id == mapping.id,
                    PropertyMapping.ontology_property == ont_p,
                )
            )
            if not p_check.scalar_one_or_none():
                pm = PropertyMapping(
                    entity_mapping_id=mapping.id,
                    ontology_property=ont_p,
                    grpc_field=grpc_f,
                )
                db.add(pm)

        await db.commit()
        print(f"Supplier Mapping setup complete.")

        # 5. 创建另一个 DataProduct (Order Service)
        result = await db.execute(
            select(DataProduct).where(DataProduct.name == "ERP Orders")
        )
        order_product = result.scalar_one_or_none()

        if not order_product:
            order_product = DataProduct(
                name="ERP Orders",
                description="Test ERP Orders Service",
                grpc_host="localhost",
                grpc_port=6689,
                service_name="erp.OrderService",
                connection_status=ConnectionStatus.CONNECTED,
            )
            db.add(order_product)
            await db.commit()
            await db.refresh(order_product)

        # 6. 创建 EntityMapping (PurchaseOrder)
        order_mapping_res = await db.execute(
            select(EntityMapping).where(
                EntityMapping.data_product_id == order_product.id,
                EntityMapping.ontology_class_name == "PurchaseOrder",
            )
        )
        order_mapping = order_mapping_res.scalar_one_or_none()
        if not order_mapping:
            order_mapping = EntityMapping(
                data_product_id=order_product.id,
                ontology_class_name="PurchaseOrder",
                grpc_message_type="erp.PurchaseOrder",
                list_method="ListOrders",
                id_field_mapping="id",
                name_field_mapping="order_number",
            )
            db.add(order_mapping)
            await db.commit()
            await db.refresh(order_mapping)

        # 7. 创建 PropertyMapping (Order)
        order_props = [
            ("order_number", "order_number"),
            ("total_amount", "total_amount"),
            ("status", "status"),
            ("supplier_id", "supplier_id"),  # 同步时需带上外键属性以便后期关联
        ]
        for ont_p, grpc_f in order_props:
            p_check = await db.execute(
                select(PropertyMapping).where(
                    PropertyMapping.entity_mapping_id == order_mapping.id,
                    PropertyMapping.ontology_property == ont_p,
                )
            )
            if not p_check.scalar_one_or_none():
                db.add(
                    PropertyMapping(
                        entity_mapping_id=order_mapping.id,
                        ontology_property=ont_p,
                        grpc_field=grpc_f,
                    )
                )

        # 8. 创建 RelationshipMapping (PO -> Supplier)
        # 关联 SupplierMapping (id=1) 和 OrderMapping
        rel_check = await db.execute(
            select(RelationshipMapping).where(
                RelationshipMapping.source_entity_mapping_id == order_mapping.id,
                RelationshipMapping.ontology_relationship == "orderedFrom",
            )
        )
        if not rel_check.scalar_one_or_none():
            db.add(
                RelationshipMapping(
                    source_entity_mapping_id=order_mapping.id,
                    target_entity_mapping_id=mapping.id,  # Supplier Mapping
                    ontology_relationship="orderedFrom",
                    source_fk_field="supplier_id",
                    target_id_field="id",
                )
            )

        await db.commit()
        print("Setup complete.")
        return order_product.id


if __name__ == "__main__":
    product_id = asyncio.run(setup())
    print(f"Ready to sync product ID: {product_id}")
