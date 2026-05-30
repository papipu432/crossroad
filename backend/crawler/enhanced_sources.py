"""
CROSSROAD — Enhanced Indonesian Data Sources
=============================================
Specialized crawlers for government databases, asset declarations,
corruption cases, and business registries.

Sources:
  - KPU (Komisi Pemilihan Umum): Election candidates, vote counts, party structures
  - LHKPN (Laporan Harta Kekayaan Penyelenggara Negara): Asset declarations
  - KPK (Komisi Pemberantasan Korupsi): Corruption cases, investigations
  - AHU Online: Business ownership registry
  - OSS: Investment and business licensing
"""

import asyncio
import logging
import re
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from slugify import slugify

logger = logging.getLogger(__name__)


@dataclass
class AssetDeclaration:
    """LHKPN asset declaration record."""
    name: str
    position: str
    agency: str
    report_date: str
    total_assets: float
    cash: float
    receivables: float
    investments: Dict[str, float]
    real_estate: List[Dict]
    vehicles: List[Dict]
    liabilities: float
    source_url: str


@dataclass
class KPKCase:
    """KPK corruption case record."""
    case_number: str
    title: str
    status: str  # investigation, prosecution, trial, verdict
    suspects: List[str]
    related_officials: List[str]
    loss_amount: float
    category: str  # bribery, embezzlement, gratification, etc.
    timeline: List[Dict]
    source_url: str


@dataclass
class BusinessOwnership:
    """Business ownership from AHU/OSS."""
    company_name: str
    npwb: str
    establishment_date: str
    capital: float
    shareholders: List[Dict]
    directors: List[Dict]
    commissioners: List[Dict]
    business_activities: List[str]
    address: str
    province: str


class KPUCrawler:
    """
    Crawl KPU (General Elections Commission) data.
    Provides candidate lists, election results, party structures.
    
    Note: Uses official KPU API where available.
    """
    
    BASE_URL = "https://data.kpu.go.id"
    API_BASE = "https://api.kpu.go.id"
    
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def get_candidates_2024(self, level: str = "nasional") -> List[Dict]:
        """
        Get 2024 election candidates.
        level: nasional | provinsi | kabupaten
        """
        candidates = []
        
        try:
            # Presidential candidates
            if level == "nasional":
                pres_url = f"{self.BASE_URL}/pilpres/2024/paslon"
                resp = await self.client.get(pres_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    # Parse paslon cards
                    for card in soup.select('.paslon-card'):
                        name_el = card.select_one('.nama-paslon')
                        number_el = card.select_one('.nomor-urut')
                        if name_el and number_el:
                            candidates.append({
                                'type': 'presiden',
                                'number': int(number_el.text.strip()),
                                'name': name_el.text.strip(),
                                'parties': self._extract_supporting_parties(card),
                                'source_url': pres_url
                            })
            
            # DPR candidates by province
            elif level in ("provinsi", "nasional"):
                dpr_url = f"{self.BASE_URL}/pileg/2024/dpr"
                resp = await self.client.get(dpr_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    for row in soup.select('table.data-table tr'):
                        cols = row.select('td')
                        if len(cols) >= 5:
                            candidates.append({
                                'type': 'dpr',
                                'number': cols[0].text.strip(),
                                'name': cols[1].text.strip(),
                                'party': cols[2].text.strip(),
                                'province': cols[3].text.strip(),
                                'dapil': cols[4].text.strip(),
                                'source_url': dpr_url
                            })
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.error(f"KPU candidates error: {e}")
        
        return candidates
    
    def _extract_supporting_parties(self, card) -> List[str]:
        """Extract parties supporting a presidential ticket."""
        parties = []
        for party_el in card.select('.partai-pendukung'):
            parties.append(party_el.text.strip())
        return parties
    
    async def get_election_results(self, region: str = "nasional") -> Dict:
        """Get official election results by region."""
        results = {
            'region': region,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'presidential': {},
            'legislative': []
        }
        
        try:
            # Presidential results
            pres_url = f"{self.BASE_URL}/pilpres/2024/hasil"
            resp = await self.client.get(pres_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for row in soup.select('.hasil-row'):
                    paslon_num = row.select_one('.nomor')
                    votes = row.select_one('.suara')
                    percent = row.select_one('.persen')
                    if paslon_num and votes:
                        results['presidential'][int(paslon_num.text)] = {
                            'votes': int(votes.text.replace('.', '')),
                            'percent': float(percent.text.replace('%', '')) if percent else 0
                        }
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.error(f"KPU results error: {e}")
        
        return results
    
    async def get_party_structure(self, party_name: str) -> Dict:
        """Get party organizational structure from KPU records."""
        structure = {
            'party': party_name,
            'leadership': [],
            'regions': []
        }
        
        try:
            url = f"{self.BASE_URL}/parpol/{slugify(party_name)}"
            resp = await self.client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Extract leadership
                for leader in soup.select('.pengurus-item'):
                    name = leader.select_one('.nama')
                    position = leader.select_one('.jabatan')
                    if name and position:
                        structure['leadership'].append({
                            'name': name.text.strip(),
                            'position': position.text.strip()
                        })
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.error(f"Party structure error: {e}")
        
        return structure


class LHKPNCrawler:
    """
    Crawl LHKPN (Asset Declarations) for wealth tracking.
    Critical for detecting conflicts of interest and illicit enrichment.
    
    Source: https://elhkpn.kpk.go.id
    """
    
    BASE_URL = "https://elhkpn.kpk.go.id"
    
    def __init__(self, delay: float = 3.0):
        self.delay = delay
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def search_by_name(self, name: str) -> List[AssetDeclaration]:
        """Search asset declarations by name."""
        declarations = []
        
        try:
            search_url = f"{self.BASE_URL}/laporan/search"
            params = {'q': name, 'limit': 20}
            resp = await self.client.get(search_url, params=params)
            
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get('results', []):
                    decl = await self._parse_declaration(item)
                    if decl:
                        declarations.append(decl)
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.warning(f"LHKPN search error for {name}: {e}")
        
        return declarations
    
    async def _parse_declaration(self, item: Dict) -> Optional[AssetDeclaration]:
        """Parse a single declaration record."""
        try:
            # Fetch full details
            detail_url = f"{self.BASE_URL}/laporan/{item.get('id', '')}"
            resp = await self.client.get(detail_url)
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            
            return AssetDeclaration(
                name=data.get('nama', ''),
                position=data.get('jabatan', ''),
                agency=data.get('instansi', ''),
                report_date=data.get('tanggal_lapor', ''),
                total_assets=self._parse_value(data.get('total_harta', '0')),
                cash=self._parse_value(data.get('kas', '0')),
                receivables=self._parse_value(data.get('piutang', '0')),
                investments=data.get('investasi', {}),
                real_estate=data.get('properti', []),
                vehicles=data.get('kendaraan', []),
                liabilities=self._parse_value(data.get('hutang', '0')),
                source_url=detail_url
            )
            
        except Exception as e:
            logger.warning(f"Parse declaration error: {e}")
            return None
    
    def _parse_value(self, value_str: str) -> float:
        """Parse Indonesian currency format to float."""
        if not value_str:
            return 0.0
        try:
            # Remove "Rp" and dots, replace comma with dot
            cleaned = value_str.replace('Rp', '').replace('.', '').replace(',', '.')
            return float(cleaned)
        except:
            return 0.0
    
    async def detect_wealth_changes(self, person_slug: str, person_name: str) -> Dict:
        """
        Compare multiple years of declarations to detect unusual wealth growth.
        Returns alert if growth exceeds normal income.
        """
        alerts = {
            'person': person_name,
            'slug': person_slug,
            'declarations': [],
            'growth_rate': 0.0,
            'alert_level': 'normal'  # normal | suspicious | critical
        }
        
        declarations = await self.search_by_name(person_name)
        if not declarations:
            return alerts
        
        # Sort by date
        declarations.sort(key=lambda d: d.report_date)
        alerts['declarations'] = [
            {'date': d.report_date, 'total': d.total_assets}
            for d in declarations
        ]
        
        if len(declarations) >= 2:
            first = declarations[0].total_assets
            last = declarations[-1].total_assets
            
            if first > 0:
                growth = ((last - first) / first) * 100
                alerts['growth_rate'] = growth
                
                # Flag suspicious growth (>100% without position change)
                if growth > 100:
                    alerts['alert_level'] = 'suspicious'
                if growth > 300:
                    alerts['alert_level'] = 'critical'
        
        return alerts


class KPKCrawler:
    """
    Crawl KPK (Corruption Eradication Commission) data.
    Tracks corruption cases involving politicians.
    
    Source: https://www.kpk.go.id
    """
    
    BASE_URL = "https://www.kpk.go.id"
    
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def search_cases(self, keyword: str) -> List[KPKCase]:
        """Search corruption cases by keyword (person name, institution)."""
        cases = []
        
        try:
            search_url = f"{self.BASE_URL}/berita/search"
            params = {'q': keyword, 'kategori': 'penindakan'}
            resp = await self.client.get(search_url, params=params)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for article in soup.select('.article-item'):
                    case = await self._parse_case_article(article)
                    if case:
                        cases.append(case)
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.warning(f"KPK case search error: {e}")
        
        return cases
    
    async def _parse_case_article(self, article) -> Optional[KPKCase]:
        """Parse a KPK news article into structured case data."""
        try:
            title_el = article.select_one('.title')
            date_el = article.select_one('.date')
            excerpt = article.select_one('.excerpt')
            
            if not title_el:
                return None
            
            title = title_el.text.strip()
            
            # Extract case number from title or content
            case_match = re.search(r'No\.?\s*(\d+/\w+/\d+)', title)
            case_number = case_match.group(1) if case_match else ""
            
            # Determine status from keywords
            status = 'investigation'
            if 'vonis' in title.lower():
                status = 'verdict'
            elif 'sidang' in title.lower():
                status = 'trial'
            elif 'tersangka' in title.lower():
                status = 'prosecution'
            
            # Estimate loss amount
            loss_amount = 0.0
            loss_match = re.search(r'Rp\s*([\d.,]+)\s*(?:miliar|triliun)', excerpt.text if excerpt else '', re.IGNORECASE)
            if loss_match:
                amount_str = loss_match.group(1).replace('.', '').replace(',', '.')
                loss_amount = float(amount_str)
                if 'triliun' in (excerpt.text if excerpt else '').lower():
                    loss_amount *= 1000
                elif 'miliar' in (excerpt.text if excerpt else '').lower():
                    pass  # already in billions
            
            return KPKCase(
                case_number=case_number,
                title=title,
                status=status,
                suspects=[],  # Would need full article parse
                related_officials=[],
                loss_amount=loss_amount,
                category=self._categorize_case(title),
                timeline=[],
                source_url=f"{self.BASE_URL}{article.select_one('a')['href']}" if article.select_one('a') else ""
            )
            
        except Exception as e:
            logger.warning(f"Parse KPK case error: {e}")
            return None
    
    def _categorize_case(self, title: str) -> str:
        """Categorize case type from title."""
        title_lower = title.lower()
        if 'suap' in title_lower or 'bribery' in title_lower:
            return 'bribery'
        elif 'korupsi' in title_lower or 'embezzlement' in title_lower:
            return 'embezzlement'
        elif 'gratifikasi' in title_lower:
            return 'gratification'
        elif 'pencucian uang' in title_lower or 'money laundering' in title_lower:
            return 'money_laundering'
        else:
            return 'other'
    
    async def get_person_cases(self, person_name: str) -> List[KPKCase]:
        """Get all KPK cases involving a specific person."""
        all_cases = await self.search_cases(person_name)
        
        # Filter cases actually mentioning this person
        relevant = []
        for case in all_cases:
            # In production, would fetch full article and check mentions
            if person_name.lower() in case.title.lower():
                relevant.append(case)
        
        return relevant


class AHUCrawler:
    """
    Crawl AHU Online (Administrative Law Entity) for business ownership.
    Links politicians to companies they own/control.
    
    Source: https://ahu.go.id
    """
    
    BASE_URL = "https://ahu.go.id"
    
    def __init__(self, delay: float = 3.0):
        self.delay = delay
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def search_company(self, company_name: str) -> Optional[BusinessOwnership]:
        """Search company by name."""
        try:
            search_url = f"{self.BASE_URL}/search"
            params = {'q': company_name}
            resp = await self.client.get(search_url, params=params)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                first_result = soup.select_one('.company-result')
                if first_result:
                    return await self._parse_company(first_result)
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.warning(f"AHU search error: {e}")
        
        return None
    
    async def _parse_company(self, element) -> Optional[BusinessOwnership]:
        """Parse company details."""
        try:
            name = element.select_one('.company-name').text.strip()
            npwb = element.select_one('.npwb').text.strip()
            
            # Extract shareholders, directors from detailed view
            # This would require clicking through to detail page
            
            return BusinessOwnership(
                company_name=name,
                npwb=npwb,
                establishment_date="",
                capital=0.0,
                shareholders=[],
                directors=[],
                commissioners=[],
                business_activities=[],
                address="",
                province=""
            )
            
        except Exception as e:
            logger.warning(f"Parse company error: {e}")
            return None
    
    async def find_politician_companies(self, politician_name: str) -> List[BusinessOwnership]:
        """Find companies associated with a politician."""
        companies = []
        
        # Search by name as shareholder/director
        # This is a simplified version - real implementation would use advanced search
        
        variations = [
            politician_name,
            politician_name.split()[-1],  # Last name only
            f"PT {politician_name}",
        ]
        
        for query in variations:
            result = await self.search_company(query)
            if result:
                companies.append(result)
        
        return companies


class IntegratedDataSource:
    """
    Unified interface for all enhanced data sources.
    Orchestrates crawlers and merges results.
    """
    
    def __init__(self):
        self.kpu = KPUCrawler()
        self.lhkpn = LHKPNCrawler()
        self.kpk = KPKCrawler()
        self.ahu = AHUCrawler()
    
    async def close_all(self):
        await self.kpu.close()
        await self.lhkpn.close()
        await self.kpk.close()
        await self.ahu.close()
    
    async def enrich_person(self, person_slug: str, person_name: str, position: str) -> Dict:
        """
        Enrich a person's profile with data from all sources.
        Returns comprehensive intelligence dossier.
        """
        dossier = {
            'person': person_name,
            'slug': person_slug,
            'position': position,
            'election_data': None,
            'asset_declarations': [],
            'wealth_alert': None,
            'kpk_cases': [],
            'business_interests': [],
            'risk_score': 0.0,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Parallel fetch from all sources
        tasks = [
            self.lhkpn.search_by_name(person_name),
            self.kpk.get_person_cases(person_name),
            self.ahu.find_politician_companies(person_name),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process LHKPN
        if isinstance(results[0], list):
            dossier['asset_declarations'] = [
                {
                    'date': d.report_date,
                    'total_assets': d.total_assets,
                    'liabilities': d.liabilities,
                    'net_worth': d.total_assets - d.liabilities,
                    'source_url': d.source_url
                }
                for d in results[0]
            ]
            
            # Check wealth changes
            wealth_alert = await self.lhkpn.detect_wealth_changes(person_slug, person_name)
            dossier['wealth_alert'] = wealth_alert
            
            # Adjust risk score
            if wealth_alert['alert_level'] == 'suspicious':
                dossier['risk_score'] += 0.3
            elif wealth_alert['alert_level'] == 'critical':
                dossier['risk_score'] += 0.6
        
        # Process KPK
        if isinstance(results[1], list):
            dossier['kpk_cases'] = [
                {
                    'case_number': c.case_number,
                    'title': c.title,
                    'status': c.status,
                    'category': c.category,
                    'loss_amount': c.loss_amount,
                    'source_url': c.source_url
                }
                for c in results[1]
            ]
            
            # KPK cases significantly increase risk
            dossier['risk_score'] += min(len(results[1]) * 0.4, 1.0)
        
        # Process Business
        if isinstance(results[2], list):
            dossier['business_interests'] = [
                {
                    'company': c.company_name,
                    'npwb': c.npwb,
                    'role': 'shareholder',  # Would need deeper parsing
                    'province': c.province
                }
                for c in results[2]
            ]
            
            # Business interests add moderate risk
            if len(results[2]) > 3:
                dossier['risk_score'] += 0.2
        
        # Cap risk score at 1.0
        dossier['risk_score'] = min(dossier['risk_score'], 1.0)
        
        return dossier


# Convenience functions
async def crawl_kpu_candidates(level: str = "nasional") -> List[Dict]:
    """Quick helper to get KPU candidates."""
    crawler = KPUCrawler()
    try:
        return await crawler.get_candidates_2024(level)
    finally:
        await crawler.close()


async def crawl_lhkpn_assets(name: str) -> List[AssetDeclaration]:
    """Quick helper to search LHKPN."""
    crawler = LHKPNCrawler()
    try:
        return await crawler.search_by_name(name)
    finally:
        await crawler.close()


async def crawl_kpk_cases(keyword: str) -> List[KPKCase]:
    """Quick helper to search KPK cases."""
    crawler = KPKCrawler()
    try:
        return await crawler.search_cases(keyword)
    finally:
        crawler.close()
