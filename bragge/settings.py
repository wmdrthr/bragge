# Scrapy settings for bragge project

import os

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
}

BASEDIR = os.getenv('BRAGGE_BASEDIR', '/tmp/bragge')

FILES_STORE  = os.path.join(BASEDIR, 'files/audio/')
IMAGES_STORE = os.path.join(BASEDIR, 'files/images/')
IMAGES_THUMBS = { 'small': (128, 72) }

HTTPCACHE_ENABLED = True
HTTPCACHE_DIR = os.path.join(BASEDIR, 'httpcache')
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
