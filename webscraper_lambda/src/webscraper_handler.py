import logging
import time
import json

import requests
from pydantic import BaseModel, ValidationError, HttpUrl, model_validator
from typing import Optional, Any

from starlette.exceptions import HTTPException
from typing_extensions import Self

from WebScraperService import WebScraper

logger = logging.getLogger()
logger.setLevel("INFO")

"""
It should be said, that the current implementation, completely ignores the robots.txt for any given website.
Instead, if our initial ping request is blocked, we just use a Bright Data proxy and scrape it anyway.
This is makes one liable to legal repercussions and should adressed in the future. Since my internship ends soon, 
i won't have time to implement a proper check for this. However, it is a pretty simple implementation:

Every website, that has declared a robots.txt, has a specific endpoint for this: 
Example: https://www.audiobooks.com/robots.txt
This file specifies which domains/sub-domains are off limits for scraping. This should be read and parsed, such that
we don't scrape any sites outlined in the .txt file. 

If robots.txt isn't present at <website>/robots.txt, then they have not declared a robots.txt, and can be scraped freely.
This means, that if our ping to <website>/robots.txt doesn't yield any meaningful output, then we just proceed as usual.
"""


# The possible values that our request can contain. URL is obligatory, proxy and monitor are both optional.
class Body(BaseModel):
    url: HttpUrl = None
    proxy: Optional[bool] = False
    monitor: Optional[bool] = False


class Event(Body):
    body: Body

    # Pydantic decorator for validating models.
    # See https://docs.pydantic.dev/latest/concepts/validators/#model-validators
    @model_validator(mode='before')
    @classmethod
    def check_parameters(cls, data: Any) -> Any:
        """Check parameters in request, should adhere to the right types and URL should always be present"""
        logger.info(data)
        if isinstance(data, dict):
            if 'body' in data and isinstance(data['body'], str):
                data['body'] = json.loads(data['body'])
            elif 'body' not in data:
                data = {'body': data}
            assert ('url' in data['body']), 'Please provide a URL'
            return data

    @model_validator(mode='after')
    def validate_pairs(self) -> Self:
        """Check pairs in request. URL and monitor can't both be present, when proxy is absent.
        Monitor and proxy also can't be present without a URL."""
        url = self.body.url
        proxy = self.body.proxy
        monitor = self.body.monitor

        if url and monitor and not proxy:
            raise ValidationError("Can't monitor bandwith/costs when proxy is not defined.\n")
        if proxy and monitor and not url:
            raise ValidationError("Can't monitor bandwith/costs without a URL to visit.\n")
        return self


def handler(event: dict, context) -> dict:
    try:
        request = Event.model_validate(event)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    flag1 = time.perf_counter()

    body = request.body
    logger.info(f"Request good, body is: {body}")
    url, proxy, monitor = str(body.url), bool(body.proxy), bool(body.monitor)

    if proxy is False:
        proxy = ping_site(url)

    site_text = WebScraper(proxy, monitor, url).extract_text()

    flag2 = time.perf_counter()
    # Calculate performance and return finished campaign and/or message templates.
    logger.info(f"Entire process was executed in {flag2 - flag1:.2f} seconds.")

    return {
        'statusCode': 200,
        "ExecutedVersion": "$LATEST",
        'body': json.dumps({
            'site_text': site_text,
            'proxy_enabled': proxy,
        }, ensure_ascii=False,
            indent=2)
    }


def ping_site(url) -> bool:
    """Function for pinging a website to check if it's blocked/exists or not."""
    ping = requests.get(url, timeout=5)
    logger.info(f"Response from request: {ping}")
    if ping.status_code != 200:
        logger.info(f"Request was blocked. Retrying with proxy.")
        return True
    elif ping.status_code in [200, 201, 202]:
        logger.info(f"Request successful. Proceeding without proxy.")
        return False
    else:
        raise HTTPException(status_code=500, detail=f"Error when pinging website: {ping}")
