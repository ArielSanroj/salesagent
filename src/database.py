#!/usr/bin/env python3
"""
Database Models and Service for HR Tech Lead Generation System
Uses SQLModel for type-safe database operations
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlmodel import Field, SQLModel, create_engine as create_sqlmodel_engine

from .constants import SIGNAL_TYPES

logger = logging.getLogger(__name__)


class OpportunityDB(SQLModel, table=True):
    """Database model for opportunities"""

    __tablename__ = "opportunities"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    company: str = Field(index=True)
    person: str
    email: str = Field(index=True)
    url: str
    date: str
    content: str
    relevance_score: float = Field(index=True)
    signal_type: int = Field(index=True)
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Additional metadata
    email_validated: bool = Field(default=False)
    contacted: bool = Field(default=False)
    contacted_at: Optional[datetime] = None
    notes: Optional[str] = None

    def to_opportunity(self) -> "Opportunity":  # type: ignore
        """Convert to Opportunity dataclass"""
        try:
            from .models import Opportunity
        except ImportError:
            from models import Opportunity
        return Opportunity(
            title=self.title,
            company=self.company,
            person=self.person,
            email=self.email,
            url=self.url,
            date=self.date,
            content=self.content,
            relevance_score=self.relevance_score,
            signal_type=self.signal_type,
            source=self.source,
        )

    @classmethod
    def from_opportunity(cls, opp: "Opportunity") -> "OpportunityDB":  # type: ignore
        """Create from Opportunity dataclass"""
        # opp is already an Opportunity instance, no need to import
        return cls(
            title=opp.title,
            company=opp.company,
            person=opp.person,
            email=opp.email,
            url=opp.url,
            date=opp.date,
            content=opp.content,
            relevance_score=opp.relevance_score,
            signal_type=opp.signal_type,
            source=opp.source,
        )


class DatabaseService:
    """Service for database operations"""

    def __init__(self, database_url: str = "sqlite:///opportunities.db"):
        """
        Initialize database service
        
        Args:
            database_url: Database connection URL
                         Examples:
                         - SQLite: "sqlite:///opportunities.db"
                         - PostgreSQL: "postgresql://user:pass@localhost/dbname"
        """
        self.database_url = database_url
        self.engine = create_sqlmodel_engine(database_url, echo=False)
        self._create_tables()

    def _create_tables(self) -> None:
        """Create all database tables"""
        SQLModel.metadata.create_all(self.engine)
        logger.info(f"✅ Database tables created/verified: {self.database_url}")

    def save_opportunities(self, opportunities: List) -> int:  # type: ignore
        """Save opportunities to database, avoiding duplicates"""
        if not opportunities:
            return 0

        saved_count = 0
        with Session(self.engine) as session:
            for opp in opportunities:
                try:
                    # Check if opportunity already exists (by email or company+person)
                    existing = None
                    
                    # First check by email if available
                    if opp.email and opp.email != "Manual validation needed":
                        existing = session.exec(
                            select(OpportunityDB).where(OpportunityDB.email == opp.email)
                        ).first()
                    
                    # If not found by email, check by company + person
                    if not existing:
                        existing = session.exec(
                            select(OpportunityDB).where(
                                OpportunityDB.company == opp.company,
                                OpportunityDB.person == opp.person,
                            )
                        ).first()

                    if existing:
                        # Update existing record if relevance score is higher
                        if opp.relevance_score > existing.relevance_score:
                            existing.relevance_score = opp.relevance_score
                            existing.updated_at = datetime.now(timezone.utc)
                            session.add(existing)
                            saved_count += 1
                            logger.debug(f"Updated opportunity: {opp.company} - {opp.person}")
                    else:
                        # Create new record
                        opp_db = OpportunityDB.from_opportunity(opp)
                        session.add(opp_db)
                        saved_count += 1
                        logger.debug(f"Saved new opportunity: {opp.company} - {opp.person}")

                except Exception as e:
                    logger.error(f"Error saving opportunity {opp.company}: {e}")
                    continue

            session.commit()

        logger.info(f"✅ Saved {saved_count} opportunities to database")
        return saved_count

    def get_opportunities(
        self,
        signal_type: Optional[int] = None,
        min_relevance: float = 0.0,
        limit: Optional[int] = None,
        order_by: str = "relevance_score",
        descending: bool = True,
    ) -> List[OpportunityDB]:
        """Get opportunities from database with filters"""
        with Session(self.engine) as session:
            query = select(OpportunityDB)

            # Apply filters
            if signal_type:
                query = query.where(OpportunityDB.signal_type == signal_type)
            
            if min_relevance > 0:
                query = query.where(OpportunityDB.relevance_score >= min_relevance)

            # Apply ordering
            if order_by == "relevance_score":
                if descending:
                    query = query.order_by(OpportunityDB.relevance_score.desc())
                else:
                    query = query.order_by(OpportunityDB.relevance_score.asc())
            elif order_by == "created_at":
                if descending:
                    query = query.order_by(OpportunityDB.created_at.desc())
                else:
                    query = query.order_by(OpportunityDB.created_at.asc())

            # Apply limit
            if limit:
                query = query.limit(limit)

            results = session.exec(query).all()
            return list(results)

    def get_opportunity_by_id(self, opportunity_id: int) -> Optional[OpportunityDB]:
        """Get opportunity by ID"""
        with Session(self.engine) as session:
            return session.get(OpportunityDB, opportunity_id)

    def update_opportunity(self, opportunity_id: int, **kwargs) -> bool:
        """Update opportunity fields"""
        with Session(self.engine) as session:
            opp = session.get(OpportunityDB, opportunity_id)
            if not opp:
                return False

            for key, value in kwargs.items():
                if hasattr(opp, key):
                    setattr(opp, key, value)

            opp.updated_at = datetime.now(timezone.utc)
            session.add(opp)
            session.commit()
            return True

    def mark_contacted(self, opportunity_id: int, notes: Optional[str] = None) -> bool:
        """Mark opportunity as contacted"""
        return self.update_opportunity(
            opportunity_id,
            contacted=True,
            contacted_at=datetime.now(timezone.utc),
            notes=notes,
        )

    def get_statistics(self) -> dict:
        """Get database statistics"""
        with Session(self.engine) as session:
            total = session.exec(select(OpportunityDB)).all()
            total_count = len(total)

            if total_count == 0:
                return {
                    "total_opportunities": 0,
                    "by_signal": {},
                    "avg_relevance": 0,
                    "contacted_count": 0,
                    "email_validated_count": 0,
                }

            # Count by signal
            by_signal = {}
            for signal_id in SIGNAL_TYPES.keys():
                count = len(
                    session.exec(
                        select(OpportunityDB).where(OpportunityDB.signal_type == signal_id)
                    ).all()
                )
                by_signal[signal_id] = count

            # Average relevance
            avg_relevance = sum(opp.relevance_score for opp in total) / total_count

            # Contacted count
            contacted_count = len(
                session.exec(
                    select(OpportunityDB).where(OpportunityDB.contacted == True)
                ).all()
            )

            # Email validated count
            email_validated_count = len(
                session.exec(
                    select(OpportunityDB).where(OpportunityDB.email_validated == True)
                ).all()
            )

            return {
                "total_opportunities": total_count,
                "by_signal": by_signal,
                "avg_relevance": round(avg_relevance, 3),
                "contacted_count": contacted_count,
                "email_validated_count": email_validated_count,
                "contacted_percentage": round((contacted_count / total_count) * 100, 1) if total_count > 0 else 0,
            }

    def delete_opportunity(self, opportunity_id: int) -> bool:
        """Delete opportunity by ID"""
        with Session(self.engine) as session:
            opp = session.get(OpportunityDB, opportunity_id)
            if not opp:
                return False

            session.delete(opp)
            session.commit()
            return True

    def clear_old_opportunities(self, days: int = 90) -> int:
        """Delete opportunities older than specified days"""
        cutoff_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)

        with Session(self.engine) as session:
            # This is a simplified version - in production, you'd parse the date string
            # For now, we'll delete based on created_at
            old_opps = session.exec(
                select(OpportunityDB).where(OpportunityDB.created_at < cutoff_date)
            ).all()

            count = len(old_opps)
            for opp in old_opps:
                session.delete(opp)

            session.commit()
            logger.info(f"🗑️  Deleted {count} old opportunities (older than {days} days)")
            return count

