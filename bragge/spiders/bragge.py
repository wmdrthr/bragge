#! encoding: utf-8

from urllib.parse import urljoin
import string

import scrapy
from sqlalchemy import create_engine, Table, MetaData, select
import pendulum

GENRES = {'Culture', 'History', 'Philosophy', 'Religion', 'Science'}
ERAS = {'Prehistoric', 'Mesopotamian', 'Ancient Egypt', 'Ancient Greece',
        'Ancient Rome', 'Early Middle Ages', 'Medieval', 'Renaissance',
        '16th Century', '17th Century', '18th Century', 'Enlightenment',
        'Romantic', '19th Century', 'Victorian', '20th Century'}

class Bragge(scrapy.Spider):

    name = 'bragge'
    start_url = 'https://www.bbc.co.uk/programmes/p0054578'

    def start_requests(self):

        engine = create_engine(self.crawler.settings.get('DATABASE_URL'))
        metadata = MetaData(bind=engine)
        episodes = Table('episodes', metadata, autoload=True)

        with engine.connect() as connection:
            result = connection.execute(select([episodes.c.url]).
                                        order_by(episodes.c.parsed_at.desc())
                                        .limit(1))
            row = result.first()
            if row is not None:
                self.logger.info(f'Resuming crawl from {row["url"]}')
                return [scrapy.Request(row['url'], callback = self.parse_next)]
            else:
                self.logger.info(f'Starting crawl from {self.start_url}')
                return [scrapy.Request(self.start_url, callback = self.parse)]

    def parse_next(self, response):

        # Is the next episode available? We know the current episode's
        # date, and we know the episodes are published on Thursdays,
        # so check if the next Thursday after the current episode's
        # date is in the future.

        episode_date = response.xpath('//div[@class="broadcast-event__time beta"]/@content').get()
        episode_date = pendulum.parse(episode_date)
        today = pendulum.today('UTC')
        if episode_date.next(pendulum.THURSDAY) < today:
            next_link = response.xpath('//a[@data-bbc-title="next:title"]/@href').get()
            if next_link is not None:
                return scrapy.Request(next_link, callback = self.parse)
            else:
                return None
        else:
            return None

    def parse(self, response):

        slug = response.url.split('/')[-1]

        title = response.xpath('//div[@class="island"]//h1[@class="no-margin"]/text()').get()

        episode_date = response.xpath('//div[@class="broadcast-event__time beta"]/@content').get()
        if episode_date is None:
            episode_date = response.xpath('//div[@class="episode-panel__meta"]/time/@datetime').get()
        episode_date = pendulum.parse(episode_date)

        synopsis = response.xpath('//div[@class="island"]//div[@class="synopsis-toggle__short"]/p/text()').get()
        if synopsis[-1] != '.':
            synopsis = synopsis + '.'

        description_nodes = response.xpath('//div[@class="island"]//div[@class="synopsis-toggle__long"]/p')
        description = []
        if len(description_nodes) > 0:
            for node in response.xpath('//div[@class="island"]//div[@class="synopsis-toggle__long"]/p'):
                description.append(node.get())

        file_urls = []
        audio_url = response.xpath('//div[@class="buttons__download"]/a/@href').get()
        if audio_url is None:
            audio_url = response.xpath('//a[@aria-label="Download Higher quality (128kbps) "]/@href').get()

        if audio_url is not None:
            file_urls.append(urljoin(response.url, audio_url))

        image_url = response.xpath('//div[@class="episode-playout"]//img/@src').get()

        links = []
        reading_list = []
        parent = response.xpath('//div[@id="features"]//div[@class="feature__description centi"]')
        if parent is not None:
            # links
            nodes = list(parent.xpath('p/strong/parent::p/preceding-sibling::p'))
            for node in nodes[:-1]:
                links.append(node.get())

            # reading list
            nodes = list(parent.xpath('p/strong/parent::p/following-sibling::p'))
            for node in nodes[:-1]:
                reading_list.append(node.get())

        genre = era = None
        featured_container = response.xpath('//a[@data-bbc-title="featured-in:group:title"]')
        for collection in featured_container.xpath('span[@class="programme__title "]/span/text()').getall():
            if collection in GENRES:
                genre = collection
            elif collection in ERAS:
                era = collection

        yield { 'url': response.url,
                'slug': slug,
                'title': title,
                'date': episode_date,
                'synopsis': synopsis,
                'description': description,
                'links': links,
                'reading_list': reading_list,
                'genre': genre,
                'era': era,
                'image_urls': [image_url],
                'file_urls': file_urls}

        yield self.parse_next(response)

