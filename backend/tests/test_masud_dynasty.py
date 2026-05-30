"""
CROSSROAD — Mas'ud Dynasty Investigation Module
================================================
Specialized detector for the infamous Mas'ud political dynasty in East Kalimantan.

Target: Governor of East Kalimantan (Rudy Mas'ud / Rudy Resnawan)
Detection Goals:
  1. Map all family members in government positions
  2. Track all companies owned by family members
  3. Detect "Harum Resort" style monopolies (government contracts to family businesses)
  4. Identify self-dealing loops: Politician → Company → Government Contract
  5. Calculate oligarchy score based on wealth, power concentration, and conflicts

Example Pattern to Detect:
  - Governor owns PT Harum Resort
  - All government banquets MUST use Harum Resort
  = CONFLICT OF INTEREST + ABUSE OF POWER
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SelfDealingScheme:
    """Represents a detected self-dealing scheme."""
    politician_name: str
    politician_position: str
    company_name: str
    company_npwb: str
    relationship_type: str  # OWNER, COMMISSIONER, BENEFICIAL_OWNER
    government_contract_type: str  # BANQUET, CONSTRUCTION, SUPPLY, etc.
    contract_value: Optional[float] = None
    is_exclusive: bool = False  # Like "MUST use Harum Resort"
    confidence_score: float = 0.7
    evidence_urls: List[str] = field(default_factory=list)
    detection_date: str = ""


@dataclass
class OligarchyScore:
    """Comprehensive oligarchy score for a politician/family."""
    person_slug: str
    family_name: str
    
    # Component scores (0.0 - 1.0)
    wealth_concentration: float = 0.0
    political_power: float = 0.0
    business_density: float = 0.0
    conflict_severity: float = 0.0
    monopoly_control: float = 0.0
    
    # Final score
    total_score: float = 0.0
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Details
    total_companies: int = 0
    total_government_positions: int = 0
    detected_schemes: List[SelfDealingScheme] = field(default_factory=list)
    warning_flags: List[str] = field(default_factory=list)


class MasudDynastyDetector:
    """
    Specialized detector for the Mas'ud Dynasty and similar oligarchic networks.
    
    Detection Strategies:
    1. Family clustering with surname + geographic proximity
    2. Business ownership mapping via AHU/IDX/LHKPN
    3. Government contract tracking via LPSE/OpenSP2D
    4. Self-dealing loop detection (Politician → Company → Contract)
    5. Monopoly pattern recognition (exclusive mandates)
    """
    
    def __init__(self, graph_db, db):
        self.graph = graph_db
        self.db = db
        
        # Mas'ud-specific patterns
        self.target_surnames = ["Mas'ud", "Masud", "Resnawan", "Rudy"]
        self.target_regions = ["Kalimantan Timur", "Kaltim", "Balikpapan", "Samarinda"]
        
        # High-risk sectors for self-dealing
        self.high_risk_sectors = [
            "Hospitality", "Resort", "Hotel", "Restaurant",  # Banquet schemes
            "Construction", "Konstruksi", "Pengembangan Properti",
            "Mining", "Pertambangan", "Coal", "Batubara",
            "Transportation", "Logistik", "Shipping",
            "Energy", "Listrik", "Oil", "Gas",
            "Catering", "Event Organizer", "Venue"
        ]
        
        # Position-Sector conflict rules
        self.conflict_rules = {
            "Gubernur": ["Construction", "Mining", "Hospitality", "Transportation"],
            "Wakil Gubernur": ["Construction", "Mining", "Hospitality"],
            "Bupati": ["Construction", "Mining", "Agriculture"],
            "Walikota": ["Property", "Retail", "Hospitality"],
            "Kepala Dinas": ["Sector-specific contracts"],
        }
    
    async def scan_masud_dynasty(self) -> OligarchyScore:
        """
        Comprehensive scan of the Mas'ud dynasty network.
        Returns oligarchy score with detailed findings.
        """
        logger.info("🔍 Starting Mas'ud Dynasty investigation...")
        
        # Step 1: Find all Mas'ud family members
        family_members = await self._find_family_members()
        logger.info(f"Found {len(family_members)} family members")
        
        # Step 2: Get government positions
        govt_positions = await self._get_government_positions(family_members)
        logger.info(f"Found {len(govt_positions)} government positions")
        
        # Step 3: Map business ownership
        business_holdings = await self._map_business_holdings(family_members)
        logger.info(f"Found {len(business_holdings)} business holdings")
        
        # Step 4: Detect self-dealing schemes
        schemes = await self._detect_self_dealing(govt_positions, business_holdings)
        logger.info(f"Detected {len(schemes)} self-dealing schemes")
        
        # Step 5: Check for monopoly patterns (like Harum Resort)
        monopolies = await self._detect_monopoly_patterns(govt_positions, business_holdings)
        logger.info(f"Detected {len(monopolies)} monopoly patterns")
        
        schemes.extend(monopolies)
        
        # Step 6: Calculate oligarchy score
        score = self._calculate_oligarchy_score(
            family_members, govt_positions, business_holdings, schemes
        )
        score.detected_schemes = schemes
        
        return score
    
    async def _find_family_members(self) -> List[Dict]:
        """Find all Mas'ud family members in the database."""
        query = """
        MATCH (p:Person)
        WHERE 
          p.name =~ "(?i).*mas['\"]?ud.*" OR
          p.name =~ "(?i).*resnawan.*" OR
          p.province =~ "(?i).*kalimantan.*timur.*"
        RETURN p
        """
        
        members = []
        try:
            async with self.graph.driver.session() as session:
                result = await session.run(query)
                async for record in result:
                    person = dict(record["p"])
                    # Check surname match
                    name = person.get("name", "").lower()
                    if any(surname.lower() in name for surname in self.target_surnames):
                        members.append(person)
        except Exception as e:
            logger.error(f"Error finding family members: {e}")
        
        # Also check PostgreSQL
        try:
            pg_members = await self.db.list_persons(limit=5000)
            for p in pg_members:
                name = (p.get("full_name") or p.get("name") or "").lower()
                province = (p.get("province") or "").lower()
                
                if any(surname.lower() in name for surname in self.target_surnames):
                    if p not in members:
                        members.append(p)
                elif "kalimantan timur" in province or "kaltim" in province:
                    if any(surname.lower() in name for surname in ["rudy", "gubernur"]):
                        if p not in members:
                            members.append(p)
        except Exception as e:
            logger.error(f"Error checking PG: {e}")
        
        return members
    
    async def _get_government_positions(self, members: List[Dict]) -> List[Dict]:
        """Extract government positions from family members."""
        positions = []
        govt_keywords = ["gubernur", "bupati", "walikota", "dpr", "dprd", "menteri", "wakil"]
        
        for member in members:
            role = (member.get("role_type") or "").lower()
            position = (member.get("position") or member.get("current_position") or "").lower()
            
            if any(keyword in role or keyword in position for keyword in govt_keywords):
                positions.append({
                    "person": member,
                    "role": member.get("role_type"),
                    "position": member.get("current_position") or member.get("position"),
                    "province": member.get("province"),
                    "party": member.get("party"),
                })
        
        return positions
    
    async def _map_business_holdings(self, members: List[Dict]) -> List[Dict]:
        """Map all business holdings for family members."""
        holdings = []
        
        for member in members:
            slug = member.get("slug")
            if not slug:
                continue
            
            try:
                companies = await self.graph.get_person_companies(slug)
                for item in companies:
                    company = item.get("company", {})
                    relationship = item.get("relationship", {})
                    
                    holdings.append({
                        "person": member,
                        "person_slug": slug,
                        "company": company,
                        "company_name": company.get("name"),
                        "company_npwb": company.get("npwb"),
                        "role_type": relationship.get("role_type"),
                        "shares_percent": relationship.get("shares_percent"),
                        "is_current": relationship.get("is_current", True),
                        "business_activities": company.get("business_activities", []),
                    })
            except Exception as e:
                logger.warning(f"Error getting companies for {slug}: {e}")
        
        return holdings
    
    async def _detect_self_dealing(
        self, 
        govt_positions: List[Dict], 
        business_holdings: List[Dict]
    ) -> List[SelfDealingScheme]:
        """Detect self-dealing schemes where politicians profit from their positions."""
        schemes = []
        
        for pos in govt_positions:
            person = pos["person"]
            person_name = person.get("name") or person.get("full_name")
            position = pos["position"] or pos["role"]
            
            # Get allowed conflict sectors for this position
            allowed_sectors = self._get_conflict_sectors(position)
            
            for holding in business_holdings:
                if holding["person_slug"] != person.get("slug"):
                    continue
                
                company = holding["company"]
                company_name = company.get("name", "")
                activities = holding.get("business_activities", [])
                
                # Check if company operates in high-risk sector
                is_high_risk = any(
                    sector.lower() in str(act).lower() 
                    for act in activities 
                    for sector in self.high_risk_sectors
                )
                
                if is_high_risk and any(sector in str(activities) for sector in allowed_sectors):
                    scheme = SelfDealingScheme(
                        politician_name=person_name,
                        politician_position=position,
                        company_name=company_name,
                        company_npwb=company.get("npwb", ""),
                        relationship_type=holding.get("role_type", "OWNER"),
                        government_contract_type=self._infer_contract_type(activities),
                        is_exclusive=False,  # Will be updated by monopoly detection
                        confidence_score=0.8,
                        detection_date=datetime.now().isoformat(),
                    )
                    schemes.append(scheme)
        
        return schemes
    
    async def _detect_monopoly_patterns(
        self,
        govt_positions: List[Dict],
        business_holdings: List[Dict]
    ) -> List[SelfDealingScheme]:
        """
        Detect monopoly patterns like "All government banquets MUST use Harum Resort".
        
        This queries news articles, procurement data, and regulatory documents
        for exclusive mandates.
        """
        monopolies = []
        
        # Keywords that indicate exclusive mandates
        exclusive_keywords = [
            "wajib menggunakan", "harus menggunakan", "diwajibkan",
            "eksklusif", "monopoli", "tunggal", "only", "must use",
            "ditunjuk langsung", "penunjukan langsung"
        ]
        
        for pos in govt_positions:
            person = pos["person"]
            position = pos["position"] or pos["role"]
            
            # Only check high-level officials who can issue mandates
            if not any(keyword in (position or "").lower() 
                      for keyword in ["gubernur", "bupati", "walikota", "kepala dinas"]):
                continue
            
            for holding in business_holdings:
                if holding["person_slug"] != person.get("slug"):
                    continue
                
                company = holding["company"]
                company_name = company.get("name", "")
                activities = holding.get("business_activities", [])
                
                # Check for hospitality/venue companies (like Harum Resort)
                is_hospitality = any(
                    keyword in str(act).lower()
                    for act in activities
                    for keyword in ["resort", "hotel", "venue", "banquet", "catering", "event"]
                )
                
                if is_hospitality:
                    # Search for exclusive mandate evidence
                    evidence = await self._search_exclusive_mandates(
                        person.get("name"),
                        company_name,
                        position
                    )
                    
                    if evidence:
                        scheme = SelfDealingScheme(
                            politician_name=person.get("name"),
                            politician_position=position,
                            company_name=company_name,
                            company_npwb=company.get("npwb", ""),
                            relationship_type=holding.get("role_type", "OWNER"),
                            government_contract_type="EXCLUSIVE_MANDATE",
                            is_exclusive=True,
                            confidence_score=0.95,
                            evidence_urls=evidence,
                            detection_date=datetime.now().isoformat(),
                        )
                        monopolies.append(scheme)
        
        return monopolies
    
    async def _search_exclusive_mandates(
        self, 
        politician_name: str, 
        company_name: str,
        position: str
    ) -> List[str]:
        """Search for evidence of exclusive mandates in news/documents."""
        evidence_urls = []
        
        # Query news articles for exclusive mandate patterns
        query = """
        MATCH (n:News)
        WHERE 
          n.content =~ "(?i).*" + $politician + ".*" + $company + ".*" AND
          (n.content =~ "(?i).*wajib.*" OR n.content =~ "(?i).*eksklusif.*" OR n.content =~ "(?i).*monopoli.*")
        RETURN n.url, n.title
        LIMIT 10
        """
        
        try:
            async with self.graph.driver.session() as session:
                result = await session.run(
                    query,
                    {"politician": politician_name or "", "company": company_name or ""}
                )
                async for record in result:
                    evidence_urls.append(record["n.url"])
        except Exception as e:
            logger.warning(f"Error searching mandates: {e}")
        
        # Also check for procurement patterns (would need LPSE integration)
        # TODO: Add LPSE query for single-bidder contracts
        
        return evidence_urls
    
    def _get_conflict_sectors(self, position: str) -> List[str]:
        """Get sectors that conflict with a given position."""
        position_lower = (position or "").lower()
        
        for pos_keyword, sectors in self.conflict_rules.items():
            if pos_keyword.lower() in position_lower:
                return sectors
        
        return []
    
    def _infer_contract_type(self, activities: List[str]) -> str:
        """Infer government contract type from business activities."""
        activities_str = " ".join(str(a) for a in activities).lower()
        
        if any(k in activities_str for k in ["resort", "hotel", "banquet", "catering"]):
            return "HOSPITALITY_EVENT"
        elif any(k in activities_str for k in ["construction", "konstruksi", "bangun"]):
            return "CONSTRUCTION"
        elif any(k in activities_str for k in ["mining", "tambang", "coal"]):
            return "MINING_CONCESSION"
        elif any(k in activities_str for k in ["transport", "logistik"]):
            return "TRANSPORTATION_SERVICE"
        else:
            return "GENERAL_PROCUREMENT"
    
    def _calculate_oligarchy_score(
        self,
        family_members: List[Dict],
        govt_positions: List[Dict],
        business_holdings: List[Dict],
        schemes: List[SelfDealingScheme]
    ) -> OligarchyScore:
        """Calculate comprehensive oligarchy score."""
        
        if not family_members:
            return OligarchyScore(
                person_slug="",
                family_name="Unknown",
                risk_level="LOW"
            )
        
        # Determine family name
        family_name = "Mas'ud"  # Default for this detector
        
        # Count unique people
        unique_people = len(set(m.get("slug") or m.get("name") for m in family_members))
        
        # Component calculations (0.0 - 1.0 scale)
        
        # 1. Wealth Concentration: Based on number of companies and capital
        company_count = len(business_holdings)
        wealth_score = min(company_count / 20.0, 1.0)  # Max at 20 companies
        
        # 2. Political Power: Based on positions held
        position_count = len(govt_positions)
        has_governor = any("gubernur" in (p.get("position") or "").lower() for p in govt_positions)
        power_score = min(position_count / 10.0, 1.0)
        if has_governor:
            power_score = min(power_score + 0.3, 1.0)  # Governor bonus
        
        # 3. Business Density: Companies per family member
        if unique_people > 0:
            density = company_count / unique_people
            density_score = min(density / 5.0, 1.0)  # Max at 5 companies/person
        else:
            density_score = 0.0
        
        # 4. Conflict Severity: Based on detected schemes
        scheme_count = len(schemes)
        exclusive_count = sum(1 for s in schemes if s.is_exclusive)
        conflict_score = min(scheme_count / 5.0, 1.0)
        if exclusive_count > 0:
            conflict_score = min(conflict_score + 0.4, 1.0)  # Exclusive mandate penalty
        
        # 5. Monopoly Control: Exclusive mandates are critical
        monopoly_score = min(exclusive_count / 3.0, 1.0)  # Max at 3 monopolies
        
        # Weighted total
        total = (
            wealth_score * 0.20 +
            power_score * 0.25 +
            density_score * 0.15 +
            conflict_score * 0.25 +
            monopoly_score * 0.15
        )
        
        # Determine risk level
        if total >= 0.8 or exclusive_count > 0:
            risk_level = "CRITICAL"
        elif total >= 0.6:
            risk_level = "HIGH"
        elif total >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Generate warning flags
        warnings = []
        if has_governor and company_count > 5:
            warnings.append("Governor owns multiple companies")
        if exclusive_count > 0:
            warnings.append(f"DETECTED EXCLUSIVE MANDATES ({exclusive_count})")
        if scheme_count > 3:
            warnings.append(f"Multiple self-dealing schemes ({scheme_count})")
        if any(s.politician_position and "gubernur" in s.politician_position.lower() 
               for s in schemes):
            warnings.append("Governor directly profiting from business interests")
        
        return OligarchyScore(
            person_slug=family_members[0].get("slug", ""),
            family_name=family_name,
            wealth_concentration=round(wealth_score, 2),
            political_power=round(power_score, 2),
            business_density=round(density_score, 2),
            conflict_severity=round(conflict_score, 2),
            monopoly_control=round(monopoly_score, 2),
            total_score=round(total, 2),
            risk_level=risk_level,
            total_companies=company_count,
            total_government_positions=position_count,
            warning_flags=warnings,
        )
    
    async def _calculate_oligarchy_score_for_person(self, person_slug: str) -> Dict:
        """
        Calculate oligarchy score for a single person.
        Helper method for batch scanning.
        """
        # Get person info
        person = await self.db.get_person(person_slug)
        if not person:
            return {"total_score": 0.0, "risk_level": "LOW", "company_count": 0, "conflict_count": 0}
        
        # Get business holdings
        try:
            companies = await self.graph.get_person_companies(person_slug)
            company_count = len(companies)
        except Exception:
            companies = []
            company_count = 0
        
        # Get conflicts
        try:
            conflicts = await self.graph.detect_business_conflicts(person_slug)
            conflict_count = len(conflicts)
        except Exception:
            conflicts = []
            conflict_count = 0
        
        # Check if governor
        position = person.get("position") or ""
        is_governor = "gubernur" in position.lower()
        
        # Simple scoring
        wealth_score = min(company_count / 20.0, 1.0)
        power_score = 0.3 if person.get("role_type") else 0.0
        if is_governor:
            power_score = min(power_score + 0.3, 1.0)
        conflict_score = min(conflict_count / 5.0, 1.0)
        
        total = wealth_score * 0.3 + power_score * 0.4 + conflict_score * 0.3
        
        if total >= 0.7:
            risk_level = "CRITICAL"
        elif total >= 0.5:
            risk_level = "HIGH"
        elif total >= 0.3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "total_score": round(total, 2),
            "risk_level": risk_level,
            "company_count": company_count,
            "conflict_count": conflict_count,
        }


async def main():
    """Test the Mas'ud Dynasty detector."""
    from backend.graph import GraphDB
    from backend.db import Database
    
    graph = GraphDB()
    db = Database()
    
    await db.init()
    await graph.init_schema()
    
    detector = MasudDynastyDetector(graph, db)
    
    print("\n" + "="*80)
    print("🔍 MAS'UD DYNASTY INVESTIGATION")
    print("="*80 + "\n")
    
    score = await detector.scan_masud_dynasty()
    
    print(f"\n📊 OLIGARCHY SCORE REPORT")
    print(f"{'='*60}")
    print(f"Family Name:        {score.family_name}")
    print(f"Risk Level:         ⚠️  {score.risk_level}")
    print(f"Total Score:        {score.total_score}/1.0")
    print(f"\nComponent Scores:")
    print(f"  • Wealth Concentration:  {score.wealth_concentration}")
    print(f"  • Political Power:       {score.political_power}")
    print(f"  • Business Density:      {score.business_density}")
    print(f"  • Conflict Severity:     {score.conflict_severity}")
    print(f"  • Monopoly Control:      {score.monopoly_control}")
    print(f"\nStatistics:")
    print(f"  • Family Members:        Detected")
    print(f"  • Government Positions:  {score.total_government_positions}")
    print(f"  • Companies Owned:       {score.total_companies}")
    print(f"  • Self-Dealing Schemes:  {len(score.detected_schemes)}")
    
    if score.warning_flags:
        print(f"\n⚠️  WARNING FLAGS:")
        for flag in score.warning_flags:
            print(f"   ❗ {flag}")
    
    if score.detected_schemes:
        print(f"\n🔴 DETECTED SELF-DEALING SCHEMES:")
        for i, scheme in enumerate(score.detected_schemes, 1):
            print(f"\n   Scheme #{i}:")
            print(f"     Politician: {scheme.politician_name} ({scheme.politician_position})")
            print(f"     Company:    {scheme.company_name}")
            print(f"     Type:       {scheme.government_contract_type}")
            print(f"     Exclusive:  {'YES ⚠️' if scheme.is_exclusive else 'No'}")
            print(f"     Confidence: {scheme.confidence_score:.0%}")
    
    print("\n" + "="*80 + "\n")
    
    await db.close()
    await graph.close()


if __name__ == "__main__":
    asyncio.run(main())
