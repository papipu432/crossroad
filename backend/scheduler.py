"""
CROSSROAD — Scheduler & Dynamic Updater
=========================================
Daily scheduled scraping with intelligent delta updates.
Tracks changes in positions, party switches, new relationships, and breaking news.

Features:
  - Daily incremental crawls (only updated/changed content)
  - Weekly full refresh for critical sources (DPR, KPU)
  - Event-triggered scrapes (breaking news, elections, reshuffles)
  - Change detection with audit trail
  - Automatic party/coalition structure updates
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

import redis.asyncio as aioredis
from slugify import slugify

import db
from graph import GraphDB
from crawler.wiki import WikiCrawler
from crawler.news import NewsCrawler
from enricher.llm import LLMEnricher
from constants import SEED_OFFICIALS, OFFICIAL_SOURCES, KNOWN_PARTIES

logger = logging.getLogger(__name__)

REDIS_URL = "redis://redis:6379/0"


class ScheduleType(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    EVENT_TRIGGERED = "event"


@dataclass
class ScheduledTask:
    name: str
    schedule_type: ScheduleType
    interval_hours: int
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    priority: int = 5  # 1=highest, 10=lowest
    config: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class ChangeRecord:
    """Audit trail for detected changes."""
    timestamp: datetime
    entity_type: str  # person, party, relationship, position
    entity_id: str
    change_type: str  # created, updated, deleted, position_changed, party_switched
    old_value: Optional[Dict] = None
    new_value: Optional[Dict] = None
    source: str = ""
    confidence: float = 1.0


class DynamicUpdater:
    """
    Manages incremental updates and change detection.
    Only processes changed/new content to minimize API calls.
    """
    
    def __init__(self, graph_db: GraphDB, llm: LLMEnricher):
        self.graph_db = graph_db
        self.llm = llm
        self.redis: Optional[aioredis.Redis] = None
        self.change_log: List[ChangeRecord] = []
        
    async def _get_redis(self) -> aioredis.Redis:
        if not self.redis:
            self.redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        return self.redis
    
    async def get_last_crawl_hash(self, source: str) -> Optional[str]:
        """Get hash of last successful crawl for change detection."""
        r = await self._get_redis()
        return await r.get(f"crossroad:crawl_hash:{source}")
    
    async def set_crawl_hash(self, source: str, content_hash: str):
        """Store hash after successful crawl."""
        r = await self._get_redis()
        await r.set(f"crossroad:crawl_hash:{source}", content_hash, ex=86400*30)
    
    async def detect_position_changes(self) -> List[ChangeRecord]:
        """
        Check for position changes by re-scraping official sources.
        Compares current DB state with fresh data.
        """
        changes = []
        
        # Check DPR members
        try:
            from crawler.wiki_graph_crawler import parse_dpr_list
            fresh_dpr = await parse_dpr_list(OFFICIAL_SOURCES["wiki_list_dpr"])
            
            async with self.graph_db.driver.session() as session:
                for member in fresh_dpr:
                    name = member.get("name", "")
                    if not name:
                        continue
                    
                    slug = slugify(name, separator="-")
                    
                    # Get current record
                    result = await session.run("""
                        MATCH (p:Person {slug: $slug})
                        RETURN p.position AS position, p.party AS party, p.dapil AS dapil
                    """, {"slug": slug})
                    record = await result.single()
                    
                    if record:
                        current_pos = record["position"]
                        current_party = record["party"]
                        new_pos = member.get("position", "")
                        new_party = member.get("party", "")
                        
                        # Detect position change
                        if current_pos != new_pos and new_pos:
                            changes.append(ChangeRecord(
                                timestamp=datetime.now(timezone.utc),
                                entity_type="person",
                                entity_id=slug,
                                change_type="position_changed",
                                old_value={"position": current_pos},
                                new_value={"position": new_pos},
                                source="DPR Update",
                                confidence=0.95
                            ))
                        
                        # Detect party switch
                        if current_party != new_party and new_party:
                            changes.append(ChangeRecord(
                                timestamp=datetime.now(timezone.utc),
                                entity_type="person",
                                entity_id=slug,
                                change_type="party_switched",
                                old_value={"party": current_party},
                                new_value={"party": new_party},
                                source="DPR Update",
                                confidence=0.9
                            ))
                    else:
                        # New person discovered
                        changes.append(ChangeRecord(
                            timestamp=datetime.now(timezone.utc),
                            entity_type="person",
                            entity_id=slug,
                            change_type="created",
                            new_value=member,
                            source="DPR Discovery",
                            confidence=0.85
                        ))
        except Exception as e:
            logger.error(f"DPR change detection error: {e}")
        
        return changes
    
    async def detect_new_relationships(self, person_slug: str) -> List[ChangeRecord]:
        """Re-analyze a person's page for new relationships."""
        changes = []
        
        try:
            wiki_crawler = WikiCrawler(delay=1.0)
            url = f"https://id.wikipedia.org/wiki/{person_slug.replace('-', '_').title()}"
            
            # Re-crawl with fresh extraction
            extracted = await wiki_crawler.extract_person_info(url)
            
            if not extracted:
                return changes
            
            # Compare with existing relationships
            async with self.graph_db.driver.session() as session:
                result = await session.run("""
                    MATCH (p:Person {slug: $slug})-[:FAMILY_OF|WORKS_AT|MEMBER_OF|ALLIED_WITH]->(related)
                    RETURN related.slug AS slug, type(relationship) AS rel_type
                """, {"slug": person_slug})
                
                existing = await result.fetch()
                existing_set = {(r["slug"], r["rel_type"]) for r in existing}
            
            # Check for new family relationships
            for rel in extracted.get("relationships", []):
                rel_slug = slugify(rel.get("name", ""), separator="-")
                rel_type = rel.get("type", "")
                
                if (rel_slug, rel_type) not in existing_set:
                    changes.append(ChangeRecord(
                        timestamp=datetime.now(timezone.utc),
                        entity_type="relationship",
                        entity_id=f"{person_slug}->{rel_slug}",
                        change_type="created",
                        new_value={"from": person_slug, "to": rel_slug, "type": rel_type},
                        source="Wikipedia Re-crawl",
                        confidence=rel.get("confidence", 0.8)
                    ))
        except Exception as e:
            logger.warning(f"Relationship detection error for {person_slug}: {e}")
        
        return changes
    
    async def apply_change(self, change: ChangeRecord):
        """Apply a detected change to the database."""
        logger.info(f"Applying change: {change.change_type} on {change.entity_type}:{change.entity_id}")
        
        if change.entity_type == "person":
            if change.change_type == "position_changed":
                await db.update_person_position(
                    change.entity_id,
                    change.new_value.get("position", ""),
                    change.source
                )
                await self.graph_db.update_person_position(
                    change.entity_id,
                    change.new_value.get("position", "")
                )
            
            elif change.change_type == "party_switched":
                await db.update_person_party(
                    change.entity_id,
                    change.new_value.get("party", ""),
                    change.source
                )
                await self.graph_db.update_person_party(
                    change.entity_id,
                    change.new_value.get("party", "")
                )
            
            elif change.change_type == "created":
                await db.upsert_person({
                    "full_name": change.new_value.get("name", ""),
                    "role_type": change.new_value.get("role_type", "dpr"),
                    "current_position": change.new_value.get("position", ""),
                    "party": change.new_value.get("party", ""),
                    "province": change.new_value.get("province", ""),
                    "dapil": change.new_value.get("dapil", ""),
                    "sources": [{"name": change.source, "url": change.source}]
                })
        
        elif change.entity_type == "relationship":
            if change.change_type == "created":
                rel_data = change.new_value or {}
                await self.graph_db.create_relationship(
                    rel_data.get("from", ""),
                    rel_data.get("to", ""),
                    rel_data.get("type", "RELATED_TO"),
                    {"source": change.source, "detected_at": datetime.now(timezone.utc).isoformat()}
                )
        
        # Log change
        self.change_log.append(change)
        await self._store_change(change)
    
    async def _store_change(self, change: ChangeRecord):
        """Store change in Redis for audit trail."""
        r = await self._get_redis()
        change_data = {
            "timestamp": change.timestamp.isoformat(),
            "entity_type": change.entity_type,
            "entity_id": change.entity_id,
            "change_type": change.change_type,
            "old_value": change.old_value,
            "new_value": change.new_value,
            "source": change.source,
            "confidence": change.confidence
        }
        await r.lpush("crossroad:change_log", str(change_data))
        await r.ltrim("crossroad:change_log", 0, 999)  # Keep last 1000 changes
    
    async def get_recent_changes(self, hours: int = 24) -> List[Dict]:
        """Get recent changes from audit log."""
        r = await self._get_redis()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        raw = await r.lrange("crossroad:change_log", 0, 999)
        changes = []
        for item in raw:
            try:
                change = eval(item) if isinstance(item, str) else item
                if change.get("timestamp", "") >= cutoff:
                    changes.append(change)
            except:
                pass
        return changes


class Scheduler:
    """
    Main scheduler orchestrating all periodic tasks.
    Runs as background task in FastAPI app.
    """
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.graph_db: Optional[GraphDB] = None
        self.llm: Optional[LLMEnricher] = None
        self.updater: Optional[DynamicUpdater] = None
        
    def register_task(self, task: ScheduledTask):
        """Register a scheduled task."""
        self.tasks[task.name] = task
        task.next_run = datetime.now(timezone.utc) + timedelta(hours=task.interval_hours)
        logger.info(f"Registered task: {task.name} (every {task.interval_hours}h)")
    
    async def initialize(self):
        """Initialize scheduler with default tasks."""
        self.graph_db = GraphDB()
        self.llm = LLMEnricher()
        self.updater = DynamicUpdater(self.graph_db, self.llm)
        
        # Register default tasks
        self.register_task(ScheduledTask(
            name="daily_news_update",
            schedule_type=ScheduleType.DAILY,
            interval_hours=24,
            priority=1,
            config={"sources": "all", "max_articles_per_person": 5}
        ))
        
        self.register_task(ScheduledTask(
            name="weekly_dpr_refresh",
            schedule_type=ScheduleType.WEEKLY,
            interval_hours=168,
            priority=2,
            config={"source": "dpr", "detect_changes": True}
        ))
        
        self.register_task(ScheduledTask(
            name="weekly_wiki_deep_crawl",
            schedule_type=ScheduleType.WEEKLY,
            interval_hours=168,
            priority=3,
            config={"depth": 2, "top_n_persons": 50}
        ))
        
        self.register_task(ScheduledTask(
            name="daily_dynasty_recalc",
            schedule_type=ScheduleType.DAILY,
            interval_hours=24,
            priority=5,
            config={"min_members": 2}
        ))
        
        self.register_task(ScheduledTask(
            name="monthly_party_structure",
            schedule_type=ScheduleType.MONTHLY,
            interval_hours=720,
            priority=4,
            config={"update_coalitions": True, "update_factions": True}
        ))
    
    async def run_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        logger.info(f"Running task: {task.name}")
        task.last_run = datetime.now(timezone.utc)
        
        try:
            if task.name == "daily_news_update":
                await self._run_news_update(task.config)
            
            elif task.name == "weekly_dpr_refresh":
                await self._run_dpr_refresh(task.config)
            
            elif task.name == "weekly_wiki_deep_crawl":
                await self._run_wiki_crawl(task.config)
            
            elif task.name == "daily_dynasty_recalc":
                await self._run_dynasty_recalc(task.config)
            
            elif task.name == "monthly_party_structure":
                await self._run_party_update(task.config)
            
            task.errors.clear()
            logger.info(f"Task completed: {task.name}")
            
        except Exception as e:
            logger.error(f"Task {task.name} failed: {e}")
            task.errors.append(str(e))
        
        finally:
            task.next_run = datetime.now(timezone.utc) + timedelta(hours=task.interval_hours)
    
    async def _run_news_update(self, config: Dict):
        """Daily news update for all tracked persons."""
        from crawler.news import NewsCrawler
        
        news_crawler = NewsCrawler(delay=1.0, max_per_source=config.get("max_articles_per_person", 5))
        persons = await db.list_persons(limit=2000)
        
        logger.info(f"Updating news for {len(persons)} persons")
        
        for person in persons[:100]:  # Limit to top 100 most active
            name = person.get("full_name", "")
            if not name:
                continue
            
            try:
                articles = await news_crawler.crawl_person(name)
                if articles:
                    scored = await self.llm.score_news(person.get("party", ""), articles)
                    for article in scored[:5]:
                        await db.upsert_news(article)
            except Exception as e:
                logger.warning(f"News update failed for {name}: {e}")
            
            await asyncio.sleep(0.5)  # Rate limiting
    
    async def _run_dpr_refresh(self, config: Dict):
        """Weekly DPR member list refresh with change detection."""
        if not config.get("detect_changes", True):
            return
        
        logger.info("Running DPR change detection...")
        changes = await self.updater.detect_position_changes()
        
        for change in changes:
            await self.updater.apply_change(change)
        
        logger.info(f"DPR refresh complete: {len(changes)} changes detected")
    
    async def _run_wiki_crawl(self, config: Dict):
        """Weekly deep crawl of top N persons' Wikipedia pages."""
        from agents.graph_agent import GraphMiningAgent
        
        depth = config.get("depth", 2)
        top_n = config.get("top_n_persons", 50)
        
        # Get most connected persons
        async with self.graph_db.driver.session() as session:
            result = await session.run("""
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[r]-(other)
                RETURN p.slug AS slug, count(DISTINCT other) AS connections
                ORDER BY connections DESC
                LIMIT $limit
            """, {"limit": top_n})
            
            top_persons = await result.fetch()
        
        agent = GraphMiningAgent(
            graph_db=self.graph_db,
            llm=self.llm,
            max_depth=depth,
            max_nodes=500,
            concurrency=2,
            min_relevance=2
        )
        
        seed_urls = [
            f"https://id.wikipedia.org/wiki/{p['slug'].replace('-', '_').title()}"
            for p in top_persons
        ]
        
        logger.info(f"Deep crawling {len(seed_urls)} Wikipedia pages")
        stats = await agent.run(seed_urls, job_id=None)
        logger.info(f"Wiki crawl complete: {stats}")
    
    async def _run_dynasty_recalc(self, config: Dict):
        """Recalculate dynasty detection daily."""
        from intelligence.dynasties import DynastyDetector
        
        detector = DynastyDetector(graph_db=self.graph_db, db=db)
        dynasties = await detector.detect_all(min_members=config.get("min_members", 2))
        
        # Store in cache
        r = await self.updater._get_redis()
        import json
        await r.set("crossroad:dynasties_cache", json.dumps(dynasties), ex=86400)
        
        logger.info(f"Dynasty recalc complete: {len(dynasties)} dynasties detected")
    
    async def _run_party_update(self, config: Dict):
        """Monthly party structure and coalition update."""
        from intelligence.coalitions import CoalitionViewer
        
        if config.get("update_coalitions"):
            viewer = CoalitionViewer(db=db, graph_db=self.graph_db)
            coalitions = await viewer.get_all_coalitions()
            
            r = await self.updater._get_redis()
            import json
            await r.set("crossroad:coalitions_cache", json.dumps(coalitions), ex=86400*30)
        
        logger.info("Party structure update complete")
    
    async def start(self):
        """Start the scheduler loop."""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        await self.initialize()
        self.running = True
        
        logger.info("🕐 Scheduler started")
        
        while self.running:
            now = datetime.now(timezone.utc)
            
            # Find due tasks
            due_tasks = [
                task for task in self.tasks.values()
                if task.enabled and task.next_run and task.next_run <= now
            ]
            
            # Sort by priority
            due_tasks.sort(key=lambda t: t.priority)
            
            # Execute due tasks
            for task in due_tasks:
                if not self.running:
                    break
                await self.run_task(task)
                await asyncio.sleep(5)  # Gap between tasks
            
            # Sleep until next check
            await asyncio.sleep(60)
    
    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Scheduler stopped")
        
        if self.graph_db:
            await self.graph_db.close()


# Global scheduler instance
_scheduler: Optional[Scheduler] = None


async def start_scheduler():
    """Start background scheduler."""
    global _scheduler
    _scheduler = Scheduler()
    await _scheduler.start()


async def stop_scheduler():
    """Stop background scheduler."""
    global _scheduler
    if _scheduler:
        await _scheduler.stop()


def get_scheduler() -> Optional[Scheduler]:
    """Get scheduler instance."""
    return _scheduler
