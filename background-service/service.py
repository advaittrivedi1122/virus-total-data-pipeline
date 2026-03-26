# from fastapi import APIRouter, Depends, Query
from database import Report, Reports, db, VT_API_KEY
import httpx
from enum import Enum

class Identifiers(Enum):
    IP = 1
    DOMAIN = 2
    FILEHASH = 3

VT_API_RATE_LIMIT_KEY = "vt:rate_limit"
VT_API_RATE_LIMIT_TTL = 60 # reset after 60s (fixed window)
VT_API_RESPONSE_TTL = 300 # cache response for 5m

BASE_IP_VT_API = "https://www.virustotal.com/api/v3/ip_addresses/"
BASE_DOMAIN_VT_API = "https://www.virustotal.com/api/v3/domains/"
BASE_FILEHASH_VT_API = "https://www.virustotal.com/api/v3/files/"

HEADERS = {
    "accept": "application/json",
    "x-apikey": VT_API_KEY
}

RATE_LIMIT_EXCEEDED_ERROR = {"error" : "Virus Total API V3 - Rate Limit Exceeded"}

class BackgroundService:
    def __init__(self):
        self.reports = Reports()
        self.pgdb_session = db.get_db()

    async def get_ip_address_data(self, ip_address: str):
        url = BASE_IP_VT_API + ip_address
        res = await self.get_data(ip_address, Identifiers.IP.value, url)
        return res
    
    async def get_domain_data(self, domain: str):
        url = BASE_DOMAIN_VT_API + domain
        res = await self.get_data(domain, Identifiers.DOMAIN.value, url)
        return res
    
    async def get_filehash_data(self, filehash: str):
        url = BASE_FILEHASH_VT_API + filehash
        res = await self.get_data(filehash, Identifiers.FILEHASH.value, url)
        return res
    
    async def get_data(self, identifier: str, identifier_type: int, url: str):
        db_res = self.check_in_db(identifier, identifier_type)
        if not db_res.get("error"):
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
        self.reports.upsert(report, self.pgdb_session)
        return api_res
    
    def check_in_db(self, identifier: str, identifier_type: int):
        res = self.reports.get(identifier, identifier_type, self.pgdb_session)
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