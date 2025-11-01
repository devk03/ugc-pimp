from sqlalchemy import (
    create_engine, Column, String, Text, Date,
    ForeignKey, Index, DateTime, Integer, Numeric
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
import uuid
import os
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.sql import text
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable not set. "
        "Please set it in your .env file. "
        "Example: DATABASE_URL=postgresql://user:password@localhost:5432/dbname"
    )

# --- SQLAlchemy Setup ---
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20
)
Base = declarative_base()

# --------------------------------------------------------------------------
# TABLE DEFINITIONS
# --------------------------------------------------------------------------

class Brand(Base):
    """Brand/company information linked to Supabase auth."""
    __tablename__ = 'brands'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile = Column(String(36), nullable=False, comment="Supabase auth user ID (foreign key)")
    additional = Column(JSONB, nullable=True, comment="Additional brand metadata")

    # Relationships
    campaigns = relationship("Campaign", back_populates="brand")

    def __repr__(self):
        return f"<Brand(id='{self.id}', profile='{self.profile}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "profile": self.profile,
            "additional": self.additional,
        }


class Campaign(Base):
    """Marketing campaigns with asset storage paths."""
    __tablename__ = 'campaigns'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, comment="Campaign name")
    brand_id = Column(UUID(as_uuid=True), ForeignKey('brands.id', ondelete='CASCADE'), nullable=False)
    product = Column(Text, nullable=True, comment="Product name or description")
    asset_bucket_path = Column(Text, nullable=True, comment="S3/Supabase storage bucket path for campaign assets")
    description = Column(Text, nullable=True, comment="Campaign description")
    spend = Column(Numeric(12, 2), nullable=True, comment="Campaign spend amount")
    additional = Column(JSONB, nullable=True, comment="Additional campaign metadata")

    # Relationships
    brand = relationship("Brand", back_populates="campaigns")
    assets = relationship("Asset", back_populates="campaign")
    contact_campaigns = relationship("ContactCampaign", back_populates="campaign")

    # Indexes
    __table_args__ = (
        Index('idx_campaign_brand_id', 'brand_id'),
    )

    def __repr__(self):
        return f"<Campaign(id='{self.id}', name='{self.name}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "name": self.name,
            "brand_id": str(self.brand_id),
            "product": self.product,
            "asset_bucket_path": self.asset_bucket_path,
            "description": self.description,
            "spend": str(self.spend) if self.spend else None,
            "additional": self.additional,
        }


class Asset(Base):
    """Campaign assets stored in S3/Supabase storage."""
    __tablename__ = 'assets'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False)
    asset_path = Column(Text, nullable=False, comment="Storage path to the asset file")
    tag = Column(Text, nullable=True, comment="Asset tag or category")
    additional = Column(JSONB, nullable=True, comment="Additional asset metadata")

    # Relationships
    campaign = relationship("Campaign", back_populates="assets")

    # Indexes
    __table_args__ = (
        Index('idx_asset_campaign_id', 'campaign_id'),
    )

    def __repr__(self):
        return f"<Asset(id='{self.id}', campaign_id='{self.campaign_id}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id),
            "asset_path": self.asset_path,
            "tag": self.tag,
            "additional": self.additional,
        }


class Contact(Base):
    """Contact information with platform and tagging support."""
    __tablename__ = 'contacts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firstname = Column(Text, nullable=False, comment="Contact first name")
    lastname = Column(Text, nullable=False, comment="Contact last name")
    platform = Column(ARRAY(Text), nullable=True, comment="Social media platforms (e.g., ['instagram', 'tiktok'])")
    tags = Column(ARRAY(Text), nullable=True, comment="Contact tags for categorization")
    description = Column(Text, nullable=True, comment="Contact description or notes")
    additional = Column(JSONB, nullable=True, comment="Additional contact metadata")

    # Relationships
    contact_campaigns = relationship("ContactCampaign", back_populates="contact")

    def __repr__(self):
        return f"<Contact(id='{self.id}', name='{self.firstname} {self.lastname}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "firstname": self.firstname,
            "lastname": self.lastname,
            "platform": self.platform or [],
            "tags": self.tags or [],
            "description": self.description,
            "additional": self.additional,
        }


class ContactCampaign(Base):
    """Junction table linking contacts to campaigns."""
    __tablename__ = 'contact_campaigns'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), ForeignKey('contacts.id', ondelete='CASCADE'), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False)
    description = Column(Text, nullable=True, comment="Description of contact's role in campaign")
    additional = Column(JSONB, nullable=True, comment="Additional metadata for this relationship")

    # Relationships
    contact = relationship("Contact", back_populates="contact_campaigns")
    campaign = relationship("Campaign", back_populates="contact_campaigns")

    # Indexes
    __table_args__ = (
        Index('idx_contact_campaign_contact_id', 'contact_id'),
        Index('idx_contact_campaign_campaign_id', 'campaign_id'),
    )

    def __repr__(self):
        return f"<ContactCampaign(id='{self.id}', contact_id='{self.contact_id}', campaign_id='{self.campaign_id}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "contact_id": str(self.contact_id),
            "campaign_id": str(self.campaign_id),
            "description": self.description,
            "additional": self.additional,
        }


def setup_database():
    """Creates the database schema."""
    print("=" * 70)
    print("Setting up database schema...")
    print("=" * 70)
    print(f"Connecting to: {DATABASE_URL[:40]}...")
    print()

    # Create all tables
    print("Creating tables...")
    Base.metadata.create_all(engine)
    tables = ['brands', 'campaigns', 'assets', 'contacts', 'contact_campaigns']
    for table in tables:
        print(f"    {table}")
    print()

    print("=" * 70)
    print(" Database schema setup complete!")
    print("=" * 70)
    print()
    print("Tables created:")
    print("  - brands: Brand profiles linked to Supabase auth")
    print("  - campaigns: Marketing campaigns with S3/Supabase storage paths")
    print("  - assets: Campaign assets with storage paths")
    print("  - contacts: Contact information with platform and tags")
    print("  - contact_campaigns: Junction table linking contacts to campaigns")
    print()


if __name__ == "__main__":
    setup_database()
