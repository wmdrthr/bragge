
import os
import json
from datetime import datetime

import scrapy
from sqlalchemy import create_engine, Table, MetaData
from mutagen import id3

class BraggeValidationPipeline():

    def process_item(self, item, spider):

        try:
            for key in ('slug', 'url', 'title', 'synopsis', 'genre', 'era'):
                assert (key in item and len(item[key]) > 0), f'item does not have {key}'

            assert 'date' in item and item['date'] is not None, 'item does not have date'

            for key in ('links', 'reading_list'):
                if key in item and len(item[key]) > 0:
                    for entry in item[key]:
                        assert len(entry) > 0, f'empty entry in {key}'

            assert 'description' in item, 'missing description'
            assert len(item['description']) > 0, 'empty description'
            for entry in item['description']:
                assert len(entry) > 0, f'empty entry in description'

            assert len(item['files']) == 1 and len(item['files'][0]['path']) > 0, 'missing audio file'
            assert len(item['images']) == 1 and len(item['images'][0]['path']) > 0, 'missing image'

            return item

        except AssertionError as ae:
            for key,val in item.items():
                item[key] = str(val)
            spider.logger.error(f'Dropping item: {json.dumps(item)}')
            raise scrapy.exceptions.DropItem(f'Validation Failure: {ae.args[0]}')

class BraggePipeline():

    def __init__(self, db_engine, basedir, files_store):

        self.resources_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources')

        self.basedir = basedir
        os.makedirs(os.path.join(self.basedir, 'files', 'audio'))

        self.files_store = files_store

        self.engine = db_engine
        self._initialize_database(self.engine)

    @classmethod
    def from_crawler(cls, crawler):

        engine = create_engine(crawler.settings.get('DATABASE_URL'))

        return cls(
            db_engine = engine,
            basedir      = crawler.settings.get('BASEDIR'),
            files_store  = crawler.settings.get('FILES_STORE'),
        )

    def _initialize_database(self, engine):

        metadata = MetaData(bind=engine)

        self.episodes = Table('episodes', metadata, autoload=True)
        self.descriptions = Table('descriptions', metadata, autoload=True)
        self.links = Table('links', metadata, autoload=True)
        self.reading_lists = Table('reading_lists', metadata, autoload=True)

        genres = Table('genres', metadata, autoload=True)
        eras = Table('eras', metadata, autoload=True)

        with engine.connect() as connection:

            self.genres = {}
            result = connection.execute(genres.select())
            for row in result:
                self.genres[row['genre']] = row['id']

            self.eras = {}
            result = connection.execute(eras.select())
            for row in result:
                self.eras[row['era']] = row['id']

    def process_audio_file(self, item):

        mp3file_path = os.path.join(self.files_store, item['files'][0]['path'])
        os.link(mp3file_path, os.path.join(self.basedir, 'files', 'audio', f'{item["slug"]}.mp3'))

        # Update MP3 tags
        try:
            mp3file = id3.ID3(mp3file_path)

            mp3file.delall('USLT')
            mp3file.setall('TIT2', [id3.TIT2(encoding = id3.Encoding.UTF8, text = item['title'])])
            mp3file.setall('TDRC', [id3.TDOR(encoding = id3.Encoding.UTF8, text = item['date'].strftime('%Y-%m-%dT%H:%M:%S'))])
            mp3file.setall('COMM', [id3.COMM(encoding = id3.Encoding.UTF8, lang='eng', text = item['synopsis'])])
            mp3file.setall('TALB', [id3.TALB(encoding = id3.Encoding.UTF8, text = f'In Our Time Archive: {item["genre"]}')])
            mp3file.setall('TLAN', [id3.TLAN(encoding = id3.Encoding.UTF8, text = 'eng')])
            mp3file.setall('TCOP', [id3.TCOP(encoding = id3.Encoding.UTF8, text = f"{item['date'].year} BBC")])

            with open(os.path.join(self.resources_dir, f"{item['genre']}.jpg"), 'rb') as albumart:
                mp3file.setall('APIC', [id3.APIC(encoding = id3.Encoding.UTF8,
                                                 mime = 'image/jpeg',
                                                 type = id3.PictureType.COVER_FRONT,
                                                 desc = 'Cover',
                                                 data = albumart.read())])
            mp3file.save()
        except Exception as e:
            spider.logger.error(f"Error while processing MP3 file: {item['files'][0]['path']}")
            raise

    def persist(self, item):

        with self.engine.begin() as connection:

            keys = ['slug', 'url', 'title', 'date', 'synopsis']
            values = {'parsed_at': datetime.utcnow()}
            for key in keys:
                values[key] = item[key]
            values['genre'] = self.genres[item['genre']]
            values['era'] = self.eras[item['era']]

            result = connection.execute(self.episodes.insert().values(**values))

            episode_id = result.inserted_primary_key[0]

            if len(item['description']) > 0:
                description_values = [{'episodeid':episode_id, 'description': d} for d in item['description']]
                connection.execute(self.descriptions.insert(), description_values)

            if len(item['links']) > 0:
                links_values = [{'episodeid':episode_id, 'link_text': lt} for lt in item['links']]
                connection.execute(self.links.insert(), links_values)

            if len(item['reading_list']) > 0:
                reading_list_values = [{'episodeid':episode_id, 'rl_entry': rle} for rle in item['reading_list']]
                connection.execute(self.links.insert(), reading_list_values)

    def process_item(self, item, spider):

        try:
            self.process_audio_file(item)
            self.persist(item)

            return item
        except:
            for key,val in item.items():
                item[key] = str(val)
            spider.logger.error(f'Error while processing item: {json.dumps(item)}',
                                exc_info=True)
            raise
