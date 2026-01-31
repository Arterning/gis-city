"""POI data model for PostGIS."""
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from database import Base


class POI(Base):
    """Point of Interest model."""

    __tablename__ = "poi"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Basic fields
    name = Column(String(255), nullable=False, index=True, comment="POI名称")
    poi_type = Column(String(100), index=True, comment="POI类型")
    address = Column(String(500), comment="地址")

    # Geometry field (supports Point, Polygon, MultiPolygon, etc. with SRID 4326 - WGS84)
    geom = Column(
        Geometry(srid=4326),
        nullable=False,
        comment="几何对象（支持点、线、面，WGS84坐标系）"
    )

    # Custom properties (flexible JSONB field)
    properties = Column(JSONB, comment="自定义属性（JSON格式）")

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    def __repr__(self):
        return f"<POI(id={self.id}, name='{self.name}', type='{self.poi_type}')>"

    def to_dict(self):
        """Convert POI to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "poi_type": self.poi_type,
            "address": self.address,
            "properties": self.properties,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
