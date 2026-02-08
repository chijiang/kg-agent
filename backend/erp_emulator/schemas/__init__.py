"""ERP Emulator Schemas

Pydantic schemas for request/response validation.
"""

from erp_emulator.schemas.supplier import (
    SupplierBase,
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    SupplierListResponse,
)
from erp_emulator.schemas.material import (
    MaterialBase,
    MaterialCreate,
    MaterialUpdate,
    MaterialResponse,
    MaterialListResponse,
)
from erp_emulator.schemas.purchase_order import (
    OrderItemBase,
    OrderItemCreate,
    OrderItemResponse,
    PurchaseOrderBase,
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderResponse,
    PurchaseOrderListResponse,
    PurchaseOrderWithItemsResponse,
)
from erp_emulator.schemas.payment import (
    PaymentBase,
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentListResponse,
)
from erp_emulator.schemas.contract import (
    ContractBase,
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractListResponse,
)
from erp_emulator.schemas.common import PaginationParams, PaginatedResponse

__all__ = [
    # Common
    "PaginationParams",
    "PaginatedResponse",
    # Supplier
    "SupplierBase",
    "SupplierCreate",
    "SupplierUpdate",
    "SupplierResponse",
    "SupplierListResponse",
    # Material
    "MaterialBase",
    "MaterialCreate",
    "MaterialUpdate",
    "MaterialResponse",
    "MaterialListResponse",
    # Purchase Order
    "OrderItemBase",
    "OrderItemCreate",
    "OrderItemResponse",
    "PurchaseOrderBase",
    "PurchaseOrderCreate",
    "PurchaseOrderUpdate",
    "PurchaseOrderResponse",
    "PurchaseOrderListResponse",
    "PurchaseOrderWithItemsResponse",
    # Payment
    "PaymentBase",
    "PaymentCreate",
    "PaymentUpdate",
    "PaymentResponse",
    "PaymentListResponse",
    # Contract
    "ContractBase",
    "ContractCreate",
    "ContractUpdate",
    "ContractResponse",
    "ContractListResponse",
]
