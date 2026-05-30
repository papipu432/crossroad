"""
CROSSROAD — Enhanced Business Registry Crawler
==============================================
Comprehensive scraping of Indonesian business registries to track:
- Company ownership structures
- Commissioner and Director positions
- Shareholder networks linking politicians to businesses
- Ultimate beneficial ownership (UBO) detection

Sources:
  - AHU Online (Direktorat Jenderal Administrasi Hukum Umum)
  - OSS (Online Single Submission)
  - IDX (Indonesia Stock Exchange) for public companies
  - PPATK (Financial Intelligence Unit) for beneficial ownership
"""

import asyncio
import logging
import re
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

import httpx
from bs4 import BeautifulSoup
from slugify import slugify

logger = logging.getLogger(__name__)


class RoleType(str, Enum):
    """Business role types."""
    SHAREHOLDER = "shareholder"
    COMMISSIONER = "commissioner"
    DIRECTOR = "director"
    BENEFICIAL_OWNER = "beneficial_owner"
    FOUNDER = "founder"


@dataclass
class PersonRole:
    """Person's role in a company."""
    name: str
    role: RoleType
    shares_percent: Optional[float] = None
    shares_value: Optional[float] = None
    appointment_date: Optional[str] = None
    id_number: Optional[str] = None  # KTP/NPWP (masked)
    address: Optional[str] = None


@dataclass
class Company:
    """Detailed company information."""
    name: str
    npwb: str  # Nomor Pokok Wajib Pajak Badan
    establishment_date: str
    establishment_deed: str
    capital_authorized: float
    capital_paid: float
    currency: str = "IDR"
    
    # Key people
    shareholders: List[PersonRole] = field(default_factory=list)
    directors: List[PersonRole] = field(default_factory=list)
    commissioners: List[PersonRole] = field(default_factory=list)
    beneficial_owners: List[PersonRole] = field(default_factory=list)
    
    # Business details
    business_activities: List[str] = field(default_factory=list)
    kblis_codes: List[str] = field(default_factory=list)
    address: str = ""
    province: str = ""
    city: str = ""
    postal_code: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    
    # Status
    status: str = "active"  # active, inactive, dissolved
    last_updated: str = ""
    
    # Source tracking
    source_url: str = ""
    data_source: str = "AHU"


@dataclass
class OwnershipChain:
    """Track ownership chains for UBO detection."""
    company_name: str
    owner_name: str
    ownership_percent: float
    intermediate_companies: List[str] = field(default_factory=list)
    is_direct: bool = True
    confidence: float = 0.7


class AHUEnhancedCrawler:
    """
    Enhanced AHU Online crawler with deep company structure extraction.
    
    Note: Real implementation would need to handle:
    - Login/authentication for detailed views
    - CAPTCHA solving or API access
    - Rate limiting compliance
    """
    
    BASE_URL = "https://ahu.go.id"
    SEARCH_URL = "https://ahu.go.id/search"
    
    def __init__(self, delay: float = 3.0, use_api: bool = False):
        self.delay = delay
        self.use_api = use_api
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    async def close(self):
        await self.client.aclose()
    
    async def search_company_by_name(self, company_name: str, exact: bool = False) -> List[Company]:
        """Search companies by name with fuzzy matching."""
        companies = []
        
        try:
            params = {
                'q': company_name,
                'type': 'company',
                'limit': 20
            }
            
            if exact:
                params['exact'] = 'true'
            
            resp = await self.client.get(self.SEARCH_URL, params=params)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                for result in soup.select('.company-result-item'):
                    company = await self._parse_search_result(result)
                    if company:
                        companies.append(company)
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.warning(f"AHU search error for '{company_name}': {e}")
        
        return companies
    
    async def _parse_search_result(self, element) -> Optional[Company]:
        """Parse a search result into basic company info."""
        try:
            name_el = element.select_one('.company-name')
            npwb_el = element.select_one('.npwb-number')
            
            if not name_el:
                return None
            
            company = Company(
                name=name_el.text.strip(),
                npwb=npwb_el.text.strip() if npwb_el else "",
                establishment_date="",
                establishment_deed="",
                capital_authorized=0.0,
                capital_paid=0.0,
                source_url=f"{self.BASE_URL}{element.select_one('a')['href']}" if element.select_one('a') else ""
            )
            
            # Fetch full details
            if company.source_url:
                await asyncio.sleep(self.delay)
                full_company = await self.fetch_company_details(company.source_url)
                if full_company:
                    return full_company
            
            return company
            
        except Exception as e:
            logger.warning(f"Parse search result error: {e}")
            return None
    
    async def fetch_company_details(self, url: str) -> Optional[Company]:
        """Fetch complete company details from detail page."""
        try:
            resp = await self.client.get(url)
            if resp.status_code != 200:
                return None
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract basic info
            name = self._extract_text(soup, '.company-header .name')
            npwb = self._extract_text(soup, '.company-header .npwb')
            
            # Parse establishment
            est_date = self._extract_text(soup, '.establishment-date')
            est_deed = self._extract_text(soup, '.establishment-deed')
            
            # Parse capital
            capital_auth = self._parse_currency(self._extract_text(soup, '.capital-authorized'))
            capital_paid = self._parse_currency(self._extract_text(soup, '.capital-paid'))
            
            # Parse people
            shareholders = await self._parse_people_section(soup, '.shareholders-section', RoleType.SHAREHOLDER)
            directors = await self._parse_people_section(soup, '.directors-section', RoleType.DIRECTOR)
            commissioners = await self._parse_people_section(soup, '.commissioners-section', RoleType.COMMISSIONER)
            beneficial_owners = await self._parse_people_section(soup, '.beneficial-owners-section', RoleType.BENEFICIAL_OWNER)
            
            # Parse business activities
            activities = []
            for item in soup.select('.business-activity-item'):
                activities.append(item.text.strip())
            
            # Parse KBLI codes
            kblis = []
            for item in soup.select('.kbli-code-item'):
                kblis.append(item.text.strip())
            
            # Parse address
            address = self._extract_text(soup, '.address-full')
            province = self._extract_text(soup, '.province')
            city = self._extract_text(soup, '.city')
            postal = self._extract_text(soup, '.postal-code')
            
            # Parse status
            status = self._extract_text(soup, '.company-status') or 'active'
            
            # Parse last updated
            last_updated = self._extract_text(soup, '.last-updated')
            
            return Company(
                name=name or "",
                npwb=npwb or "",
                establishment_date=est_date or "",
                establishment_deed=est_deed or "",
                capital_authorized=capital_auth,
                capital_paid=capital_paid,
                shareholders=shareholders,
                directors=directors,
                commissioners=commissioners,
                beneficial_owners=beneficial_owners,
                business_activities=activities,
                kblis_codes=kblis,
                address=address or "",
                province=province or "",
                city=city or "",
                postal_code=postal or "",
                status=status,
                last_updated=last_updated or datetime.now(timezone.utc).isoformat(),
                source_url=url
            )
            
        except Exception as e:
            logger.warning(f"Fetch company details error: {e}")
            return None
    
    async def _parse_people_section(self, soup, selector: str, role_type: RoleType) -> List[PersonRole]:
        """Parse people section (shareholders, directors, etc.)."""
        people = []
        
        try:
            section = soup.select_one(selector)
            if not section:
                return people
            
            for person_el in section.select('.person-item'):
                name = self._extract_text(person_el, '.person-name')
                
                # For shareholders, extract percentage
                shares_percent = None
                shares_value = None
                if role_type == RoleType.SHAREHOLDER:
                    pct_text = self._extract_text(person_el, '.shares-percent')
                    if pct_text:
                        pct_match = re.search(r'([\d.]+)%', pct_text)
                        if pct_match:
                            shares_percent = float(pct_match.group(1))
                    
                    val_text = self._extract_text(person_el, '.shares-value')
                    if val_text:
                        shares_value = self._parse_currency(val_text)
                
                # Extract appointment date
                appt_date = self._extract_text(person_el, '.appointment-date')
                
                # Extract ID (masked)
                id_num = self._extract_text(person_el, '.id-number')
                
                # Extract address
                addr = self._extract_text(person_el, '.address')
                
                if name:
                    people.append(PersonRole(
                        name=name,
                        role=role_type,
                        shares_percent=shares_percent,
                        shares_value=shares_value,
                        appointment_date=appt_date,
                        id_number=id_num,
                        address=addr
                    ))
        
        except Exception as e:
            logger.warning(f"Parse people section error: {e}")
        
        return people
    
    def _extract_text(self, soup, selector: str) -> str:
        """Safely extract text from element."""
        el = soup.select_one(selector)
        return el.text.strip() if el else ""
    
    def _parse_currency(self, value_str: str) -> float:
        """Parse Indonesian currency format to float."""
        if not value_str:
            return 0.0
        try:
            # Remove Rp, dots, spaces; replace comma with dot
            cleaned = value_str.replace('Rp', '').replace('.', '').replace(',', '.').replace(' ', '')
            return float(cleaned)
        except:
            return 0.0
    
    async def find_companies_by_person(self, person_name: str) -> List[Company]:
        """
        Find all companies where a person has any role.
        Uses multiple search strategies for comprehensive coverage.
        """
        companies = []
        seen_npwb: Set[str] = set()
        
        # Strategy 1: Search by full name
        results = await self.search_company_by_name(person_name)
        for company in results:
            if company.npwb not in seen_npwb:
                # Check if person is actually in the company
                if self._person_in_company(person_name, company):
                    companies.append(company)
                    seen_npwb.add(company.npwb)
        
        # Strategy 2: Search by last name only (for common names)
        name_parts = person_name.split()
        if len(name_parts) > 1:
            last_name = name_parts[-1]
            await asyncio.sleep(self.delay)
            results = await self.search_company_by_name(last_name)
            for company in results:
                if company.npwb not in seen_npwb:
                    if self._person_in_company(person_name, company):
                        companies.append(company)
                        seen_npwb.add(company.npwb)
        
        # Strategy 3: Search variations (with titles, etc.)
        variations = [
            f"Ir. {person_name}",
            f"Dr. {person_name}",
            f"H. {person_name}",
            f"Hj. {person_name}",
        ]
        
        for variant in variations:
            await asyncio.sleep(self.delay)
            results = await self.search_company_by_name(variant)
            for company in results:
                if company.npwb not in seen_npwb:
                    if self._person_in_company(person_name, company):
                        companies.append(company)
                        seen_npwb.add(company.npwb)
        
        return companies
    
    def _person_in_company(self, person_name: str, company: Company) -> bool:
        """Check if person appears in any role in the company."""
        name_lower = person_name.lower()
        name_parts = set(person_name.lower().split())
        
        all_people = (
            company.shareholders + 
            company.directors + 
            company.commissioners + 
            company.beneficial_owners
        )
        
        for person_role in all_people:
            role_name_lower = person_role.name.lower()
            
            # Exact match
            if name_lower == role_name_lower:
                return True
            
            # Partial match (name contains)
            if name_lower in role_name_lower or role_name_lower in name_lower:
                return True
            
            # Token overlap (for slight variations)
            role_parts = set(role_name_lower.split())
            overlap = name_parts & role_parts
            if len(overlap) >= max(len(name_parts) - 1, 2):
                return True
        
        return False
    
    async def get_ownership_chain(self, company_name: str, target_person: str, max_depth: int = 3) -> List[OwnershipChain]:
        """
        Trace ownership chain from company to ultimate beneficial owner.
        Detects indirect ownership through intermediate companies.
        """
        chains = []
        
        # Start with direct company
        companies = await self.search_company_by_name(company_name, exact=True)
        if not companies:
            return chains
        
        company = companies[0]
        
        # Check direct ownership
        for shareholder in company.shareholders:
            if self._names_match(shareholder.name, target_person):
                chains.append(OwnershipChain(
                    company_name=company_name,
                    owner_name=target_person,
                    ownership_percent=shareholder.shares_percent or 0.0,
                    is_direct=True,
                    confidence=0.95
                ))
        
        # TODO: Recursive search for indirect ownership
        # This would require traversing corporate structures
        
        return chains
    
    def _names_match(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
        """Fuzzy name matching for Indonesian names."""
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()
        
        # Exact match
        if n1 == n2:
            return True
        
        # One contains the other
        if n1 in n2 or n2 in n1:
            return True
        
        # Token-based similarity
        tokens1 = set(n1.split())
        tokens2 = set(n2.split())
        
        if not tokens1 or not tokens2:
            return False
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        similarity = len(intersection) / len(union) if union else 0
        
        return similarity >= threshold


class OSSCrawler:
    """
    OSS (Online Single Submission) crawler for business licensing data.
    Provides additional verification of business activities and investments.
    
    Source: https://oss.go.id
    """
    
    BASE_URL = "https://oss.go.id"
    
    def __init__(self, delay: float = 3.0):
        self.delay = delay
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def lookup_nib(self, nib: str) -> Optional[Dict]:
        """Lookup company by NIB (Nomor Induk Berusaha)."""
        try:
            url = f"{self.BASE_URL}/nib/{nib}"
            resp = await self.client.get(url)
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'nib': nib,
                    'company_name': data.get('nama_perusahaan', ''),
                    'npwp': data.get('npwp', ''),
                    'establishment_date': data.get('tanggal_daftar', ''),
                    'status': data.get('status', ''),
                    'risk_level': data.get('tingkat_risiko', ''),
                    'kblis': data.get('kblis', []),
                    'address': data.get('alamat', ''),
                    'province': data.get('provinsi', ''),
                    'capital': data.get('modal', 0),
                    'source_url': url
                }
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.warning(f"OSS NIB lookup error: {e}")
        
        return None
    
    async def search_by_sector(self, sector: str, province: str = None) -> List[Dict]:
        """Search companies by business sector/KBLI code."""
        companies = []
        
        try:
            params = {'sector': sector}
            if province:
                params['province'] = province
            
            url = f"{self.BASE_URL}/api/companies"
            resp = await self.client.get(url, params=params)
            
            if resp.status_code == 200:
                data = resp.json()
                companies = data.get('results', [])
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.warning(f"OSS sector search error: {e}")
        
        return companies


class IDXCrawler:
    """
    Indonesia Stock Exchange crawler for public companies.
    Tracks politician connections to publicly traded companies.
    
    Source: https://idx.co.id
    """
    
    BASE_URL = "https://idx.co.id"
    
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def get_listed_companies(self) -> List[Dict]:
        """Get all companies listed on IDX."""
        companies = []
        
        try:
            url = f"{self.BASE_URL}/en/stock-market/list-of-companies/"
            resp = await self.client.get(url)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                for row in soup.select('.company-row'):
                    ticker = self._extract_text(row, '.ticker')
                    name = self._extract_text(row, '.company-name')
                    sector = self._extract_text(row, '.sector')
                    
                    if ticker and name:
                        companies.append({
                            'ticker': ticker,
                            'name': name,
                            'sector': sector,
                            'listing_date': self._extract_text(row, '.listing-date'),
                            'shares_outstanding': self._parse_number(self._extract_text(row, '.shares')),
                            'market_cap': self._parse_number(self._extract_text(row, '.market-cap')),
                            'source_url': f"{self.BASE_URL}/en/stock-market/stock-profile/?code={ticker}"
                        })
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.warning(f"IDX listed companies error: {e}")
        
        return companies
    
    async def get_company_profile(self, ticker: str) -> Optional[Dict]:
        """Get detailed profile for a listed company."""
        try:
            url = f"{self.BASE_URL}/en/stock-market/stock-profile/?code={ticker}"
            resp = await self.client.get(url)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Extract commissioners and directors
                commissioners = []
                for item in soup.select('.commissioner-item'):
                    commissioners.append({
                        'name': self._extract_text(item, '.name'),
                        'position': self._extract_text(item, '.position'),
                        'appointment_date': self._extract_text(item, '.appointment-date')
                    })
                
                directors = []
                for item in soup.select('.director-item'):
                    directors.append({
                        'name': self._extract_text(item, '.name'),
                        'position': self._extract_text(item, '.position'),
                        'appointment_date': self._extract_text(item, '.appointment-date')
                    })
                
                # Extract major shareholders
                shareholders = []
                for item in soup.select('.shareholder-item'):
                    shareholders.append({
                        'name': self._extract_text(item, '.name'),
                        'shares_percent': self._parse_percent(self._extract_text(item, '.percent')),
                        'shares_count': self._parse_number(self._extract_text(item, '.count'))
                    })
                
                return {
                    'ticker': ticker,
                    'company_name': self._extract_text(soup, '.company-name'),
                    'sector': self._extract_text(soup, '.sector'),
                    'sub_sector': self._extract_text(soup, '.sub-sector'),
                    'commissioners': commissioners,
                    'directors': directors,
                    'major_shareholders': shareholders,
                    'financials': self._extract_financials(soup),
                    'source_url': url
                }
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.warning(f"IDX company profile error: {e}")
        
        return None
    
    def _extract_text(self, soup, selector: str) -> str:
        el = soup.select_one(selector)
        return el.text.strip() if el else ""
    
    def _parse_number(self, value_str: str) -> float:
        if not value_str:
            return 0.0
        try:
            return float(value_str.replace(',', ''))
        except:
            return 0.0
    
    def _parse_percent(self, value_str: str) -> float:
        if not value_str:
            return 0.0
        try:
            return float(value_str.replace('%', ''))
        except:
            return 0.0
    
    def _extract_financials(self, soup) -> Dict:
        """Extract key financial metrics."""
        return {
            'revenue': self._parse_number(self._extract_text(soup, '.revenue')),
            'net_income': self._parse_number(self._extract_text(soup, '.net-income')),
            'total_assets': self._parse_number(self._extract_text(soup, '.total-assets')),
            'equity': self._parse_number(self._extract_text(soup, '.equity'))
        }


class BusinessRegistryIntegration:
    """
    Unified interface for all business registry sources.
    Orchestrates crawlers and provides consolidated business intelligence.
    """
    
    def __init__(self):
        self.ahu = AHUEnhancedCrawler()
        self.oss = OSSCrawler()
        self.idx = IDXCrawler()
    
    async def close_all(self):
        await self.ahu.close()
        await self.oss.close()
        await self.idx.close()
    
    async def get_person_business_portfolio(self, person_name: str) -> Dict:
        """
        Get complete business portfolio for a person.
        Aggregates data from all registries.
        """
        portfolio = {
            'person': person_name,
            'total_companies': 0,
            'as_shareholder': [],
            'as_commissioner': [],
            'as_director': [],
            'as_beneficial_owner': [],
            'estimated_total_value': 0.0,
            'sectors': set(),
            'public_companies': [],
            'private_companies': [],
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Search AHU (private companies)
        ahu_companies = await self.ahu.find_companies_by_person(person_name)
        
        for company in ahu_companies:
            portfolio['total_companies'] += 1
            
            # Categorize by role
            for role in company.shareholders:
                if self.ahu._names_match(role.name, person_name):
                    portfolio['as_shareholder'].append({
                        'company': company.name,
                        'npwb': company.npwb,
                        'shares_percent': role.shares_percent,
                        'shares_value': role.shares_value,
                        'province': company.province
                    })
                    if role.shares_value:
                        portfolio['estimated_total_value'] += role.shares_value
                    company.business_activities and portfolio['sectors'].update(company.business_activities)
            
            for role in company.commissioners:
                if self.ahu._names_match(role.name, person_name):
                    portfolio['as_commissioner'].append({
                        'company': company.name,
                        'npwb': company.npwb,
                        'appointment_date': role.appointment_date,
                        'province': company.province
                    })
                    company.business_activities and portfolio['sectors'].update(company.business_activities)
            
            for role in company.directors:
                if self.ahu._names_match(role.name, person_name):
                    portfolio['as_director'].append({
                        'company': company.name,
                        'npwb': company.npwb,
                        'appointment_date': role.appointment_date,
                        'province': company.province
                    })
                    company.business_activities and portfolio['sectors'].update(company.business_activities)
            
            for role in company.beneficial_owners:
                if self.ahu._names_match(role.name, person_name):
                    portfolio['as_beneficial_owner'].append({
                        'company': company.name,
                        'npwb': company.npwb,
                        'ownership_percent': role.shares_percent,
                        'province': company.province
                    })
            
            portfolio['private_companies'].append({
                'name': company.name,
                'npwb': company.npwb,
                'province': company.province,
                'status': company.status
            })
        
        # Search IDX (public companies)
        idx_companies = await self.idx.get_listed_companies()
        
        for company in idx_companies:
            # Check commissioners
            profile = await self.idx.get_company_profile(company['ticker'])
            if profile:
                for comm in profile.get('commissioners', []):
                    if self.ahu._names_match(comm['name'], person_name):
                        portfolio['as_commissioner'].append({
                            'company': company['name'],
                            'ticker': company['ticker'],
                            'position': comm['position'],
                            'appointment_date': comm['appointment_date'],
                            'is_public': True
                        })
                        portfolio['public_companies'].append({
                            'name': company['name'],
                            'ticker': company['ticker'],
                            'sector': company['sector']
                        })
                
                for director in profile.get('directors', []):
                    if self.ahu._names_match(director['name'], person_name):
                        portfolio['as_director'].append({
                            'company': company['name'],
                            'ticker': company['ticker'],
                            'position': director['position'],
                            'appointment_date': director['appointment_date'],
                            'is_public': True
                        })
                        portfolio['public_companies'].append({
                            'name': company['name'],
                            'ticker': company['ticker'],
                            'sector': company['sector']
                        })
                
                for shareholder in profile.get('major_shareholders', []):
                    if self.ahu._names_match(shareholder['name'], person_name):
                        portfolio['as_shareholder'].append({
                            'company': company['name'],
                            'ticker': company['ticker'],
                            'shares_percent': shareholder['shares_percent'],
                            'shares_count': shareholder['shares_count'],
                            'is_public': True
                        })
                        portfolio['public_companies'].append({
                            'name': company['name'],
                            'ticker': company['ticker'],
                            'sector': company['sector']
                        })
        
        # Convert sectors set to list for JSON serialization
        portfolio['sectors'] = list(portfolio['sectors'])
        
        return portfolio
    
    async def detect_conflicts_of_interest(self, person_name: str, position: str) -> List[Dict]:
        """
        Detect potential conflicts of interest based on business holdings.
        
        Examples:
        - Minister of Energy owns coal mining companies
        - DPR member in Commission VI (industry) owns manufacturing companies
        - Governor owns construction companies operating in their province
        """
        conflicts = []
        
        portfolio = await self.get_person_business_portfolio(person_name)
        
        # Define conflict patterns
        conflict_patterns = {
            'energy_minister_mining': {
                'positions': ['Menteri ESDM', 'Staf Khusus Menteri ESDM'],
                'sectors': ['Pertambangan', 'Energi', 'Minyak dan Gas'],
                'severity': 'critical'
            },
            'transport_minister_infrastructure': {
                'positions': ['Menteri Perhubungan', 'Dirjen Perhubungan'],
                'sectors': ['Transportasi', 'Konstruksi Jalan', 'Logistik'],
                'severity': 'high'
            },
            'agriculture_minister_agribusiness': {
                'positions': ['Menteri Pertanian', 'Staf Khusus Menteri Pertanian'],
                'sectors': ['Perkebunan', 'Pertanian', 'Agroindustri'],
                'severity': 'high'
            },
            'dpr_commission_vi_industry': {
                'positions': ['Anggota Komisi VI DPR', 'Ketua Komisi VI DPR'],
                'sectors': ['Manufaktur', 'Industri', 'Perdagangan'],
                'severity': 'medium'
            },
            'governor_local_construction': {
                'positions': ['Gubernur', 'Wakil Gubernur'],
                'sectors': ['Konstruksi', 'Pengembangan Properti'],
                'severity': 'high'
            }
        }
        
        # Check each pattern
        for pattern_id, pattern in conflict_patterns.items():
            # Check if position matches
            position_match = any(pos.lower() in position.lower() for pos in pattern['positions'])
            
            if position_match:
                # Check if business sectors match
                matching_sectors = set(portfolio['sectors']) & set(pattern['sectors'])
                
                if matching_sectors:
                    conflicts.append({
                        'type': pattern_id,
                        'severity': pattern['severity'],
                        'position': position,
                        'conflicting_sectors': list(matching_sectors),
                        'companies': portfolio['private_companies'] + portfolio['public_companies'],
                        'recommendation': f"Review for potential divestment required"
                    })
        
        return conflicts


# Convenience functions
async def crawl_business_portfolio(person_name: str) -> Dict:
    """Quick helper to get person's business portfolio."""
    integration = BusinessRegistryIntegration()
    try:
        return await integration.get_person_business_portfolio(person_name)
    finally:
        await integration.close_all()


async def detect_conflicts(person_name: str, position: str) -> List[Dict]:
    """Quick helper to detect conflicts of interest."""
    integration = BusinessRegistryIntegration()
    try:
        return await integration.detect_conflicts_of_interest(person_name, position)
    finally:
        await integration.close_all()
