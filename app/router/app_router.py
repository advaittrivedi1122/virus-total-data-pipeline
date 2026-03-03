from fastapi import APIRouter, Depends, Query
from app.database import Report, Reports, db, VT_API_KEY
import httpx
from enum import Enum
import json

class Indentifiers(Enum):
    IP = 1
    DOMAIN = 2
    FILEHASH = 3

VT_API_RATE_LIMIT_KEY = "vt:rate_limit"
VT_API_RATE_LIMIT_TTL = 60 # reset after 60s
VT_API_RESPONSE_TTL = 300 # cache response for 5m

BASE_IP_VT_API = "https://www.virustotal.com/api/v3/ip_addresses/"
BASE_DOMAIN_VT_API = "https://www.virustotal.com/api/v3/domains/"
BASE_FILEHASH_VT_API = "https://www.virustotal.com/api/v3/files/"

HEADERS = {
    "accept": "application/json",
    "x-apikey": VT_API_KEY
}

RATE_LIMIT_EXCEEDED_ERROR = {"error" : "Virus Total API V3 - Rate Limit Exceeded"}

class AppService:
    def __init__(self):
        self.reports = Reports()


    async def get_ip_address_data(self, ip_address: str, refresh: bool, session):
        url = BASE_IP_VT_API + ip_address
        res = await self.get_data(ip_address, Indentifiers.IP.value, url, refresh, session)
        return res
    
    async def get_domain_data(self, domain: str, refresh: bool, session):
        url = BASE_DOMAIN_VT_API + domain
        res = await self.get_data(domain, Indentifiers.DOMAIN.value, url, refresh, session)
        return res
    
    async def get_filehash_data(self, filehash: str, refresh: bool, session):
        url = BASE_FILEHASH_VT_API + filehash
        res = await self.get_data(filehash, Indentifiers.FILEHASH.value, url, refresh, session)
        return res
    
    
    async def get_data(self, identifier: str, identifier_type: int, url: str, refresh: bool, session):
        # if refresh passed, fetch from VT API if rate limit not exceeded and update cache and db
        if not refresh:
            # Check in cache
            cache_res = self.check_in_cache(identifier)
            if cache_res:
                return cache_res # found in cache, return
            # Check in db (not present in cache)
            db_res = self.check_in_db(identifier, identifier_type, session)
            if not db_res.get("error"):
                # populate cache as data found from db
                db._redis.setex(identifier, 600, json.dumps(db_res))
                return db_res # found in db, return
        # Call VT API if rate limit not exceeded
        rate_limit_exceeded = self.check_rate_limit_exceeded()
        if rate_limit_exceeded:
            return RATE_LIMIT_EXCEEDED_ERROR
        api_res = await self.call_vt_api(url)
        if api_res.get("error"):
            return api_res
        # add to db
        report = Report(identifier=identifier, identifier_type=identifier_type, data=api_res)
        self.reports.upsert(report, session)
        # populate cache
        db._redis.setex(identifier, 600, json.dumps(api_res))
        return api_res
    

    def check_in_cache(self, identifier: str):
        res = None
        raw_res = db._redis.get(identifier)
        if raw_res:
            res = json.loads(raw_res)
        return res
    

    def check_in_db(self, identifier: str, identifier_type: int, session):
        res = self.reports.get(identifier, identifier_type, session)
        return res
    
    
    async def call_vt_api(self, url: str):
        async with httpx.AsyncClient(timeout=5) as client:
            try:
                response = await client.get(url, headers=HEADERS)
                return response.json()
            except httpx.RequestError as e:
                return {"error": str(e)}
    

    def check_rate_limit_exceeded(self):
        count = db._redis.incr(VT_API_RATE_LIMIT_KEY)
        if count == 1:
            db._redis.expire(VT_API_RATE_LIMIT_KEY, VT_API_RATE_LIMIT_TTL)
        elif count > 4:
            return True
        return False
        


class AppRouter:
    def __init__(self):
        self.service = AppService()
        self.router = APIRouter(prefix="/api/v1")
        self._setup_routes()
    
    def _setup_routes(self):
        # ip address
        @self.router.get("/ip/{ip_address}")
        async def get_ip_details(ip_address: str, refresh: bool = Query(False), session = Depends(db.get_db)):
            res = await self.service.get_ip_address_data(ip_address, refresh, session)
            return res
        # domain
        @self.router.get("/domain/{domain}")
        async def get_domain_details(domain: str, refresh: bool = Query(False), session = Depends(db.get_db)):
            res = await self.service.get_domain_data(domain, refresh, session)
            return res
        # file hash
        @self.router.get("/filehash/{filehash}")
        async def get_filehash_details(filehash: str, refresh: bool = Query(False), session = Depends(db.get_db)):
            res = await self.service.get_filehash_data(filehash, refresh, session)
            return res
            
            



# router = APIRouter()

# @router.get("/router")