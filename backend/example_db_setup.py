# --------------------------------------------------------------------------
# File: database_setup.py
# --------------------------------------------------------------------------
# Description: Defines the BACKEND API PostgreSQL schema for Supabase.
#              This creates tables used by the FastAPI server ONLY.
#
#              BACKEND TABLES (Supabase - this file):
#              - documents: Core document metadata with pgvector embeddings
#              - procurement_notices: Active SAM.gov procurement notices/opportunities
#              - users: User profiles and business information
#              - saved_documents: User-saved documents (notices, grants, etc.)
#              - stripe_customers: Subscription billing
#
#              RECSYS TABLES (Local PostgreSQL - backend/recsys/database_setup.py):
#              - agencies, entities, codes, procurement_notices, awards, etc.
#              - These are NOT created by this file!
# --------------------------------------------------------------------------

from sqlalchemy import (
    create_engine, Column, String, Text, Date, Boolean,
    ForeignKey, Index, JSON, DateTime
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
import os
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy.sql import text
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Sequence
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get DATABASE_URL from environment (for Supabase)
# This is separate from recsys settings which uses local PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable not set. "
        "Please set it in your .env file to your Supabase connection string. "
        "Example: DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:5432/postgres"
    )

# Text embedding dimension (for pgvector columns)
# Gemini embedding-001 returns 768 dimensions
TEXT_EMBEDDING_DIM = 768

# --- SQLAlchemy Setup ---
# Configure engine with connection pooling for Supabase
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,      # Test connections before using to avoid stale connections
    pool_recycle=300,        # Recycle connections after 5 minutes
    pool_size=10,            # Connection pool size
    max_overflow=20          # Max overflow connections
)
Base = declarative_base()

# --------------------------------------------------------------------------
# BACKEND API TABLE DEFINITIONS (for Supabase)
# --------------------------------------------------------------------------

class SqlUser(Base):
    """User profiles table for storing business profile information."""
    __tablename__ = 'users'

    user_id = Column(String(36), primary_key=True, comment="Supabase user UID from auth system")
    uei = Column(String(12), nullable=True, comment="Unique Entity ID if user represents a business entity")
    legal_name = Column(String(255), nullable=False, comment="User's legal business name or personal name")
    dba_name = Column(String(255), nullable=True, comment="Doing Business As name")
    parent_uei = Column(String(12), nullable=True, comment="Parent entity UEI if applicable")
    geohash = Column(String(12), nullable=True, comment="Geographic location hash")
    website = Column(String(255), nullable=True, comment="User's website URL")

    # Business classification information
    entity_structure_code = Column(String(10), nullable=True, comment="Entity structure (LLC, Corp, etc.)")
    primary_naics = Column(String(10), nullable=True, comment="Primary NAICS code")

    # List-based features (stored as JSON for flexibility)
    all_naics_codes = Column(JSON, nullable=True, comment="All NAICS codes associated with user")
    all_psc_codes = Column(JSON, nullable=True, comment="All PSC codes associated with user")
    sba_business_types = Column(JSON, nullable=True, comment="SBA business type classifications")

    # Profile description and embeddings
    profile_description = Column(JSON, nullable=True, comment="User's profile description as array of strings")
    description_embedding = Column(Vector(TEXT_EMBEDDING_DIM), comment="Embeddings for profile description")

    # Metadata and timestamps
    created_at = Column(Date, nullable=True)
    updated_at = Column(Date, nullable=True)

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', legal_name='{self.legal_name}')>"


class SqlDocument(Base):
    """Generic documents table for storing document metadata."""
    __tablename__ = 'documents'

    doc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, comment="AI-generated description from document content")
    fulltext = Column(Text, comment="Concatenated title + description for search")
    dense_embedding = Column(Vector(TEXT_EMBEDDING_DIM), comment="Gemini embedding-001 vector for semantic search")
    document_type = Column(String(50))
    file_path = Column(String(500))
    created_date = Column(Date)
    updated_date = Column(Date)


class SqlProcurementNotice(Base):
    """Procurement notices from SAM.gov."""
    __tablename__ = 'procurement_notices'

    doc_id = Column(UUID(as_uuid=True), ForeignKey('documents.doc_id', ondelete='CASCADE'), primary_key=True)
    solicitation_number = Column(Text)
    classification_code = Column(Text)
    posted_date = Column(Date)
    due_date = Column(Date)
    contact = Column(Text)
    agency = Column(Text)
    sub_agency = Column(Text)
    offices = Column(ARRAY(Text))
    naics_code = Column(Text)
    set_aside = Column(Text)
    notice_type = Column(Text)
    sam_gov_url = Column(Text, comment="Browser URL for viewing the contract (uiLink)")
    description_url = Column(Text, comment="API URL for fetching the description HTML content")
    summary = Column(Text, comment="Original description from SAM.gov")
    pdf_links = Column(ARRAY(Text))

    # AI-generated fields
    ai_generated_summary = Column(Text, nullable=True, comment="AI-generated concise summary of the notice")
    ai_key_requirements = Column(JSON, nullable=True, comment="AI-extracted key requirements as JSON array")

    document = relationship("SqlDocument")


class SavedDocument(Base):
    """User favorites/saved documents table (procurement notices, grants, etc.)."""
    __tablename__ = 'saved_documents'

    # Composite primary key for user + document
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True, comment="Supabase user UID from auth system")
    doc_id = Column(UUID(as_uuid=True), ForeignKey('documents.doc_id', ondelete='CASCADE'), primary_key=True, comment="Reference to document ID")

    # Metadata about the saved document
    user_notes = Column(Text, nullable=True, comment="Optional user notes about this document")
    tags = Column(JSON, default=list, comment="User-defined tags")

    # Timestamps
    saved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # User preferences for this contract
    is_favorite = Column(Boolean, default=False, nullable=False)
    reminder_date = Column(DateTime(timezone=True), nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index('idx_saved_documents_user_saved_at', 'user_id', 'saved_at'),
        Index('idx_saved_documents_user_favorite', 'user_id', 'is_favorite'),
    )

    def __repr__(self):
        return f"<SavedDocument(user_id='{self.user_id}', doc_id='{self.doc_id}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "doc_id": str(self.doc_id),
            "user_notes": self.user_notes,
            "tags": self.tags or [],
            "saved_at": self.saved_at.isoformat() if self.saved_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None,
            "is_favorite": self.is_favorite,
            "reminder_date": self.reminder_date.isoformat() if self.reminder_date is not None else None
        }

    @classmethod
    def get_user_documents(
        cls,
        db: Session,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        favorites_only: bool = False
    ) -> Sequence['SavedDocument']:
        """Get saved documents for a user with pagination."""
        query = db.query(cls).filter(cls.user_id == user_id)

        if favorites_only:
            query = query.filter(cls.is_favorite == True)

        return query.order_by(cls.saved_at.desc()).offset(offset).limit(limit).all()

    @classmethod
    def save_document(
        cls,
        db: Session,
        user_id: str,
        doc_id: str,
        user_notes: Optional[str] = None,
        tags: Optional[list] = None
    ) -> 'SavedDocument':
        """Save a document for a user (upsert operation)."""
        import logging
        from uuid import UUID
        logger = logging.getLogger(__name__)

        # Convert doc_id to UUID if it's a string
        doc_uuid = UUID(doc_id) if isinstance(doc_id, str) else doc_id

        # Check if already saved
        existing = db.query(cls).filter(
            cls.user_id == user_id,
            cls.doc_id == doc_uuid
        ).first()

        if existing:
            # Update existing
            existing.user_notes = user_notes
            existing.tags = tags or []
            existing.updated_at = datetime.now(timezone.utc)
            saved_document = existing
            logger.info(f"Updated saved document {doc_id} for user {user_id}")
        else:
            # Create new
            saved_document = cls(
                user_id=user_id,
                doc_id=doc_uuid,
                user_notes=user_notes,
                tags=tags or []
            )
            db.add(saved_document)
            logger.info(f"Saved document {doc_id} for user {user_id}")

        try:
            db.commit()
            return saved_document
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save document {doc_id} for user {user_id}: {e}")
            raise


# Alias for backward compatibility with old API routes
SavedContract = SavedDocument


class StripeCustomer(Base):
    """Stripe billing table for subscription management."""
    __tablename__ = 'stripe_customers'

    # Primary key - links to User table
    user_id = Column(String(36), ForeignKey('users.user_id'), primary_key=True, comment="Supabase user UID")

    # Stripe identifiers
    stripe_customer_id = Column(String(100), unique=True, nullable=False, index=True, comment="Stripe customer ID (cus_...)")
    stripe_subscription_id = Column(String(100), nullable=True, comment="Stripe subscription ID (sub_...)")

    # Subscription details
    subscription_status = Column(String(50), nullable=True, comment="active, canceled, past_due, trialing, etc.")
    subscription_current_period_end = Column(DateTime(timezone=True), nullable=True, comment="When current billing period ends")
    cancel_at_period_end = Column(Boolean, default=False, nullable=False, comment="Whether subscription will cancel at period end")

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_stripe_customer_id', 'stripe_customer_id'),
        Index('idx_subscription_status', 'subscription_status'),
    )

    def __repr__(self):
        return f"<StripeCustomer(user_id='{self.user_id}', status='{self.subscription_status}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "user_id": self.user_id,
            "stripe_customer_id": self.stripe_customer_id,
            "stripe_subscription_id": self.stripe_subscription_id,
            "subscription_status": self.subscription_status,
            "subscription_current_period_end": self.subscription_current_period_end.isoformat() if self.subscription_current_period_end is not None else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None,
        }

    @classmethod
    def get_by_user_id(cls, db: Session, user_id: str) -> Optional['StripeCustomer']:
        """Get Stripe customer by user ID."""
        return db.query(cls).filter(cls.user_id == user_id).first()

    @classmethod
    def get_by_stripe_customer_id(cls, db: Session, stripe_customer_id: str) -> Optional['StripeCustomer']:
        """Get Stripe customer by Stripe customer ID."""
        return db.query(cls).filter(cls.stripe_customer_id == stripe_customer_id).first()

    @classmethod
    def get_by_subscription_id(cls, db: Session, subscription_id: str) -> Optional['StripeCustomer']:
        """Get Stripe customer by subscription ID."""
        return db.query(cls).filter(cls.stripe_subscription_id == subscription_id).first()


class JobsQueue(Base):
    """A job queue for background processing tasks."""
    __tablename__ = 'jobs_queue'

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(UUID(as_uuid=True), ForeignKey('documents.doc_id', ondelete='CASCADE'), nullable=False, index=True)
    process_type = Column(String(100), nullable=False, index=True, comment="e.g., 'description_generation', 'es_indexing'")
    status = Column(String(50), nullable=False, default='pending', index=True, comment="pending, processing, completed, failed")
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index('idx_jobs_queue_status_type', 'status', 'process_type'),
    )

    def __repr__(self):
        return f"<JobsQueue(job_id='{self.job_id}', doc_id='{self.doc_id}', type='{self.process_type}', status='{self.status}')>"


class ProcessLog(Base):
    """Log table for tracking ingestion and indexing processes."""
    __tablename__ = 'process_logs'

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_name = Column(String(100), nullable=False, index=True, comment="e.g., 'sam_ingestion', 'indexing'")
    status = Column(String(50), nullable=False, comment="running, completed, failed")
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Simple metrics
    total_count = Column(JSON, nullable=True, comment="Process-specific metrics (e.g., {'fetched': 100, 'inserted': 95})")
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_process_logs_name_started', 'process_name', 'started_at'),
    )

    def __repr__(self):
        return f"<ProcessLog(process_name='{self.process_name}', status='{self.status}', started_at='{self.started_at}')>"


def setup_database():
    """Creates the backend API database schema in Supabase."""
    print("=" * 70)
    print("Setting up BACKEND API database schema in Supabase...")
    print("=" * 70)
    print(f"Connecting to: {DATABASE_URL[:40]}...")
    print()

    # Enable pgvector extension
    print("1. Enabling pgvector extension...")
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        connection.commit()
    print("   ✓ pgvector extension enabled")
    print()

    # Create all tables
    print("2. Creating tables...")
    Base.metadata.create_all(engine)
    tables = ['users', 'documents', 'procurement_notices', 'saved_documents', 'stripe_customers', 'jobs_queue', 'process_logs']
    for table in tables:
        print(f"   ✓ {table}")
    print()

    # Create HNSW index for dense embeddings
    print("3. Creating HNSW index for vector similarity search...")
    with engine.connect() as connection:
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_documents_dense_embedding
            ON documents USING hnsw (dense_embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """))
        connection.commit()
    print("   ✓ HNSW index created")
    print()

    print("=" * 70)
    print("✅ Backend API database schema setup complete!")
    print("=" * 70)
    print()
    print("Tables created in Supabase:")
    print("  - users: User profiles and business information")
    print("  - documents: Core document metadata with embeddings")
    print("  - procurement_notices: SAM.gov procurement notices/opportunities")
    print("  - saved_documents: User-saved documents (notices, grants, etc.)")
    print("  - stripe_customers: Subscription billing")
    print("  - jobs_queue: A central queue for background processing tasks")
    print("  - process_logs: Logs for ingestion and indexing processes")
    print()
    print("NOTE: This does NOT include RecSys tables (agencies, entities, etc.)")
    print("      Those remain in your local PostgreSQL via backend/recsys/database_setup.py")
    print()


if __name__ == "__main__":
    setup_database()
