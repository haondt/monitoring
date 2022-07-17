from typing import List
import json
import requests
import datetime
import aiohttp
import asyncio

class ServiceConfig:
    name: str = None
    contains: List[str] = []
    url: str = None
    status: int = 0
    headers = {}

class Service:
    config: ServiceConfig = None
    errors: List[str] = []
    last_notification: datetime.datetime = None
    is_up: bool = False
    failures: int = 0

    def createErrorMsg(self):
        m = f'Service: {self.config.name}:'
        if self.errors:
            m += ''.join(['\n\t\t' + i for i in self.errors])
        else:
            m += '\nNo errors.'
        return m

class HealthChecker:
    def __init__(self):
        self.services: List[Service] = []
        with open('config.json') as f:
            j = json.loads(' '.join(f.readlines()))
            for i in j:
                sc = ServiceConfig()
                sc.__dict__ = i
                s = Service()
                s.config = sc
                self.services.append(s)

    async def check_service(self, session, s: Service):
        print(s.config.name)
        sc = s.config
        s.errors = []
        hasErrors = False
        try:
            async with session.get(sc.url, headers=sc.headers, verify_ssl=False, timeout=30) as r:
                if (r.status is not sc.status):
                    s.errors.append(f"Status code error: Expected {sc.status} but received {r.status_code}")
                    hasErrors = True
                content = str(await r.content.read())
                for st in sc.contains:
                    if st not in content:
                        s.errors.append(f"Content error: Did not find string \"{st}\" in response")
                        hasErrors = True
        except Exception as e:
            s.errors.append(f"\n\t{type(e).__name__}: {str(e)}")
            hasErrors = True

        if hasErrors:
            s.failures += 1
            if (s.failures > 5):
                s.is_up = False
        else:
            s.is_up = True
            s.failures = 0

    async def ping(self):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for s in self.services:
                tasks.append(asyncio.ensure_future(self.check_service(session, s)))
            await asyncio.gather(*tasks)

    async def get_errors(self) -> str:
        errorMsgs = []
        for s in self.services:
            if s.is_up:
                s.last_notification = None
            else:
                if (s.last_notification is None) or (s.last_notification < datetime.datetime.now() + datetime.timedelta(hours=4)):
                    errorMsgs.append(s.createErrorMsg())
                    s.last_notification = datetime.datetime.now()
        if len(errorMsgs) > 0:
            return "\n--------------------\n".join(errorMsgs)
        return None

    async def get_statuses(self) -> List[Service]:
        return self.services



