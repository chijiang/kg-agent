# 多角色系统实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-step.

**Goal:** 为平台添加完整的多角色功能，包括角色管理、用户审批、页面访问控制、Action权限控制、实体类型可见性控制和密码重置功能。

**Architecture:** 采用分离式权限系统（方案B），每个功能域（页面、Action、实体类型）有独立的权限表，User通过Role关联各域权限。Admin用户通过is_admin字段标识，新用户注册需admin审批后才能登录。

**Tech Stack:** FastAPI, SQLAlchemy (async), PostgreSQL, Next.js 16, React, TypeScript, Zustand

---

## Phase 1: 数据库迁移

### Task 1.1: 创建数据库迁移文件

**Files:**
- Create: `backend/alembic/versions/xxxx_add_multi_role_support.py`

**Step 1: 生成新的迁移文件**

```bash
cd backend
alembic revision -m "add multi-role support"
```

**Step 2: 编辑迁移文件**

编辑生成的迁移文件，添加以下内容：

```python
# backend/alembic/versions/xxxx_add_multi_role_support.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'xxxx'
down_revision = 'yyyy'  # 替换为实际的上一版本
branch_labels = None
depends_on = None


def upgrade():
    # 1. 添加User表新字段
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('approval_status', sa.String(), nullable=False, server_default='pending'))
    op.add_column('users', sa.Column('approval_note', sa.String(), nullable=True))
    op.add_column('users', sa.Column('approved_by', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('is_password_changed', sa.Boolean(), nullable=False, server_default='false'))

    # 2. 创建roles表
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # 3. 创建user_roles关联表
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('assigned_by', sa.Integer(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'role_id')
    )

    # 4. 创建role_page_permissions表
    op.create_table(
        'role_page_permissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('page_id', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('role_id', 'page_id')
    )

    # 5. 创建role_action_permissions表
    op.create_table(
        'role_action_permissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('action_name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('role_id', 'entity_type', 'action_name')
    )

    # 6. 创建role_entity_permissions表
    op.create_table(
        'role_entity_permissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('entity_class_name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('role_id', 'entity_class_name')
    )

    # 7. 创建索引
    op.create_index('ix_users_approval_status', 'users', ['approval_status'])
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'])

    # 8. 插入初始数据
    op.execute("""
        INSERT INTO roles (name, description, is_system) VALUES
        ('admin', '系统管理员', true),
        ('viewer', '查看者', true),
        ('editor', '编辑者', true)
    """)

    # 为admin角色添加所有页面权限
    op.execute("""
        INSERT INTO role_page_permissions (role_id, page_id)
        SELECT id, unnest(ARRAY['chat', 'rules', 'actions', 'data-products', 'ontology', 'admin'])
        FROM roles WHERE name = 'admin'
    """)


def downgrade():
    # 删除表（按依赖顺序逆序）
    op.drop_index('ix_user_roles_role_id', table_name='user_roles')
    op.drop_index('ix_user_roles_user_id', table_name='user_roles')
    op.drop_index('ix_users_approval_status', table_name='users')

    op.drop_table('role_entity_permissions')
    op.drop_table('role_action_permissions')
    op.drop_table('role_page_permissions')
    op.drop_table('user_roles')
    op.drop_table('roles')

    # 删除User表字段
    op.drop_column('users', 'is_password_changed')
    op.drop_column('users', 'approved_at')
    op.drop_column('users', 'approved_by')
    op.drop_column('users', 'approval_note')
    op.drop_column('users', 'approval_status')
    op.drop_column('users', 'is_admin')
```

**Step 3: 运行迁移**

```bash
cd backend
alembic upgrade head
```

**Step 4: 验证迁移**

```bash
psql -h localhost -U your_user -d your_database -c "\dt"  # 查看新表
psql -h localhost -U your_user -d your_database -c "\d users"  # 查看users表结构
```

**Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add database migration for multi-role support"
```

---

## Phase 2: 后端模型和Schema

### Task 2.1: 更新User模型

**Files:**
- Modify: `backend/app/models/user.py`

**Step 1: 阅读现有User模型**

```bash
cat backend/app/models/user.py
```

**Step 2: 修改User模型**

```python
# backend/app/models/user.py
from datetime import datetime
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 新增字段
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    approval_note: Mapped[str | None] = mapped_column(String(500))
    approved_by: Mapped[int | None] = mapped_column(DateTime)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_password_changed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, **kwargs):
        # 设置默认值
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        if 'is_admin' not in kwargs:
            kwargs['is_admin'] = False
        if 'approval_status' not in kwargs:
            kwargs['approval_status'] = 'pending'
        if 'is_password_changed' not in kwargs:
            kwargs['is_password_changed'] = False
        super().__init__(**kwargs)
```

**Step 3: Commit**

```bash
git add backend/app/models/user.py
git commit -m "feat: update User model with multi-role fields"
```

### Task 2.2: 创建Role相关模型

**Files:**
- Create: `backend/app/models/role.py`

**Step 1: 创建Role模型文件**

```python
# backend/app/models/role.py
from datetime import datetime
from sqlalchemy import Boolean, String, ForeignKey, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint('user_id', 'role_id', name='uq_user_role'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RolePagePermission(Base):
    __tablename__ = "role_page_permissions"
    __table_args__ = (UniqueConstraint('role_id', 'page_id', name='uq_role_page'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    page_id: Mapped[str] = mapped_column(String(50), nullable=False)


class RoleActionPermission(Base):
    __tablename__ = "role_action_permissions"
    __table_args__ = (UniqueConstraint('role_id', 'entity_type', 'action_name', name='uq_role_action'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action_name: Mapped[str] = mapped_column(String(100), nullable=False)


class RoleEntityPermission(Base):
    __tablename__ = "role_entity_permissions"
    __table_args__ = (UniqueConstraint('role_id', 'entity_class_name', name='uq_role_entity'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    entity_class_name: Mapped[str] = mapped_column(String(100), nullable=False)
```

**Step 2: 更新models/__init__.py**

```python
# backend/app/models/__init__.py
from app.models.user import User
from app.models.role import Role, UserRole, RolePagePermission, RoleActionPermission, RoleEntityPermission
from app.models.conversation import Conversation, Message
from app.models.graph import GraphEntity, GraphRelationship
from app.models.rule import Rule, ExecutionLog
from app.models.data_product import DataProduct, EntityMapping, PropertyMapping, RelationshipMapping, SyncLog, GrpcMethodCache
from app.models.llm_config import LLMConfig

__all__ = [
    'User',
    'Role',
    'UserRole',
    'RolePagePermission',
    'RoleActionPermission',
    'RoleEntityPermission',
    'Conversation',
    'Message',
    'GraphEntity',
    'GraphRelationship',
    'Rule',
    'ExecutionLog',
    'DataProduct',
    'EntityMapping',
    'PropertyMapping',
    'RelationshipMapping',
    'SyncLog',
    'GrpcMethodCache',
    'LLMConfig',
]
```

**Step 3: Commit**

```bash
git add backend/app/models/role.py backend/app/models/__init__.py
git commit -m "feat: add Role, UserRole, and permission models"
```

### Task 2.3: 创建Schema定义

**Files:**
- Create: `backend/app/schemas/role.py`

**Step 1: 创建Schema文件**

```python
# backend/app/schemas/role.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# Approval Status 枚举
class ApprovalStatus(str):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ==================== Role Schemas ====================

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(RoleBase):
    id: int
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== UserRole Schemas ====================

class AssignRoleRequest(BaseModel):
    role_id: int


# ==================== Permission Schemas ====================

class PagePermissionCreate(BaseModel):
    page_id: str


class ActionPermissionCreate(BaseModel):
    entity_type: str
    action_name: str


class EntityPermissionCreate(BaseModel):
    entity_class_name: str


# ==================== Role Detail with Permissions ====================

class RoleDetailResponse(RoleResponse):
    page_permissions: List[str] = []
    action_permissions: List[dict] = []  # [{"entity_type": str, "action_name": str}]
    entity_permissions: List[str] = []


# ==================== User Schemas (扩展) ====================

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_admin: bool
    approval_status: str
    approval_note: Optional[str] = None
    is_password_changed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int


# ==================== User Approval ====================

class ApproveUserRequest(BaseModel):
    note: Optional[str] = None


class RejectUserRequest(BaseModel):
    reason: str


# ==================== Password Reset ====================

class ResetPasswordResponse(BaseModel):
    message: str
    default_password: str  # 返回默认密码供admin查看


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ==================== Permission Cache ====================

class PermissionCacheResponse(BaseModel):
    accessible_pages: List[str]
    accessible_actions: dict  # {entity_type: [action_names]}
    accessible_entities: List[str]
    is_admin: bool


# ==================== Register Response (修改) ====================

class RegisterPendingResponse(BaseModel):
    message: str
    user_id: int
```

**Step 2: 更新schemas/__init__.py**

```python
# backend/app/schemas/__init__.py
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleDetailResponse,
    AssignRoleRequest,
    PagePermissionCreate,
    ActionPermissionCreate,
    EntityPermissionCreate,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    ApproveUserRequest,
    RejectUserRequest,
    ResetPasswordResponse,
    ChangePasswordRequest,
    PermissionCacheResponse,
    RegisterPendingResponse,
    ApprovalStatus,
)

__all__ = [
    'RoleCreate',
    'RoleUpdate',
    'RoleResponse',
    'RoleDetailResponse',
    'AssignRoleRequest',
    'PagePermissionCreate',
    'ActionPermissionCreate',
    'EntityPermissionCreate',
    'UserCreate',
    'UserUpdate',
    'UserResponse',
    'UserListResponse',
    'ApproveUserRequest',
    'RejectUserRequest',
    'ResetPasswordResponse',
    'ChangePasswordRequest',
    'PermissionCacheResponse',
    'RegisterPendingResponse',
    'ApprovalStatus',
]
```

**Step 3: Commit**

```bash
git add backend/app/schemas/role.py backend/app/schemas/__init__.py
git commit -m "feat: add schemas for role and user management"
```

---

## Phase 3: 权限检查服务

### Task 3.1: 创建权限服务

**Files:**
- Create: `backend/app/services/permission_service.py`

**Step 1: 创建权限服务文件**

```python
# backend/app/services/permission_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.models.role import Role, UserRole, RolePagePermission, RoleActionPermission, RoleEntityPermission
from typing import List, Dict, Optional


# 功能模块枚举
class PageId:
    CHAT = "chat"
    RULES = "rules"
    ACTIONS = "actions"
    DATA_PRODUCTS = "data-products"
    ONTOLOGY = "ontology"
    ADMIN = "admin"

    @classmethod
    def all(cls) -> List[str]:
        return [cls.CHAT, cls.RULES, cls.ACTIONS, cls.DATA_PRODUCTS, cls.ONTOLOGY, cls.ADMIN]


class PermissionService:
    """权限检查和缓存服务"""

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: int) -> List[Role]:
        """获取用户的所有角色"""
        result = await db.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_accessible_pages(db: AsyncSession, user: User) -> List[str]:
        """获取用户可访问的页面列表"""
        # Admin拥有所有权限
        if user.is_admin:
            return PageId.all()

        # 获取用户角色的页面权限
        result = await db.execute(
            select(RolePagePermission.page_id)
            .join(UserRole, UserRole.role_id == RolePagePermission.role_id)
            .where(UserRole.user_id == user.id)
            .distinct()
        )
        return [row[0] for row in result.all()]

    @staticmethod
    async def check_page_access(db: AsyncSession, user: User, page_id: str) -> bool:
        """检查用户是否有页面访问权限"""
        if user.is_admin:
            return True

        result = await db.execute(
            select(RolePagePermission)
            .join(UserRole, UserRole.role_id == RolePagePermission.role_id)
            .where(
                UserRole.user_id == user.id,
                RolePagePermission.page_id == page_id
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_accessible_actions(db: AsyncSession, user: User) -> Dict[str, List[str]]:
        """获取用户可执行的Action，返回 {entity_type: [action_names]}"""
        if user.is_admin:
            # Admin拥有所有action权限
            # 这里需要从action registry获取所有action
            from app.rule_engine.action_registry import action_registry
            result = {}
            for entity_type, actions in action_registry._registry.items():
                result[entity_type] = list(actions.keys())
            return result

        # 获取用户角色的action权限
        result = await db.execute(
            select(RoleActionPermission)
            .join(UserRole, UserRole.role_id == RoleActionPermission.role_id)
            .where(UserRole.user_id == user.id)
            .distinct()
        )
        permissions = result.scalars().all()

        # 按entity_type分组
        actions_dict: Dict[str, List[str]] = {}
        for perm in permissions:
            if perm.entity_type not in actions_dict:
                actions_dict[perm.entity_type] = []
            actions_dict[perm.entity_type].append(perm.action_name)

        return actions_dict

    @staticmethod
    async def check_action_permission(
        db: AsyncSession,
        user: User,
        entity_type: str,
        action_name: str
    ) -> bool:
        """检查用户是否有指定Action的执行权限"""
        if user.is_admin:
            return True

        result = await db.execute(
            select(RoleActionPermission)
            .join(UserRole, UserRole.role_id == RoleActionPermission.role_id)
            .where(
                UserRole.user_id == user.id,
                RoleActionPermission.entity_type == entity_type,
                RoleActionPermission.action_name == action_name
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_accessible_entities(db: AsyncSession, user: User) -> List[str]:
        """获取用户可访问的实体类型列表"""
        if user.is_admin:
            # Admin拥有所有实体类型的访问权限
            # 从GraphEntity表获取所有类名
            from app.models.graph import GraphEntity
            result = await db.execute(
                select(GraphEntity.type).distinct()
            )
            return list({row[0] for row in result.all() if row[0]})

        result = await db.execute(
            select(RoleEntityPermission.entity_class_name)
            .join(UserRole, UserRole.role_id == RoleEntityPermission.role_id)
            .where(UserRole.user_id == user.id)
            .distinct()
        )
        return [row[0] for row in result.all()]

    @staticmethod
    async def check_entity_access(
        db: AsyncSession,
        user: User,
        entity_class_name: str
    ) -> bool:
        """检查用户是否有指定实体类型的访问权限"""
        if user.is_admin:
            return True

        result = await db.execute(
            select(RoleEntityPermission)
            .join(UserRole, UserRole.role_id == RoleEntityPermission.role_id)
            .where(
                UserRole.user_id == user.id,
                RoleEntityPermission.entity_class_name == entity_class_name
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_permission_cache(db: AsyncSession, user: User) -> dict:
        """获取用户权限缓存（登录后调用）"""
        accessible_pages = await PermissionService.get_accessible_pages(db, user)
        accessible_actions = await PermissionService.get_accessible_actions(db, user)
        accessible_entities = await PermissionService.get_accessible_entities(db, user)

        return {
            "accessible_pages": accessible_pages,
            "accessible_actions": accessible_actions,
            "accessible_entities": accessible_entities,
            "is_admin": user.is_admin
        }
```

**Step 2: Commit**

```bash
git add backend/app/services/permission_service.py
git commit -m "feat: add permission service for access control"
```

---

## Phase 4: 用户管理API

### Task 4.1: 修改注册和登录接口

**Files:**
- Modify: `backend/app/api/auth.py`

**Step 1: 修改auth.py**

```python
# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.role import RegisterPendingResponse, TokenResponse, ChangePasswordRequest
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register", response_model=RegisterPendingResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # 检查用户是否存在
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    # 创建用户（状态为pending）
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        email=req.email,
        approval_status="pending",
        is_password_changed=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return RegisterPendingResponse(
        message="Registration pending approval",
        user_id=user.id
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 检查审批状态
    if user.approval_status == "pending":
        raise HTTPException(
            status_code=403,
            detail="Registration pending approval"
        )
    elif user.approval_status == "rejected":
        reason = user.approval_note or "No reason provided"
        raise HTTPException(
            status_code=403,
            detail=f"Registration rejected: {reason}"
        )

    # 检查账户状态
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token)


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改当前用户密码"""
    # 验证旧密码
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect password")

    # 更新密码
    current_user.password_hash = hash_password(req.new_password)
    current_user.is_password_changed = True
    await db.commit()

    return {"message": "Password changed successfully"}
```

**Step 2: Commit**

```bash
git add backend/app/api/auth.py
git commit -m "feat: update register and login with approval flow"
```

### Task 4.2: 创建用户管理API

**Files:**
- Create: `backend/app/api/users.py`

**Step 1: 创建用户管理API文件**

```python
# backend/app/api/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.role import UserRole
from app.schemas.role import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    ApproveUserRequest,
    RejectUserRequest,
    ResetPasswordResponse,
    ChangePasswordRequest,
    PermissionCacheResponse,
)
from app.api.deps import get_current_user
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/users", tags=["users"])


async def require_admin(current_user: User = Depends(get_current_user)):
    """验证用户是否为admin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    approval_status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表（admin only）"""
    query = select(User)

    # 筛选条件
    if approval_status:
        query = query.where(User.approval_status == approval_status)

    if search:
        query = query.where(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建用户（admin only）"""
    # 检查用户名是否存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    # 创建用户（直接approved）
    user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        email=user_data.email,
        approval_status="approved",
        approved_by=current_user.id,
        is_password_changed=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/pending-approvals", response_model=UserListResponse)
async def get_pending_approvals(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取待审批用户列表（admin only）"""
    result = await db.execute(
        select(User).where(User.approval_status == "pending")
    )
    users = result.scalars().all()

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=len(users)
    )


@router.post("/{user_id}/approve")
async def approve_user(
    user_id: int,
    req: ApproveUserRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """审批通过用户注册（admin only）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.approval_status != "pending":
        raise HTTPException(status_code=400, detail="User is not pending approval")

    user.approval_status = "approved"
    user.approved_by = current_user.id
    user.approved_at = func.now()
    user.approval_note = req.note
    await db.commit()

    return {"message": "User approved successfully"}


@router.post("/{user_id}/reject")
async def reject_user(
    user_id: int,
    req: RejectUserRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """拒绝用户注册（admin only）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.approval_status != "pending":
        raise HTTPException(status_code=400, detail="User is not pending approval")

    user.approval_status = "rejected"
    user.approved_by = current_user.id
    user.approved_at = func.now()
    user.approval_note = req.reason
    await db.commit()

    return {"message": "User rejected"}


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_user_password(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """重置用户密码为默认值（admin only）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 默认密码
    default_password = "123456"
    user.password_hash = hash_password(default_password)
    user.is_password_changed = False
    await db.commit()

    return ResetPasswordResponse(
        message="Password reset successfully",
        default_password=default_password
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新用户（admin only）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 更新字段
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除用户（admin only）"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()

    return {"message": "User deleted"}


@router.post("/{user_id}/roles")
async def assign_role(
    user_id: int,
    req: dict,  # {"role_id": int}
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """为用户分配角色（admin only）"""
    # 检查用户是否存在
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    role_id = req.get("role_id")
    if not role_id:
        raise HTTPException(status_code=400, detail="role_id is required")

    # 检查是否已分配
    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role already assigned")

    # 创建关联
    user_role = UserRole(
        user_id=user_id,
        role_id=role_id,
        assigned_by=current_user.id
    )
    db.add(user_role)
    await db.commit()

    return {"message": "Role assigned successfully"}


@router.delete("/{user_id}/roles/{role_id}")
async def remove_role(
    user_id: int,
    role_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """移除用户角色（admin only）"""
    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
    )
    user_role = result.scalar_one_or_none()

    if not user_role:
        raise HTTPException(status_code=404, detail="Role assignment not found")

    await db.delete(user_role)
    await db.commit()

    return {"message": "Role removed successfully"}


@router.get("/me/permissions", response_model=PermissionCacheResponse)
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的权限缓存"""
    cache = await PermissionService.get_permission_cache(db, current_user)
    return PermissionCacheResponse(**cache)
```

**Step 2: 更新main.py注册路由**

```python
# backend/app/main.py - 在路由注册部分添加
from app.api import users

app.include_router(users.router, prefix="/api")
```

**Step 3: Commit**

```bash
git add backend/app/api/users.py backend/app/main.py
git commit -m "feat: add user management API"
```

---

## Phase 5: 角色管理API

### Task 5.1: 创建角色管理API

**Files:**
- Create: `backend/app/api/roles.py`

**Step 1: 创建角色管理API文件**

```python
# backend/app/api/roles.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
from app.core.database import get_db
from app.models.role import Role, UserRole, RolePagePermission, RoleActionPermission, RoleEntityPermission
from app.models.user import User
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleDetailResponse,
    PagePermissionCreate,
    ActionPermissionCreate,
    EntityPermissionCreate,
    AssignRoleRequest,
)
from app.api.deps import get_current_user
from app.api.users import require_admin

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有角色"""
    result = await db.execute(select(Role))
    roles = result.scalars().all()

    return [RoleResponse.model_validate(r) for r in roles]


@router.get("/{role_id}", response_model=RoleDetailResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取角色详情（包含权限）"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # 获取页面权限
    page_result = await db.execute(
        select(RolePagePermission.page_id).where(RolePagePermission.role_id == role_id)
    )
    page_permissions = [row[0] for row in page_result.all()]

    # 获取action权限
    action_result = await db.execute(
        select(RoleActionPermission).where(RoleActionPermission.role_id == role_id)
    )
    action_permissions = [
        {"entity_type": p.entity_type, "action_name": p.action_name}
        for p in action_result.scalars().all()
    ]

    # 获取实体权限
    entity_result = await db.execute(
        select(RoleEntityPermission.entity_class_name).where(RoleEntityPermission.role_id == role_id)
    )
    entity_permissions = [row[0] for row in entity_result.all()]

    return RoleDetailResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        created_at=role.created_at,
        updated_at=role.updated_at,
        page_permissions=page_permissions,
        action_permissions=action_permissions,
        entity_permissions=entity_permissions,
    )


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建角色（admin only）"""
    # 检查名称是否存在
    result = await db.execute(select(Role).where(Role.name == role_data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role name already exists")

    role = Role(
        name=role_data.name,
        description=role_data.description,
        is_system=False
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return RoleResponse.model_validate(role)


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新角色（admin only）"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system role")

    # 更新字段
    if role_data.name is not None:
        # 检查名称是否重复
        existing = await db.execute(
            select(Role).where(
                Role.name == role_data.name,
                Role.id != role_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Role name already exists")
        role.name = role_data.name

    if role_data.description is not None:
        role.description = role_data.description

    await db.commit()
    await db.refresh(role)

    return RoleResponse.model_validate(role)


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除角色（admin only）"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system role")

    # 检查是否有用户使用此角色
    user_count = await db.execute(
        select(func.count()).select_from(
            select(UserRole).where(UserRole.role_id == role_id).subquery()
        )
    )
    if user_count.scalar() > 0:
        raise HTTPException(status_code=400, detail="Cannot delete role with assigned users")

    await db.delete(role)
    await db.commit()

    return {"message": "Role deleted"}


# ==================== 权限管理 ====================

@router.get("/{role_id}/permissions/pages", response_model=List[str])
async def get_page_permissions(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取角色的页面权限"""
    result = await db.execute(
        select(RolePagePermission.page_id).where(RolePagePermission.role_id == role_id)
    )
    return [row[0] for row in result.all()]


@router.post("/{role_id}/permissions/pages")
async def add_page_permission(
    role_id: int,
    perm: PagePermissionCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """添加页面权限（admin only）"""
    # 检查角色是否存在
    result = await db.execute(select(Role).where(Role.id == role_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Role not found")

    # 检查是否已存在
    existing = await db.execute(
        select(RolePagePermission).where(
            RolePagePermission.role_id == role_id,
            RolePagePermission.page_id == perm.page_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Permission already exists")

    permission = RolePagePermission(role_id=role_id, page_id=perm.page_id)
    db.add(permission)
    await db.commit()

    return {"message": "Page permission added"}


@router.delete("/{role_id}/permissions/pages/{page_id}")
async def remove_page_permission(
    role_id: int,
    page_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除页面权限（admin only）"""
    result = await db.execute(
        select(RolePagePermission).where(
            RolePagePermission.role_id == role_id,
            RolePagePermission.page_id == page_id
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    await db.delete(permission)
    await db.commit()

    return {"message": "Page permission removed"}


@router.get("/{role_id}/permissions/actions")
async def get_action_permissions(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取角色的Action权限"""
    result = await db.execute(
        select(RoleActionPermission).where(RoleActionPermission.role_id == role_id)
    )
    permissions = result.scalars().all()

    return [
        {"entity_type": p.entity_type, "action_name": p.action_name}
        for p in permissions
    ]


@router.post("/{role_id}/permissions/actions")
async def add_action_permission(
    role_id: int,
    perm: ActionPermissionCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """添加Action权限（admin only）"""
    # 检查角色是否存在
    result = await db.execute(select(Role).where(Role.id == role_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Role not found")

    # 检查是否已存在
    existing = await db.execute(
        select(RoleActionPermission).where(
            RoleActionPermission.role_id == role_id,
            RoleActionPermission.entity_type == perm.entity_type,
            RoleActionPermission.action_name == perm.action_name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Permission already exists")

    permission = RoleActionPermission(
        role_id=role_id,
        entity_type=perm.entity_type,
        action_name=perm.action_name
    )
    db.add(permission)
    await db.commit()

    return {"message": "Action permission added"}


@router.delete("/{role_id}/permissions/actions/{entity_type}/{action_name}")
async def remove_action_permission(
    role_id: int,
    entity_type: str,
    action_name: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除Action权限（admin only）"""
    result = await db.execute(
        select(RoleActionPermission).where(
            RoleActionPermission.role_id == role_id,
            RoleActionPermission.entity_type == entity_type,
            RoleActionPermission.action_name == action_name
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    await db.delete(permission)
    await db.commit()

    return {"message": "Action permission removed"}


@router.get("/{role_id}/permissions/entities", response_model=List[str])
async def get_entity_permissions(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取角色的实体类型权限"""
    result = await db.execute(
        select(RoleEntityPermission.entity_class_name).where(RoleEntityPermission.role_id == role_id)
    )
    return [row[0] for row in result.all()]


@router.post("/{role_id}/permissions/entities")
async def add_entity_permission(
    role_id: int,
    perm: EntityPermissionCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """添加实体类型权限（admin only）"""
    # 检查角色是否存在
    result = await db.execute(select(Role).where(Role.id == role_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Role not found")

    # 检查是否已存在
    existing = await db.execute(
        select(RoleEntityPermission).where(
            RoleEntityPermission.role_id == role_id,
            RoleEntityPermission.entity_class_name == perm.entity_class_name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Permission already exists")

    permission = RoleEntityPermission(
        role_id=role_id,
        entity_class_name=perm.entity_class_name
    )
    db.add(permission)
    await db.commit()

    return {"message": "Entity permission added"}


@router.delete("/{role_id}/permissions/entities/{entity_class_name}")
async def remove_entity_permission(
    role_id: int,
    entity_class_name: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除实体类型权限（admin only）"""
    result = await db.execute(
        select(RoleEntityPermission).where(
            RoleEntityPermission.role_id == role_id,
            RoleEntityPermission.entity_class_name == entity_class_name
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    await db.delete(permission)
    await db.commit()

    return {"message": "Entity permission removed"}
```

**Step 2: 更新main.py注册路由**

```python
# backend/app/main.py - 添加角色路由
from app.api import roles

app.include_router(roles.router)
```

**Step 3: Commit**

```bash
git add backend/app/api/roles.py backend/app/main.py
git commit -m "feat: add role management API"
```

---

## Phase 6: 现有API集成权限检查

### Task 6.1: 修改graph API集成实体类型权限

**Files:**
- Modify: `backend/app/api/graph.py`

**Step 1: 阅读现有graph.py文件**

```bash
head -100 backend/app/api/graph.py
```

**Step 2: 修改getRandomInstances接口添加权限过滤**

在`getRandomInstances`函数中，添加权限过滤：

```python
# backend/app/api/graph.py - 修改getRandomInstances函数

from app.services.permission_service import PermissionService

@router.get("/instances/random")
async def get_random_instances(
    limit: int = 200,
    current_user: User = Depends(get_current_user),  # 添加认证
    db: AsyncSession = Depends(get_db),
):
    # 获取用户可访问的实体类型
    accessible_entities = await PermissionService.get_accessible_entities(db, current_user)

    # 原有查询添加类型过滤
    query = select(GraphEntity).where(
        GraphEntity.type.in_(accessible_entities) if accessible_entities and not current_user.is_admin else True
    ).order_by(func.random()).limit(limit)

    # ... 其余逻辑
```

**Step 3: 修改ontology classes接口添加权限过滤**

```python
@router.get("/ontology/classes")
async def get_ontology_classes(
    current_user: User = Depends(get_current_user),  # 添加认证
    db: AsyncSession = Depends(get_db),
):
    # 获取用户可访问的实体类型
    accessible_entities = await PermissionService.get_accessible_entities(db, current_user)

    # 过滤类定义
    if not current_user.is_admin and accessible_entities:
        # 只返回用户有权限的类
        # ... 原有逻辑添加过滤
```

**Step 4: Commit**

```bash
git add backend/app/api/graph.py
git commit -m "feat: integrate entity type permissions into graph API"
```

### Task 6.2: 修改actions API添加权限检查

**Files:**
- Modify: `backend/app/api/actions.py`

**Step 1: 修改actions API添加权限检查**

```python
# backend/app/api/actions.py - 在executeAction函数中添加

from app.services.permission_service import PermissionService

@router.post("/{entity_type}/{action_name}")
async def execute_action(
    entity_type: str,
    action_name: str,
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 检查权限
    has_permission = await PermissionService.check_action_permission(
        db, current_user, entity_type, action_name
    )
    if not has_permission:
        raise HTTPException(status_code=403, detail="No permission to execute this action")

    # ... 原有逻辑
```

**Step 2: 修改listByEntityType接口过滤无权限的actions**

```python
@router.get("/{entity_type}")
async def list_actions_by_entity_type(
    entity_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 获取用户可执行的actions
    user_actions = await PermissionService.get_accessible_actions(db, current_user)

    if current_user.is_admin:
        # Admin返回所有actions
        pass
    else:
        # 过滤只返回用户有权限的actions
        allowed_actions = user_actions.get(entity_type, [])
        # ... 过滤逻辑

    # ... 返回结果
```

**Step 3: Commit**

```bash
git add backend/app/api/actions.py
git commit -m "feat: integrate action permissions check"
```

---

## Phase 7: 前端类型定义和API客户端

### Task 7.1: 更新前端类型定义

**Files:**
- Modify: `frontend/src/lib/api.ts`

**Step 1: 添加新的类型定义**

```typescript
// frontend/src/lib/api.ts - 在文件末尾添加

// ============================================================================
// Multi-Role System Types
// ============================================================================

export type ApprovalStatus = 'pending' | 'approved' | 'rejected'
export type PageId = 'chat' | 'rules' | 'actions' | 'data-products' | 'ontology' | 'admin'

export interface UserRole {
  id: number
  user_id: number
  role_id: number
  assigned_by: number | null
  assigned_at: string
}

export interface Role {
  id: number
  name: string
  description: string | null
  is_system: boolean
  created_at: string
  updated_at: string
}

export interface RoleDetail extends Role {
  page_permissions: string[]
  action_permissions: Array<{ entity_type: string; action_name: string }>
  entity_permissions: string[]
}

export interface User {
  id: number
  username: string
  email: string | null
  is_admin: boolean
  approval_status: ApprovalStatus
  approval_note: string | null
  is_password_changed: boolean
  created_at: string
}

export interface UserListResponse {
  items: User[]
  total: number
}

export interface PermissionCache {
  accessible_pages: string[]
  accessible_actions: Record<string, string[]>
  accessible_entities: string[]
  is_admin: boolean
}

export interface ResetPasswordResponse {
  message: string
  default_password: string
}

// ============================================================================
// Multi-Role System API
// ============================================================================

export const usersApi = {
  // 获取用户列表
  list: (params?: { skip?: number; limit?: number; approval_status?: string; search?: string }) =>
    api.get<UserListResponse>('/api/users', { params }),

  // 创建用户
  create: (data: { username: string; password: string; email?: string }) =>
    api.post<User>('/api/users', data),

  // 更新用户
  update: (userId: number, data: { email?: string; is_active?: boolean }) =>
    api.put<User>(`/api/users/${userId}`, data),

  // 删除用户
  delete: (userId: number) =>
    api.delete(`/api/users/${userId}`),

  // 获取待审批用户列表
  getPendingApprovals: () =>
    api.get<UserListResponse>('/api/users/pending-approvals'),

  // 审批通过
  approve: (userId: number, note?: string) =>
    api.post(`/api/users/${userId}/approve`, { note }),

  // 审批拒绝
  reject: (userId: number, reason: string) =>
    api.post(`/api/users/${userId}/reject`, { reason }),

  // 重置密码
  resetPassword: (userId: number) =>
    api.post<ResetPasswordResponse>(`/api/users/${userId}/reset-password`),

  // 分配角色
  assignRole: (userId: number, roleId: number) =>
    api.post(`/api/users/${userId}/roles`, { role_id: roleId }),

  // 移除角色
  removeRole: (userId: number, roleId: number) =>
    api.delete(`/api/users/${userId}/roles/${roleId}`),

  // 获取当前用户权限
  getMyPermissions: () =>
    api.get<PermissionCache>('/api/users/me/permissions'),

  // 修改密码
  changePassword: (oldPassword: string, newPassword: string) =>
    api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
}

export const rolesApi = {
  // 获取所有角色
  list: () =>
    api.get<Role[]>('/api/roles'),

  // 获取角色详情
  get: (roleId: number) =>
    api.get<RoleDetail>(`/api/roles/${roleId}`),

  // 创建角色
  create: (data: { name: string; description?: string }) =>
    api.post<Role>('/api/roles', data),

  // 更新角色
  update: (roleId: number, data: { name?: string; description?: string }) =>
    api.put<Role>(`/api/roles/${roleId}`, data),

  // 删除角色
  delete: (roleId: number) =>
    api.delete(`/api/roles/${roleId}`),

  // 页面权限
  getPagePermissions: (roleId: number) =>
    api.get<string[]>(`/api/roles/${roleId}/permissions/pages`),

  addPagePermission: (roleId: number, pageId: string) =>
    api.post(`/api/roles/${roleId}/permissions/pages`, { page_id: pageId }),

  removePagePermission: (roleId: number, pageId: string) =>
    api.delete(`/api/roles/${roleId}/permissions/pages/${pageId}`),

  // Action权限
  getActionPermissions: (roleId: number) =>
    api.get<Array<{ entity_type: string; action_name: string }>>(`/api/roles/${roleId}/permissions/actions`),

  addActionPermission: (roleId: number, entityType: string, actionName: string) =>
    api.post(`/api/roles/${roleId}/permissions/actions`, { entity_type: entityType, action_name: actionName }),

  removeActionPermission: (roleId: number, entityType: string, actionName: string) =>
    api.delete(`/api/roles/${roleId}/permissions/actions/${entityType}/${actionName}`),

  // 实体类型权限
  getEntityPermissions: (roleId: number) =>
    api.get<string[]>(`/api/roles/${roleId}/permissions/entities`),

  addEntityPermission: (roleId: number, entityClassName: string) =>
    api.post(`/api/roles/${roleId}/permissions/entities`, { entity_class_name: entityClassName }),

  removeEntityPermission: (roleId: number, entityClassName: string) =>
    api.delete(`/api/roles/${roleId}/permissions/entities/${entityClassName}`),
}
```

**Step 2: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add multi-role types and API client"
```

### Task 7.2: 更新auth store

**Files:**
- Modify: `frontend/src/lib/auth.ts`

**Step 1: 扩展auth store**

```typescript
// frontend/src/lib/auth.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  username: string
  is_admin?: boolean
  approval_status?: 'pending' | 'approved' | 'rejected'
  is_password_changed?: boolean
}

interface AuthState {
  user: User | null
  token: string | null
  permissions: {
    accessible_pages: string[]
    accessible_actions: Record<string, string[]>
    accessible_entities: string[]
    is_admin: boolean
  } | null
  setAuth: (user: User, token: string) => void
  setPermissions: (permissions: AuthState['permissions']) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      permissions: null,
      setAuth: (user, token) => set({ user, token }),
      setPermissions: (permissions) => set({ permissions }),
      logout: () => set({ user: null, token: null, permissions: null }),
    }),
    { name: 'auth-storage' }
  )
)
```

**Step 2: Commit**

```bash
git add frontend/src/lib/auth.ts
git commit -m "feat: extend auth store with permissions"
```

---

## Phase 8: 前端权限组件

### Task 8.1: 创建权限Hook

**Files:**
- Create: `frontend/src/hooks/usePermissions.ts`

**Step 1: 创建usePermissions hook**

```typescript
// frontend/src/hooks/usePermissions.ts
import { useEffect, useState } from 'react'
import { useAuthStore } from '@/lib/auth'
import { usersApi, PermissionCache } from '@/lib/api'

export function usePermissions() {
  const { user, token, setPermissions } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadPermissions() {
      if (!token || !user) {
        setLoading(false)
        return
      }

      try {
        const permissions = await usersApi.getMyPermissions()
        setPermissions(permissions)
      } catch (error) {
        console.error('Failed to load permissions:', error)
      } finally {
        setLoading(false)
      }
    }

    loadPermissions()
  }, [token, user, setPermissions])

  const permissions = useAuthStore((state) => state.permissions)

  const hasPageAccess = (pageId: string): boolean => {
    if (!permissions) return false
    if (permissions.is_admin) return true
    return permissions.accessible_pages.includes(pageId)
  }

  const hasActionPermission = (entityType: string, actionName: string): boolean => {
    if (!permissions) return false
    if (permissions.is_admin) return true
    const actions = permissions.accessible_actions[entityType]
    return actions?.includes(actionName) ?? false
  }

  const hasEntityAccess = (entityClassName: string): boolean => {
    if (!permissions) return false
    if (permissions.is_admin) return true
    return permissions.accessible_entities.includes(entityClassName)
  }

  return {
    permissions,
    loading,
    hasPageAccess,
    hasActionPermission,
    hasEntityAccess,
  }
}
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/usePermissions.ts
git commit -m "feat: add usePermissions hook"
```

### Task 8.2: 创建页面权限保护组件

**Files:**
- Create: `frontend/src/components/auth/ProtectedPage.tsx`
- Create: `frontend/src/components/auth/AccessDenied.tsx`

**Step 1: 创建AccessDenied组件**

```typescript
// frontend/src/components/auth/AccessDenied.tsx
export function AccessDeniedPage() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Access Denied</h1>
        <p className="text-gray-600 mb-8">You don't have permission to access this page.</p>
        <a href="/" className="text-blue-600 hover:text-blue-800">
          Return to Home
        </a>
      </div>
    </div>
  )
}
```

**Step 2: 创建ProtectedPage组件**

```typescript
// frontend/src/components/auth/ProtectedPage.tsx
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { usePermissions } from '@/hooks/usePermissions'
import { AccessDeniedPage } from './AccessDenied'

interface ProtectedPageProps {
  pageId: string
  children: React.ReactNode
}

export function ProtectedPage({ pageId, children }: ProtectedPageProps) {
  const { hasPageAccess, loading } = usePermissions()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !hasPageAccess(pageId)) {
      router.push('/')
    }
  }, [hasPageAccess, loading, pageId, router])

  if (loading) {
    return <div>Loading...</div>
  }

  if (!hasPageAccess(pageId)) {
    return <AccessDeniedPage />
  }

  return <>{children}</>
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/auth/
git commit -m "feat: add ProtectedPage and AccessDenied components"
```

---

## Phase 9: 前端管理页面

### Task 9.1: 创建用户管理页面

**Files:**
- Create: `frontend/src/app/admin/users/page.tsx`
- Create: `frontend/src/app/admin/users/components/UserList.tsx`
- Create: `frontend/src/app/admin/users/components/UserCreateDialog.tsx`

**Step 1: 创建用户管理页面**

```typescript
// frontend/src/app/admin/users/page.tsx
'use client'

import { ProtectedPage } from '@/components/auth/ProtectedPage'
import { UserList } from './components/UserList'

export default function UsersPage() {
  return (
    <ProtectedPage pageId="admin">
      <div className="container mx-auto py-6">
        <h1 className="text-3xl font-bold mb-6">User Management</h1>
        <UserList />
      </div>
    </ProtectedPage>
  )
}
```

**Step 2: 创建UserList组件**

```typescript
// frontend/src/app/admin/users/components/UserList.tsx
'use client'

import { useEffect, useState } from 'react'
import { usersApi, User } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { UserCreateDialog } from './UserCreateDialog'

export function UserList() {
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  const loadUsers = async () => {
    setLoading(true)
    try {
      const response = await usersApi.list()
      setUsers(response.items)
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl">Users ({total})</h2>
        <Button onClick={() => setShowCreate(true)}>Create User</Button>
      </div>

      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th className="text-left p-2">Username</th>
            <th className="text-left p-2">Email</th>
            <th className="text-left p-2">Status</th>
            <th className="text-left p-2">Admin</th>
            <th className="text-left p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className="border-b">
              <td className="p-2">{user.username}</td>
              <td className="p-2">{user.email || '-'}</td>
              <td className="p-2">
                <span className={`px-2 py-1 rounded text-sm ${
                  user.approval_status === 'approved' ? 'bg-green-100 text-green-800' :
                  user.approval_status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {user.approval_status}
                </span>
              </td>
              <td className="p-2">{user.is_admin ? 'Yes' : 'No'}</td>
              <td className="p-2">
                <Button variant="ghost" size="sm">Edit</Button>
                <Button variant="ghost" size="sm">Reset Password</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showCreate && (
        <UserCreateDialog
          onClose={() => setShowCreate(false)}
          onCreated={loadUsers}
        />
      )}
    </div>
  )
}
```

**Step 3: 创建UserCreateDialog组件**

```typescript
// frontend/src/app/admin/users/components/UserCreateDialog.tsx
'use client'

import { useState } from 'react'
import { usersApi } from '@/lib/api'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface UserCreateDialogProps {
  onClose: () => void
  onCreated: () => void
}

export function UserCreateDialog({ onClose, onCreated }: UserCreateDialogProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await usersApi.create({ username, password, email: email || undefined })
      onCreated()
      onClose()
    } catch (error) {
      console.error('Failed to create user:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create User</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={loading}>Create</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
```

**Step 4: Commit**

```bash
git add frontend/src/app/admin/users/
git commit -m "feat: add user management page"
```

### Task 9.2: 创建角色管理页面

**Files:**
- Create: `frontend/src/app/admin/roles/page.tsx`
- Create: `frontend/src/app/admin/roles/components/RoleList.tsx`
- Create: `frontend/src/app/admin/roles/components/RolePermissionEditor.tsx`

**Step 1: 创建角色管理页面**

```typescript
// frontend/src/app/admin/roles/page.tsx
'use client'

import { ProtectedPage } from '@/components/auth/ProtectedPage'
import { RoleList } from './components/RoleList'

export default function RolesPage() {
  return (
    <ProtectedPage pageId="admin">
      <div className="container mx-auto py-6">
        <h1 className="text-3xl font-bold mb-6">Role Management</h1>
        <RoleList />
      </div>
    </ProtectedPage>
  )
}
```

**Step 2: 创建RoleList组件**

```typescript
// frontend/src/app/admin/roles/components/RoleList.tsx
'use client'

import { useEffect, useState } from 'react'
import { rolesApi, Role } from '@/lib/api'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

export function RoleList() {
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadRoles() {
      try {
        const data = await rolesApi.list()
        setRoles(data)
      } catch (error) {
        console.error('Failed to load roles:', error)
      } finally {
        setLoading(false)
      }
    }
    loadRoles()
  }, [])

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl">Roles ({roles.length})</h2>
        <Button>Create Role</Button>
      </div>

      <div className="grid gap-4">
        {roles.map((role) => (
          <div key={role.id} className="border rounded p-4 flex justify-between items-center">
            <div>
              <h3 className="font-semibold">{role.name}</h3>
              <p className="text-sm text-gray-600">{role.description || 'No description'}</p>
              {role.is_system && (
                <span className="text-xs bg-gray-100 px-2 py-1 rounded">System Role</span>
              )}
            </div>
            <Link href={`/admin/roles/${role.id}`}>
              <Button variant="outline">Edit Permissions</Button>
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Step 3: 创建角色权限编辑页面**

```typescript
// frontend/src/app/admin/roles/[id]/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { rolesApi, RoleDetail } from '@/lib/api'
import { ProtectedPage } from '@/components/auth/ProtectedPage'
import { RolePermissionEditor } from '../components/RolePermissionEditor'

export default function RoleDetailPage() {
  const params = useParams()
  const roleId = parseInt(params.id as string)
  const [role, setRole] = useState<RoleDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadRole() {
      try {
        const data = await rolesApi.get(roleId)
        setRole(data)
      } catch (error) {
        console.error('Failed to load role:', error)
      } finally {
        setLoading(false)
      }
    }
    loadRole()
  }, [roleId])

  if (loading) return <div>Loading...</div>
  if (!role) return <div>Role not found</div>

  return (
    <ProtectedPage pageId="admin">
      <div className="container mx-auto py-6">
        <h1 className="text-3xl font-bold mb-6">Edit Role: {role.name}</h1>
        <RolePermissionEditor role={role} />
      </div>
    </ProtectedPage>
  )
}
```

**Step 4: 创建RolePermissionEditor组件**

```typescript
// frontend/src/app/admin/roles/components/RolePermissionEditor.tsx
'use client'

import { useState } from 'react'
import { RoleDetail, rolesApi } from '@/lib/api'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'

interface RolePermissionEditorProps {
  role: RoleDetail
}

const ALL_PAGES = ['chat', 'rules', 'actions', 'data-products', 'ontology', 'admin'] as const

export function RolePermissionEditor({ role }: RolePermissionEditorProps) {
  const [loading, setLoading] = useState(false)

  const handleTogglePage = async (pageId: string) => {
    setLoading(true)
    try {
      if (role.page_permissions.includes(pageId)) {
        await rolesApi.removePagePermission(role.id, pageId)
      } else {
        await rolesApi.addPagePermission(role.id, pageId)
      }
      // 重新加载角色数据
      const updated = await rolesApi.get(role.id)
      role = updated
      // 触发重新渲染
      window.location.reload()
    } catch (error) {
      console.error('Failed to toggle page permission:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Tabs defaultValue="pages">
      <TabsList>
        <TabsTrigger value="pages">Page Permissions</TabsTrigger>
        <TabsTrigger value="actions">Action Permissions</TabsTrigger>
        <TabsTrigger value="entities">Entity Permissions</TabsTrigger>
      </TabsList>

      <TabsContent value="pages">
        <div className="space-y-2">
          {ALL_PAGES.map((pageId) => (
            <div key={pageId} className="flex items-center justify-between border p-3 rounded">
              <span className="font-medium">{pageId}</span>
              <Button
                variant={role.page_permissions.includes(pageId) ? 'default' : 'outline'}
                onClick={() => handleTogglePage(pageId)}
                disabled={loading || role.is_system}
              >
                {role.page_permissions.includes(pageId) ? 'Granted' : 'Grant'}
              </Button>
            </div>
          ))}
        </div>
      </TabsContent>

      <TabsContent value="actions">
        <div className="text-sm text-gray-600">
          Action permissions configuration (TODO: implement action selector)
        </div>
      </TabsContent>

      <TabsContent value="entities">
        <div className="text-sm text-gray-600">
          Entity type permissions configuration (TODO: implement entity selector)
        </div>
      </TabsContent>
    </Tabs>
  )
}
```

**Step 5: Commit**

```bash
git add frontend/src/app/admin/roles/
git commit -m "feat: add role management page"
```

---

## Phase 10: 测试

### Task 10.1: 编写后端测试

**Files:**
- Create: `backend/tests/test_permissions.py`

**Step 1: 创建权限测试文件**

```python
# backend/tests/test_permissions.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestPermissionService:
    """测试权限服务"""

    async def test_get_accessible_pages_for_admin(self, db: AsyncSession, admin_user: User):
        """Admin用户应能访问所有页面"""
        from app.services.permission_service import PermissionService

        pages = await PermissionService.get_accessible_pages(db, admin_user)
        assert set(pages) == set(PageId.all())

    async def test_get_accessible_pages_for_regular_user(self, db: AsyncSession, regular_user: User):
        """普通用户只能访问授权的页面"""
        from app.services.permission_service import PermissionService

        pages = await PermissionService.get_accessible_pages(db, regular_user)
        assert 'chat' in pages
        assert 'admin' not in pages


class TestUserAPI:
    """测试用户管理API"""

    async def test_create_user_as_admin(self, client: AsyncClient, admin_token: str):
        """Admin可以创建用户"""
        response = await client.post(
            "/api/users",
            json={"username": "testuser", "password": "password123"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["approval_status"] == "approved"

    async def test_create_user_as_regular_user_forbidden(
        self, client: AsyncClient, user_token: str
    ):
        """普通用户不能创建用户"""
        response = await client.post(
            "/api/users",
            json={"username": "testuser", "password": "password123"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403

    async def test_list_users_requires_admin(
        self, client: AsyncClient, user_token: str
    ):
        """列出用户需要admin权限"""
        response = await client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403


class TestAuthFlow:
    """测试认证流程"""

    async def test_register_creates_pending_user(self, client: AsyncClient):
        """注册后用户状态为pending"""
        response = await client.post(
            "/auth/register",
            json={"username": "newuser", "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Registration pending approval"

    async def test_pending_user_cannot_login(self, client: AsyncClient):
        """待审批用户无法登录"""
        # 先注册
        await client.post(
            "/auth/register",
            json={"username": "pendinguser", "password": "password123"}
        )

        # 尝试登录
        response = await client.post(
            "/auth/login",
            json={"username": "pendinguser", "password": "password123"}
        )
        assert response.status_code == 403
        assert "pending approval" in response.json()["detail"]

    async def test_admin_can_approve_user(
        self, client: AsyncClient, admin_token: str, db: AsyncSession
    ):
        """Admin可以审批用户"""
        # 注册用户
        await client.post(
            "/auth/register",
            json={"username": "approveuser", "password": "password123"}
        )

        # 获取待审批用户
        response = await client.get(
            "/api/users/pending-approvals",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users = response.json()["items"]
        user_id = next(u["id"] for u in users if u["username"] == "approveuser")

        # 审批通过
        response = await client.post(
            f"/api/users/{user_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

        # 现在可以登录
        response = await client.post(
            "/auth/login",
            json={"username": "approveuser", "password": "password123"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
```

**Step 2: 运行测试**

```bash
cd backend
pytest tests/test_permissions.py -v
```

**Step 3: Commit**

```bash
git add backend/tests/test_permissions.py
git commit -m "test: add permission and user management tests"
```

---

## 总结

实现完成后，系统将具备以下功能：

1. **用户管理**：Admin可创建、编辑、删除用户，重置密码
2. **用户审批**：新用户注册需admin审批后才能登录
3. **角色管理**：Admin可创建角色并配置权限
4. **页面访问控制**：基于功能模块的访问控制
5. **Action权限**：按具体action控制执行权限
6. **实体类型过滤**：API返回时过滤未授权的实体类型
7. **密码重置**：Admin可重置用户密码为默认值
