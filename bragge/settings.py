# Scrapy settings for bragge project

BOT_NAME = 'bragge'
SPIDER_MODULES = ['bragge.spiders']

USER_AGENT = 'shiny-armadillo/0.1.0'
ROBOTSTXT_OBEY = False

TELNETCONSOLE_ENABLED = False

EXTENSIONS = {
    'scrapy.extensions.closespider.CloseSpider' : 1
}
CLOSESPIDER_ERRORCOUNT = 1
CLOSESPIDER_ITEMCOUNT = 3
CONCURRENT_REQUESTS = 1
