from typing import List
import json
import requests
import datetime
import aiohttp
import asyncio

class Service:
    name: str = None
    contains: List[str] = []
    url: str = None
    status: int = 0
    headers = {}

class HealthChecker:
    def __init__(self):
        self.reports = {}
        self.statuses = {}
        self.services: List[Service] = []
        with open('config.json') as f:
            j = json.loads(' '.join(f.readlines()))
            for i in j:
                s = Service()
                s.__dict__ = i
                self.services.append(s)

    async def check_service(self, session, s):
        hasError = False
        errorMsg = f"Service: {s.name}, Error(s): "
        try:
            async with session.get(s.url, headers=s.headers, verify_ssl=False, timeout=30) as r:
                if (r.status is not s.status):
                    errorMsg += f"\n\tStatus code error: Expected {s.status} but received {r.status_code}"
                    hasError = True
                content = str(await r.content.read())
                for st in s.contains:
                    if st not in content:
                        errorMsg += f"\n\tContent error: Did not find string \"{st}\" in response"
                        hasError = True
        except Exception as e:
            errorMsg += f"\n\tError: {str(e)}"
            hasError = True

        return (s, hasError, errorMsg)


    async def check_services(self):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for s in self.services:
                tasks.append(asyncio.ensure_future(self.check_service(session, s)))
            results = await asyncio.gather(*tasks)

        errorMsgs = []

        for s, hasError, errorMsg in results:

            if hasError:
                if (s.name not in self.reports) or (self.reports[s.name] < datetime.datetime.now()):
                    self.reports[s.name] = datetime.datetime.now() + datetime.timedelta(hours=4)
                    errorMsgs.append(errorMsg)
                self.statuses[s.name] = False
            else:
                if s.name in self.reports:
                    self.reports.pop(s.name)
                self.statuses[s.name] = True
        if len(errorMsgs) > 0:
            return "\n--------------------\n".join(errorMsgs)
        return None

    async def get_status(self):
        await self.check_services()
        return self.statuses



