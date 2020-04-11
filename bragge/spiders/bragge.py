#! encoding: utf-8

from urllib.parse import urljoin
import string

import scrapy
import pendulum

class Bragge(scrapy.Spider):

    name = 'bragge'
    start_urls = ['https://www.bbc.co.uk/programmes/p0054578']

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

        yield { 'url': response.url,
                'slug': slug,
                'title': title,
                'date': episode_date,
                'synopsis': synopsis,
                'description': description,
                'links': links,
                'reading_list': reading_list,
                'image_urls': [image_url],
                'file_urls': file_urls}

        yield self.parse_next(response)

