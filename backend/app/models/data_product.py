# backend/app/models/data_product.py
"""
数据产品与数据映射模型

用于管理外部数据产品（gRPC 服务）的注册和与 Ontology 的映射关系。
支持实体映射、属性映射和关系映射，实现知识图谱与外部数据源的自动同步。
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Text,
    Enum as SQLEnum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ConnectionStatus(enum.Enum):
    """数据产品连接状态"""

    UNKNOWN = "unknown"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class SyncDirection(enum.Enum):
    """同步方向"""

    PULL = "pull"  # 从数据产品拉取到图谱
    PUSH = "push"  # 从图谱推送到数据产品
    BIDIRECTIONAL = "bidirectional"  # 双向同步


class DataProduct(Base):
    """数据产品注册表

    存储外部 gRPC 数据服务的注册信息。
    每个数据产品对应一个 gRPC 服务端点。
    """

    __tablename__ = "data_products"

    id = Column(Integer, primary_key=True, autoincrement="auto")
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)

    # gRPC 连接信息
    grpc_host = Column(String(255), nullable=False)
    grpc_port = Column(Integer, nullable=False, default=50051)
    service_name = Column(
        String(255), nullable=False
    )  # gRPC 服务名，如 "SupplierService"

    # Proto 定义（可选，用于离线解析）
    proto_content = Column(Text)

    # 连接状态
    connection_status = Column(
        SQLEnum(ConnectionStatus), default=ConnectionStatus.UNKNOWN
    )
    last_health_check = Column(DateTime)
    last_error = Column(Text)

    # 元数据
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    entity_mappings = relationship(
        "EntityMapping",
        back_populates="data_product",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_data_products_name", "name"),
        Index("idx_data_products_active", "is_active"),
    )

    def __repr__(self):
        return f"<DataProduct(id={self.id}, name='{self.name}', host='{self.grpc_host}:{self.grpc_port}')>"


class EntityMapping(Base):
    """实体类型映射表

    定义 Ontology 类与 gRPC Message 类型之间的映射关系。
    一个 Ontology 类可以映射到多个数据产品中的 Message 类型。
    """

    __tablename__ = "entity_mappings"

    id = Column(Integer, primary_key=True, autoincrement="auto")

    # 数据产品关联
    data_product_id = Column(
        Integer, ForeignKey("data_products.id", ondelete="CASCADE"), nullable=False
    )

    # 映射信息
    ontology_class_name = Column(String(255), nullable=False)  # Ontology 类名
    grpc_message_type = Column(String(255), nullable=False)  # gRPC Message 类型

    # gRPC 方法映射（可选，自动推断或手动配置）
    list_method = Column(String(255))  # 列表方法，如 "ListSuppliers"
    get_method = Column(String(255))  # 获取方法，如 "GetSupplier"
    create_method = Column(String(255))  # 创建方法，如 "CreateSupplier"
    update_method = Column(String(255))  # 更新方法，如 "UpdateSupplier"
    delete_method = Column(String(255))  # 删除方法，如 "DeleteSupplier"

    # 同步配置
    sync_enabled = Column(Boolean, default=True)
    sync_direction = Column(SQLEnum(SyncDirection), default=SyncDirection.PULL)

    # 标识字段映射（用于匹配图谱实例和数据产品记录）
    id_field_mapping = Column(String(255), default="id")  # gRPC 中的 ID 字段
    name_field_mapping = Column(
        String(255), default="name"
    )  # 用于生成图谱实体名称的字段

    # 元数据
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    data_product = relationship("DataProduct", back_populates="entity_mappings")
    property_mappings = relationship(
        "PropertyMapping",
        back_populates="entity_mapping",
        cascade="all, delete-orphan",
    )

    # 作为源或目标的关系映射
    source_relationship_mappings = relationship(
        "RelationshipMapping",
        foreign_keys="RelationshipMapping.source_entity_mapping_id",
        back_populates="source_entity_mapping",
        cascade="all, delete-orphan",
    )
    target_relationship_mappings = relationship(
        "RelationshipMapping",
        foreign_keys="RelationshipMapping.target_entity_mapping_id",
        back_populates="target_entity_mapping",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "data_product_id",
            "ontology_class_name",
            name="uq_entity_mapping_product_class",
        ),
        Index("idx_entity_mappings_product", "data_product_id"),
        Index("idx_entity_mappings_class", "ontology_class_name"),
    )

    def __repr__(self):
        return f"<EntityMapping(id={self.id}, class='{self.ontology_class_name}' <-> message='{self.grpc_message_type}')>"


class PropertyMapping(Base):
    """属性字段映射表

    定义 Ontology 属性与 gRPC 字段之间的映射关系。
    支持数据类型转换和自定义表达式。
    """

    __tablename__ = "property_mappings"

    id = Column(Integer, primary_key=True, autoincrement="auto")

    # 实体映射关联
    entity_mapping_id = Column(
        Integer, ForeignKey("entity_mappings.id", ondelete="CASCADE"), nullable=False
    )

    # 映射信息
    ontology_property = Column(String(255), nullable=False)  # Ontology 属性名
    grpc_field = Column(String(255), nullable=False)  # gRPC 字段名

    # 类型转换（可选）
    transform_expression = Column(Text)  # Python 表达式，如 "value.upper()"
    inverse_transform = Column(Text)  # 反向转换表达式

    # 配置
    is_required = Column(Boolean, default=False)
    sync_on_update = Column(Boolean, default=True)  # 更新时是否同步

    # 元数据
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    entity_mapping = relationship("EntityMapping", back_populates="property_mappings")

    __table_args__ = (
        UniqueConstraint(
            "entity_mapping_id",
            "ontology_property",
            name="uq_property_mapping_entity_prop",
        ),
        Index("idx_property_mappings_entity", "entity_mapping_id"),
    )

    def __repr__(self):
        return f"<PropertyMapping(id={self.id}, prop='{self.ontology_property}' <-> field='{self.grpc_field}')>"


class RelationshipMapping(Base):
    """关系映射表

    定义 Ontology 关系与数据产品外键之间的映射。
    通过外键字段关联两个已映射的实体类型。
    """

    __tablename__ = "relationship_mappings"

    id = Column(Integer, primary_key=True, autoincrement="auto")

    # 源实体映射（关系的起始端）
    source_entity_mapping_id = Column(
        Integer, ForeignKey("entity_mappings.id", ondelete="CASCADE"), nullable=False
    )

    # 目标实体映射（关系的终点）
    target_entity_mapping_id = Column(
        Integer, ForeignKey("entity_mappings.id", ondelete="CASCADE"), nullable=False
    )

    # Ontology 关系类型
    ontology_relationship = Column(String(255), nullable=False)  # 如 "orderedFrom"

    # 外键映射
    source_fk_field = Column(
        String(255), nullable=False
    )  # 源实体中的外键字段，如 "supplier_id"
    target_id_field = Column(String(255), default="id")  # 目标实体的 ID 字段

    # 同步配置
    sync_enabled = Column(Boolean, default=True)

    # 元数据
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    source_entity_mapping = relationship(
        "EntityMapping",
        foreign_keys=[source_entity_mapping_id],
        back_populates="source_relationship_mappings",
    )
    target_entity_mapping = relationship(
        "EntityMapping",
        foreign_keys=[target_entity_mapping_id],
        back_populates="target_relationship_mappings",
    )

    __table_args__ = (
        UniqueConstraint(
            "source_entity_mapping_id",
            "target_entity_mapping_id",
            "ontology_relationship",
            name="uq_relationship_mapping",
        ),
        Index("idx_relationship_mappings_source", "source_entity_mapping_id"),
        Index("idx_relationship_mappings_target", "target_entity_mapping_id"),
    )

    def __repr__(self):
        return (
            f"<RelationshipMapping(id={self.id}, rel='{self.ontology_relationship}')>"
        )


class SyncLog(Base):
    """同步日志表

    记录数据同步的执行历史和结果。
    """

    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement="auto")

    # 关联信息（可以是数据产品级别或实体映射级别）
    data_product_id = Column(
        Integer, ForeignKey("data_products.id", ondelete="SET NULL"), nullable=True
    )
    entity_mapping_id = Column(
        Integer, ForeignKey("entity_mappings.id", ondelete="SET NULL"), nullable=True
    )

    # 同步信息
    sync_type = Column(String(50))  # "full", "incremental", "manual"
    direction = Column(String(20))  # "pull", "push"

    # 结果
    status = Column(String(50))  # "started", "completed", "failed"
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_message = Column(Text)

    # 时间
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)

    __table_args__ = (
        Index("idx_sync_logs_product", "data_product_id"),
        Index("idx_sync_logs_entity", "entity_mapping_id"),
        Index("idx_sync_logs_time", "started_at"),
    )

    def __repr__(self):
        return f"<SyncLog(id={self.id}, status='{self.status}', processed={self.records_processed})>"
