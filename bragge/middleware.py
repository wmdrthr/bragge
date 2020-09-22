#! encoding: utf-8

import logging
import re

import scrapy

logger = logging.getLogger(__name__)

def length_from_range_header(header_value):

    header_value = header_value.decode('ascii')

    if (m := re.match(r'bytes \d+-\d+/(\d+)', header_value)):
        return int(m.group(1))

    return -1

class FallbackDownloader:

    def __init__(self, user_agent):

        self.user_agent = user_agent

    @classmethod
    def from_crawler(cls, crawler):

        return cls(crawler.settings.get('USER_AGENT'))

    def process_response(self, request, response, spider):

        if response.status == 206:
            # If we got a partial response, but the response contains
            # all the data, pretend we got a successful response.
            if len(response.body) == length_from_range_header(response.headers.get('Content-Range')):
                return response.replace(status = 200)

        return response
