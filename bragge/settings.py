# Scrapy settings for bragge project

import os, sys
import json
from datetime import datetime

BOT_NAME = 'bragge'
SPIDER_MODULES = ['bragge.spiders']

USER_AGENT = 'shiny-armadillo/0.1.0'
ROBOTSTXT_OBEY = False
MEDIA_ALLOW_REDIRECTS = True

TELNETCONSOLE_ENABLED = False

EXTENSIONS = {
    'scrapy.extensions.closespider.CloseSpider' : 1
}
CLOSESPIDER_ERRORCOUNT = 1
CLOSESPIDER_ITEMCOUNT = 3
CONCURRENT_REQUESTS = 1


ITEM_PIPELINES = {
    'scrapy.pipelines.files.FilesPipeline': 10,
    'scrapy.pipelines.images.ImagesPipeline': 20,
    'bragge.pipelines.BraggeValidationPipeline': 100,
    'bragge.pipelines.BraggePipeline': 200,
}

BASEDIR = os.getenv('BRAGGE_BASEDIR', '/tmp/bragge')

FILES_STORE  = os.path.join(BASEDIR, 'download/audio/')
IMAGES_STORE = os.path.join(BASEDIR, 'download/images/')
IMAGES_THUMBS = { 'small': (128, 72) }

HTTPCACHE_ENABLED = True
HTTPCACHE_DIR = os.path.join(BASEDIR, 'httpcache')
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

now = datetime.utcnow()
LOG_FILE = os.path.join(BASEDIR, 'logs', now.strftime('bragge-%Y%m%d_%H%M%S.log'))

DATABASE_URL = os.getenv('BRAGGE_DATABASE', f'sqlite:///{os.path.join(BASEDIR, "bragge.db")}')

config_file = os.getenv('BRAGGE_CONFIG_FILE', os.path.join(BASEDIR, 'config'))
if os.path.exists(config_file):
    try:
        with open(config_file, 'rb') as f:
            config = json.loads(f.read())

        for key, value in config.items():
            globals()[key.upper()] = value
    except Exception as e:
        print(f'Invalid config file ({config_file}): {str(e)}')
        sys.exit(5)


