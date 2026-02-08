"""ERP Emulator API Routes

All API router modules.
"""

from erp_emulator.api import suppliers, materials, orders, payments, contracts, admin

__all__ = ["suppliers", "materials", "orders", "payments", "contracts", "admin"]
