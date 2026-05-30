"""
Neo4j Knowledge Graph client for Crossroad.
Stores all entities (persons, orgs, news) and their relationships
as a queryable graph. Powers the relationship explorer UI.
"""
import logging
import os
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver

logger = logging.getLogger(__name__)

NEO4J_URI  = os.getenv("NEO4J_URI",  "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "crossroad2025")


class GraphDB:
    def __init__(self):
        self._driver: Optional[AsyncDriver] = None

    @property
    def driver(self) -> AsyncDriver:
        if not self._driver:
            self._driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        return self._driver

    async def ping(self) -> bool:
        try:
            async with self.driver.session() as s:
                await s.run("RETURN 1")
            return True
        except Exception as e:
            logger.warning(f"Neo4j ping: {e}")
            return False

    async def close(self):
        if self._driver:
            await self._driver.close()

    async def init_schema(self):
        constraints = [
            "CREATE CONSTRAINT person_slug IF NOT EXISTS FOR (p:Person) REQUIRE p.slug IS UNIQUE",
            "CREATE CONSTRAINT org_slug IF NOT EXISTS FOR (o:Org) REQUIRE o.slug IS UNIQUE",
            "CREATE CONSTRAINT news_url IF NOT EXISTS FOR (n:News) REQUIRE n.url IS UNIQUE",
            "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)",
            "CREATE INDEX person_party IF NOT EXISTS FOR (p:Person) ON (p.party)",
            "CREATE INDEX person_role IF NOT EXISTS FOR (p:Person) ON (p.role_type)",
        ]
        async with self.driver.session() as s:
            for q in constraints:
                try:
                    await s.run(q)
                except Exception as e:
                    logger.warning(f"Schema: {e}")
        logger.info("Neo4j schema initialised")

    # ── Person nodes ──────────────────────────────────────────────────────────

    async def upsert_person(self, p: Dict):
        q = """
        MERGE (n:Person {slug: $slug})
        SET n.name         = $name,
            n.role_type    = $role_type,
            n.position     = $position,
            n.party        = $party,
            n.faction      = $faction,
            n.province     = $province,
            n.dapil        = $dapil,
            n.born         = $born,
            n.photo_url    = $photo_url,
            n.wiki_url     = $wiki_url,
            n.pg_id        = $pg_id,
            n.updated_at   = timestamp()
        """
        async with self.driver.session() as s:
            await s.run(q, {
                "slug":     p.get("slug",""),
                "name":     p.get("full_name") or p.get("name",""),
                "role_type":p.get("role_type"),
                "position": p.get("current_position") or p.get("position"),
                "party":    p.get("party"),
                "faction":  p.get("faction"),
                "province": p.get("province"),
                "dapil":    p.get("dapil"),
                "born":     p.get("born"),
                "photo_url":p.get("photo_url"),
                "wiki_url": p.get("wiki_url_id") or p.get("wiki_url"),
                "pg_id":    p.get("id"),
            })

    # ── Org nodes ─────────────────────────────────────────────────────────────

    async def upsert_org(self, o: Dict):
        q = """
        MERGE (n:Org {slug: $slug})
        SET n.name     = $name,
            n.org_type = $org_type,
            n.founded  = $founded
        """
        async with self.driver.session() as s:
            await s.run(q, {
                "slug":     o.get("slug",""),
                "name":     o.get("name",""),
                "org_type": o.get("org_type",""),
                "founded":  o.get("founded"),
            })

    # ── Relationships ─────────────────────────────────────────────────────────

    async def upsert_relationship(self, from_slug: str, from_label: str,
                                   to_slug: str, to_label: str,
                                   rel_type: str, props: Dict = None):
        """Create or merge a labelled directed relationship."""
        props = props or {}
        rel_cypher_type = rel_type.upper().replace("-", "_").replace(" ", "_")
        q = f"""
        MATCH (a:{from_label} {{slug: $from_slug}})
        MATCH (b:{to_label}   {{slug: $to_slug}})
        MERGE (a)-[r:{rel_cypher_type}]->(b)
        SET r.subtype    = $subtype,
            r.label      = $label,
            r.year_start = $year_start,
            r.year_end   = $year_end,
            r.is_current = $is_current,
            r.weight     = $weight,
            r.source_url = $source_url,
            r.evidence   = $evidence,
            r.confidence = $confidence
        """
        async with self.driver.session() as s:
            await s.run(q, {
                "from_slug":  from_slug,
                "to_slug":    to_slug,
                "subtype":    props.get("subtype"),
                "label":      props.get("label", rel_type),
                "year_start": props.get("year_start"),
                "year_end":   props.get("year_end"),
                "is_current": props.get("is_current", True),
                "weight":     props.get("weight", 1.0),
                "source_url": props.get("source_url", ""),
                "evidence":   props.get("evidence", ""),
                "confidence": props.get("confidence", 0.7),
            })

    # ── News nodes ────────────────────────────────────────────────────────────

    async def upsert_news(self, article: Dict):
        q = """
        MERGE (n:News {url: $url})
        SET n.title       = $title,
            n.outlet      = $outlet,
            n.category    = $category,
            n.published_at= $published_at,
            n.sentiment   = $sentiment
        """
        async with self.driver.session() as s:
            await s.run(q, {
                "url":          article.get("url",""),
                "title":        article.get("title",""),
                "outlet":       article.get("outlet"),
                "category":     article.get("category","other"),
                "published_at": article.get("published_at"),
                "sentiment":    article.get("sentiment","neutral"),
            })

    async def link_person_news(self, person_slug: str, news_url: str,
                                alignment: float = 0.0, mention_type: str = "mentioned"):
        q = """
        MATCH (p:Person {slug: $slug})
        MATCH (n:News   {url:  $url})
        MERGE (p)-[r:MENTIONED_IN]->(n)
        SET r.alignment   = $alignment,
            r.mention_type= $mention_type
        """
        async with self.driver.session() as s:
            try:
                await s.run(q, {"slug": person_slug, "url": news_url,
                                "alignment": alignment, "mention_type": mention_type})
            except Exception:
                pass

    # ── Graph queries ─────────────────────────────────────────────────────────

    async def get_ego_graph(self, slug: str, depth: int = 2) -> Dict:
        """
        Return the ego-network of a person up to `depth` hops.
        depth=1 → direct connections only
        depth=2 → connections of connections
        """
        q = f"""
        MATCH path = (center:Person {{slug: $slug}})-[*1..{depth}]-(neighbor)
        WHERE NOT neighbor:News
        WITH center,
             collect(DISTINCT neighbor) AS neighbors,
             collect(DISTINCT relationships(path)) AS allRels
        RETURN center, neighbors,
               [r IN apoc.coll.flatten(allRels) | r] AS rels
        """
        # Fallback without APOC if needed
        q_simple = f"""
        MATCH (center:Person {{slug: $slug}})
        OPTIONAL MATCH (center)-[r]-(neighbor)
        WHERE NOT neighbor:News
        RETURN center, collect(DISTINCT neighbor) AS neighbors,
                       collect(DISTINCT r) AS rels
        """
        async with self.driver.session() as s:
            try:
                result = await s.run(q, {"slug": slug})
                record = await result.single()
            except Exception:
                result = await s.run(q_simple, {"slug": slug})
                record = await result.single()

            if not record:
                return {"nodes": [], "edges": []}

            c = dict(record["center"])
            nodes = [self._neo_node_to_dict(record["center"])]
            seen_ids = {c.get("slug", "")}
            edges = []

            for neighbor in record.get("neighbors", []):
                if neighbor is None:
                    continue
                nd = self._neo_node_to_dict(neighbor)
                nid = nd.get("id") or nd.get("slug") or nd.get("url","")
                if nid and nid not in seen_ids:
                    seen_ids.add(nid)
                    nodes.append(nd)

            for rel in record.get("rels", []):
                if rel is None:
                    continue
                try:
                    edges.append({
                        "source": rel.start_node.get("slug") or rel.start_node.get("url",""),
                        "target": rel.end_node.get("slug")   or rel.end_node.get("url",""),
                        "type":   type(rel).__name__ if hasattr(rel, '__class__') else str(rel.type),
                        "label":  rel.get("label", ""),
                        "subtype":rel.get("subtype",""),
                        "is_current": rel.get("is_current", True),
                    })
                except Exception:
                    pass

            return {"nodes": nodes, "edges": edges, "center": c.get("slug", slug)}

    async def get_full_graph(self, limit: int = 500) -> Dict:
        """Return entire graph (capped) for the overview view."""
        q = """
        MATCH (n) WHERE n:Person OR n:Org
        WITH n LIMIT $limit
        OPTIONAL MATCH (n)-[r]->(m)
        WHERE NOT m:News
        RETURN
          collect(DISTINCT {
            id:       coalesce(n.slug, n.url, toString(id(n))),
            label:    coalesce(n.name, n.title, 'Unknown'),
            type:     head(labels(n)),
            role_type:n.role_type,
            party:    n.party,
            province: n.province
          }) AS nodes,
          collect(DISTINCT CASE WHEN r IS NOT NULL THEN {
            source:   coalesce(startNode(r).slug, startNode(r).url),
            target:   coalesce(endNode(r).slug,   endNode(r).url),
            type:     type(r),
            label:    coalesce(r.label, type(r)),
            subtype:  r.subtype,
            is_current: r.is_current
          } ELSE null END) AS edges
        """
        async with self.driver.session() as s:
            result = await s.run(q, {"limit": limit})
            record = await result.single()
            if record:
                return {
                    "nodes": record["nodes"] or [],
                    "edges": [e for e in (record["edges"] or []) if e is not None],
                }
        return {"nodes": [], "edges": []}

    async def search_graph(self, query: str) -> List[Dict]:
        """Full-text search for persons in the graph."""
        q = """
        MATCH (n:Person)
        WHERE toLower(n.name) CONTAINS toLower($q)
        RETURN n LIMIT 15
        """
        async with self.driver.session() as s:
            result = await s.run(q, {"q": query})
            records = await result.data()
            return [self._neo_node_to_dict(r["n"]) for r in records]

    async def get_path_between(self, slug_a: str, slug_b: str) -> Dict:
        """Find shortest path between two people."""
        q = """
        MATCH path = shortestPath(
            (a:Person {slug: $a})-[*..5]-(b:Person {slug: $b})
        )
        RETURN path
        """
        async with self.driver.session() as s:
            try:
                result = await s.run(q, {"a": slug_a, "b": slug_b})
                record = await result.single()
                if not record:
                    return {"nodes": [], "edges": [], "found": False}
                path = record["path"]
                nodes, edges = [], []
                seen = set()
                for node in path.nodes:
                    nd = self._neo_node_to_dict(node)
                    nid = nd.get("id", nd.get("slug",""))
                    if nid not in seen:
                        seen.add(nid)
                        nodes.append(nd)
                for rel in path.relationships:
                    edges.append({
                        "source": rel.start_node.get("slug",""),
                        "target": rel.end_node.get("slug",""),
                        "type":   rel.type,
                        "label":  rel.get("label", rel.type),
                    })
                return {"nodes": nodes, "edges": edges, "found": True}
            except Exception as e:
                logger.warning(f"path_between failed: {e}")
                return {"nodes": [], "edges": [], "found": False}

    def _neo_node_to_dict(self, node) -> Dict:
        if node is None:
            return {}
        d = dict(node)
        labels = list(node.labels) if hasattr(node, "labels") else []
        label = labels[0] if labels else "Unknown"
        d["_label"] = label
        d["id"] = d.get("slug") or d.get("url") or str(node.id)
        return d

    # ── Dynasty / coalition graph queries ─────────────────────────────────────

    async def get_party_members_in_graph(self, party: str) -> List[Dict]:
        """Get all persons in the graph with a given party."""
        q = """
        MATCH (p:Person {party: $party})
        RETURN p LIMIT 200
        """
        async with self.driver.session() as s:
            result = await s.run(q, {"party": party})
            records = await result.data()
            return [dict(r["p"]) for r in records]

    async def get_family_cluster(self, slug: str, depth: int = 3) -> Dict:
        """Get all family-connected persons (for dynasty detection)."""
        q = f"""
        MATCH (center:Person {{slug: $slug}})
        OPTIONAL MATCH path = (center)-[:FAMILY_OF*1..{depth}]-(relative:Person)
        RETURN center,
               collect(DISTINCT {{
                 slug:     relative.slug,
                 name:     relative.name,
                 role_type:relative.role_type,
                 party:    relative.party,
                 province: relative.province,
                 position: relative.position
               }}) AS relatives
        """
        try:
            async with self.driver.session() as s:
                result = await s.run(q, {"slug": slug})
                rec    = await result.single()
                if not rec:
                    return {"nodes": [], "edges": []}
                center   = dict(rec["center"])
                nodes    = [{"id": center.get("slug",""), "_label": "Person",
                             "name": center.get("name",""), **center}]
                edges    = []
                for rel in rec["relatives"]:
                    if rel and rel.get("slug"):
                        nodes.append({"id": rel["slug"], "_label": "Person", **rel})
                        edges.append({
                            "source": center.get("slug",""),
                            "target": rel["slug"],
                            "type": "FAMILY_OF", "label": "keluarga",
                        })
                return {"nodes": nodes, "edges": edges}
        except Exception as e:
            logger.warning(f"family_cluster query: {e}")
            return {"nodes": [], "edges": []}

    async def get_coalition_subgraph(self, parties: List[str]) -> Dict:
        """Get the subgraph for a set of coalition parties and their members."""
        q = """
        MATCH (p:Person)-[:MEMBER_OF]->(o:Org)
        WHERE o.name IN $parties
        OPTIONAL MATCH (p)-[r]-(connected)
        WHERE connected:Person OR connected:Org
        RETURN collect(DISTINCT {
            id:       p.slug,
            name:     p.name,
            _label:   'Person',
            party:    p.party,
            role_type:p.role_type,
            province: p.province
        }) AS person_nodes,
        collect(DISTINCT {
            id:       o.slug,
            name:     o.name,
            _label:   'Org',
            org_type: o.org_type
        }) AS org_nodes,
        collect(DISTINCT CASE WHEN r IS NOT NULL THEN {
            source: startNode(r).slug,
            target: endNode(r).slug,
            type:   type(r),
            label:  r.label
        } ELSE null END) AS edges
        """
        try:
            async with self.driver.session() as s:
                result = await s.run(q, {"parties": parties})
                rec    = await result.single()
                if not rec:
                    return {"nodes": [], "edges": []}
                nodes = (rec["person_nodes"] or []) + (rec["org_nodes"] or [])
                edges = [e for e in (rec["edges"] or []) if e is not None]
                return {"nodes": nodes, "edges": edges}
        except Exception as e:
            logger.warning(f"coalition_subgraph query: {e}")
            return {"nodes": [], "edges": []}

    async def clear_all(self):
        """Delete all nodes and relationships from Neo4j for fresh restart."""
        q = "MATCH (n) DETACH DELETE n"
        async with self.driver.session() as s:
            await s.run(q)
        logger.info("Neo4j graph cleared for fresh restart")
    
    # ── Scheduler update methods ──────────────────────────────────────────────
    
    async def update_person_position(self, slug: str, new_position: str):
        """Update a person's position in Neo4j."""
        q = """
        MATCH (p:Person {slug: $slug})
        SET p.position = $position, p.updated_at = datetime()
        RETURN p.slug
        """
        async with self.driver.session() as s:
            await s.run(q, {"slug": slug, "position": new_position})
        logger.info(f"Neo4j updated position for {slug}")
    
    async def update_person_party(self, slug: str, new_party: str):
        """Update a person's party in Neo4j."""
        q = """
        MATCH (p:Person {slug: $slug})
        SET p.party = $party, p.updated_at = datetime()
        RETURN p.slug
        """
        async with self.driver.session() as s:
            await s.run(q, {"slug": slug, "party": new_party})
        logger.info(f"Neo4j updated party for {slug}")
    
    async def create_relationship(self, from_slug: str, to_slug: str, rel_type: str, properties: Dict = None):
        """Create a relationship between two persons/entities."""
        q = f"""
        MATCH (a:Person {{slug: $from_slug}})
        MATCH (b:Person {{slug: $to_slug}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $properties, r.created_at = datetime()
        RETURN type(r) AS rel
        """
        async with self.driver.session() as s:
            await s.run(q, {
                "from_slug": from_slug,
                "to_slug": to_slug,
                "properties": properties or {}
            })
        logger.info(f"Created {rel_type} relationship: {from_slug} -> {to_slug}")
    
    # ── Company nodes ──────────────────────────────────────────────────────────
    
    async def upsert_company(self, company: Dict):
        """Create or update a Company node."""
        q = """
        MERGE (c:Company {npwb: $npwb})
        SET c.name              = $name,
            c.establishment_date= $establishment_date,
            c.capital_authorized= $capital_authorized,
            c.capital_paid      = $capital_paid,
            c.status            = $status,
            c.province          = $province,
            c.city              = $city,
            c.business_activities= $business_activities,
            c.source_url        = $source_url,
            c.data_source       = $data_source,
            c.updated_at        = timestamp()
        """
        async with self.driver.session() as s:
            await s.run(q, {
                "npwb": company.get("npwb", ""),
                "name": company.get("name", ""),
                "establishment_date": company.get("establishment_date", ""),
                "capital_authorized": company.get("capital_authorized", 0),
                "capital_paid": company.get("capital_paid", 0),
                "status": company.get("status", "active"),
                "province": company.get("province", ""),
                "city": company.get("city", ""),
                "business_activities": company.get("business_activities", []),
                "source_url": company.get("source_url", ""),
                "data_source": company.get("data_source", "AHU")
            })
        logger.info(f"Upserted company: {company.get('name')} ({company.get('npwb')})")
    
    async def link_person_company(self, person_slug: str, company_npwb: str, 
                                   role_type: str, properties: Dict = None):
        """
        Link a person to a company with a specific role.
        role_type: SHAREHOLDER, COMMISSIONER, DIRECTOR, BENEFICIAL_OWNER
        """
        role_map = {
            'shareholder': 'OWNS_SHARES',
            'commissioner': 'COMMISSIONER_OF',
            'director': 'DIRECTOR_OF',
            'beneficial_owner': 'BENEFICIAL_OWNER_OF'
        }
        
        rel_type = role_map.get(role_type.lower(), 'AFFILIATED_WITH')
        
        q = f"""
        MATCH (p:Person {{slug: $person_slug}})
        MATCH (c:Company {{npwb: $company_npwb}})
        MERGE (p)-[r:{rel_type}]->(c)
        SET r += $properties,
            r.role_type     = $role_type,
            r.appointment_date = $appointment_date,
            r.shares_percent   = $shares_percent,
            r.shares_value     = $shares_value,
            r.is_current       = $is_current,
            r.updated_at       = timestamp()
        """
        
        props = properties or {}
        async with self.driver.session() as s:
            await s.run(q, {
                "person_slug": person_slug,
                "company_npwb": company_npwb,
                "role_type": role_type,
                "appointment_date": props.get("appointment_date"),
                "shares_percent": props.get("shares_percent"),
                "shares_value": props.get("shares_value"),
                "is_current": props.get("is_current", True)
            })
        
        logger.info(f"Linked {person_slug} as {role_type} to company {company_npwb}")
    
    async def get_person_companies(self, person_slug: str) -> List[Dict]:
        """Get all companies associated with a person."""
        q = """
        MATCH (p:Person {slug: $slug})-[r]-(c:Company)
        RETURN c, r
        """
        results = []
        async with self.driver.session() as s:
            cursor = await s.run(q, {"slug": person_slug})
            async for record in cursor:
                company = dict(record["c"])
                rel = dict(record["r"]) if record["r"] else {}
                results.append({
                    "company": company,
                    "relationship": rel
                })
        return results
    
    async def get_company_people(self, company_npwb: str) -> List[Dict]:
        """Get all people associated with a company."""
        q = """
        MATCH (p:Person)-[r]-(c:Company {npwb: $npwb})
        RETURN p, r
        """
        results = []
        async with self.driver.session() as s:
            cursor = await s.run(q, {"npwb": company_npwb})
            async for record in cursor:
                person = dict(record["p"])
                rel = dict(record["r"]) if record["r"] else {}
                results.append({
                    "person": person,
                    "relationship": rel
                })
        return results
    
    async def detect_business_conflicts(self, person_slug: str) -> List[Dict]:
        """
        Detect potential conflicts of interest based on business holdings.
        Returns list of flagged relationships.
        """
        conflicts = []
        
        q = """
        MATCH (p:Person {slug: $slug})-[r:OWNS_SHARES|COMMISSIONER_OF|DIRECTOR_OF|BENEFICIAL_OWNER_OF]->(c:Company)
        WHERE r.is_current = true
        RETURN p, r, c
        """
        
        # Position-sector conflict mapping
        conflict_sectors = {
            'Menteri ESDM': ['Pertambangan', 'Energi', 'Minyak dan Gas'],
            'Menteri Perhubungan': ['Transportasi', 'Logistik'],
            'Gubernur': ['Konstruksi', 'Pengembangan Properti'],
            'Anggota Komisi VI': ['Manufaktur', 'Industri']
        }
        
        async with self.driver.session() as s:
            cursor = await s.run(q, {"slug": person_slug})
            async for record in cursor:
                person = dict(record["p"])
                company = dict(record["c"])
                rel = dict(record["r"])
                
                position = person.get("position", "")
                activities = company.get("business_activities", [])
                
                # Check for conflicts
                for pos_pattern, sectors in conflict_sectors.items():
                    if pos_pattern.lower() in position.lower():
                        for activity in activities:
                            for sector in sectors:
                                if sector.lower() in activity.lower():
                                    conflicts.append({
                                        "person": person.get("name"),
                                        "position": position,
                                        "company": company.get("name"),
                                        "sector": sector,
                                        "activity": activity,
                                        "role": rel.get("role_type"),
                                        "severity": "high" if "Menteri" in position else "medium"
                                    })
        
        return conflicts
