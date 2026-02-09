import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.sync_service import SyncService
from app.models.data_product import DataProduct, EntityMapping, PropertyMapping
from app.models.graph import GraphEntity


async def verify_sync_merge():
    print("Verifying property merge logic in SyncService...")

    # Mock DB Session
    mock_db = AsyncMock()

    # --- Mock Data Setup ---

    # 1. Mock DataProduct result
    mock_product = MagicMock(spec=DataProduct)
    mock_product.id = 1
    mock_product.grpc_host = "localhost"
    mock_product.grpc_port = 50051
    mock_product.service_name = "TestService"

    # 2. Mock EntityMappings result
    mock_mapping = MagicMock(spec=EntityMapping)
    mock_mapping.id = 1
    mock_mapping.sync_enabled = True
    mock_mapping.sync_direction.value = "pull"
    mock_mapping.list_method = "ListItems"
    mock_mapping.id_field_mapping = "id"
    mock_mapping.name_field_mapping = "name"
    mock_mapping.ontology_class_name = "TestEntity"
    mock_mapping.property_mappings = []
    mock_mapping.target_relationship_mappings = []

    # 3. Mock Existing Entity in DB
    # Expected behavior: 'manual_field' should be preserved
    existing_entity = MagicMock(spec=GraphEntity)
    existing_entity.properties = {
        "id": 1,
        "name": "Old Name",
        "manual_field": "keep_me",
    }
    existing_entity.entity_type = "TestEntity"
    existing_entity.name = "TestEntity_1"

    # --- Verify Logic Flow ---

    # We need to mock the sequence of db.execute calls
    # Call 1: select(DataProduct)
    # Call 2: select(EntityMapping)
    # Call 3: select(GraphEntity) (UPSERT check)

    # Helper to mock scalar_one_or_none and scalars().all()
    mock_result_product = MagicMock()
    mock_result_product.scalar_one_or_none.return_value = mock_product

    mock_result_mappings = MagicMock()
    mock_result_mappings.scalars.return_value.all.return_value = [mock_mapping]

    mock_result_entity = MagicMock()
    mock_result_entity.scalar_one_or_none.return_value = existing_entity

    # Configure side_effect for db.execute to return appropriate results in order
    # Note: SyncService makes calls in this order:
    # 1. Product (commit=False)
    # 2. Add SyncLog (commit=True)
    # 3. Mappings
    # 4. Entity lookup (inside loop)
    # 5. Relationship lookups (we can skip if we limit scope)

    # SyncService.sync_data_product logic is complex to mock fully sequentially due to loops
    # but we can try setting return value side effects based on the query structure if we inspect args
    # simpler: just use a side_effect list and hope the order matches

    mock_db.execute.side_effect = [
        mock_result_product,  # 1. fetch product
        # 2. sync_log insert is db.add, then commit, then refresh.
        # Wait, db.execute is used for SELECTs.
        mock_result_mappings,  # 3. fetch mappings
        mock_result_entity,  # 4. fetch entity (for the item we process)
        # ... subsequent calls would fail or return mocks, mostly we care about step 4
        AsyncMock(),  # Just in case
        AsyncMock(),
    ]

    # Mock gRPC Client
    # We need to patch DynamicGrpcClient to avoid network calls
    with patch("app.services.sync_service.DynamicGrpcClient") as MockClientCls:
        mock_client = AsyncMock()
        MockClientCls.return_value.__aenter__.return_value = mock_client

        # return one item from gRPC
        mock_client.call_method.return_value = {
            "items": [{"id": 1, "name": "New Name Used in Sync"}],
            "pagination": {"total_pages": 1},
        }

        service = SyncService(mock_db)

        try:
            await service.sync_data_product(1)
        except Exception as e:
            # It might fail on later steps (relationships etc) but we want to check if entity.properties was updated before that
            print(f"Service finished with: {e} (expected if mocks run out)")
            pass

    # --- Assertions ---
    print("\nChecking results...")
    final_props = existing_entity.properties
    print(f"Final Properties: {final_props}")

    if "manual_field" in final_props and final_props["manual_field"] == "keep_me":
        print("SUCCESS: 'manual_field' was preserved.")
    else:
        print("FAILURE: 'manual_field' was lost.")

    if final_props.get("name") == "New Name Used in Sync":
        print("SUCCESS: 'name' was updated from source.")
    else:
        print(
            f"FAILURE: 'name' was not updated correctly. Got: {final_props.get('name')}"
        )


if __name__ == "__main__":
    asyncio.run(verify_sync_merge())
