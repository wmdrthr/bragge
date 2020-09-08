
import os
import json
from datetime import datetime
import hashlib

import scrapy
from sqlalchemy import create_engine, Table, MetaData
from mutagen import id3
import boto3, botocore

def calculate_md5(file_path):
    m = hashlib.md5()
    with open(file_path, 'rb') as f:
        m.update(f.read())
    return f'"{m.hexdigest()}"' # quotes to match the ETag value from S3

def object_exists(obj, file_path):

    try:
        obj.load()
        if obj.e_tag == calculate_md5(file_path):
            return True
        return False
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            # 404 => object does not exist
            return False
        else:
            # some other error, let caller handle it
            raise

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

    def __init__(self, basedir, files_store, images_store):

        self.resources_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources')

        self.basedir = basedir
        self.files_store = files_store
        self.images_store = images_store

    @classmethod
    def from_crawler(cls, crawler):

        pipeline = cls(
            basedir      = crawler.settings.get('BASEDIR'),
            files_store  = crawler.settings.get('FILES_STORE'),
            images_store = crawler.settings.get('IMAGES_STORE'))

        pipeline._initialize_database(crawler)
        pipeline._initialize_storage(crawler)

        return pipeline

    def _initialize_database(self, crawler):

        self.engine = create_engine(crawler.settings.get('DATABASE_URL'))
        metadata = MetaData(bind=self.engine)

        self.episodes = Table('episodes', metadata, autoload=True)
        self.descriptions = Table('descriptions', metadata, autoload=True)
        self.links = Table('links', metadata, autoload=True)
        self.reading_lists = Table('reading_lists', metadata, autoload=True)

        genres = Table('genres', metadata, autoload=True)
        eras = Table('eras', metadata, autoload=True)

        with self.engine.connect() as connection:

            self.genres = {}
            result = connection.execute(genres.select())
            for row in result:
                self.genres[row['genre']] = row['id']

            self.eras = {}
            result = connection.execute(eras.select())
            for row in result:
                self.eras[row['era']] = row['id']

    def _initialize_storage(self, crawler):

        self.bucket_name = crawler.settings.get('BUCKET_NAME')

        if self.bucket_name is None:
            os.makedirs(os.path.join(self.basedir, 'files', 'audio'), exist_ok = True)
            os.makedirs(os.path.join(self.basedir, 'files', 'images', 'thumbnails'), exist_ok = True)
            return

        credentials = crawler.settings.get('CREDENTIALS')
        session = boto3.session.Session()
        self.s3 = session.resource('s3', **credentials)

        # sanity check - ensure bucket exists
        try:
            response = self.s3.meta.client.list_buckets()
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                for bucket in response['Buckets']:
                    if bucket['Name'] == self.bucket_name:
                        break
                else:
                    client.create_bucket(Bucket=self.bucket_name, ACL='private')
        except Exception as e:
            print(f'Error initializing storage: {str(e)}')
            crawler._signal_shutdown(9, 0)

    def _upload_file(self, file_path, object_path, content_type):

        if self.bucket_name is not None:
            obj = self.s3.Object(self.bucket_name, object_path)
            if not object_exists(obj, file_path):
                with open(file_path, 'rb') as f:
                    obj.put(Body = f, ContentType = content_type)
        else:
            os.link(file_path, os.path.join(self.basedir, 'files', object_path))

    def process_audio_file(self, item):

        mp3file_path = os.path.join(self.files_store, item['files'][0]['path'])

        # Update MP3 tags
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

        # upload file
        self._upload_file(mp3file_path, os.path.join('audio', f'{item["slug"]}.mp3'), 'audio/mpeg')

    def process_image_files(self, item):

        image_file_path = item['images'][0]['path']
        object_name = f'{item["slug"]}.jpg'

        image_local_path = os.path.join(self.images_store, image_file_path)
        self._upload_file(image_local_path, os.path.join('images', object_name), 'image/jpeg')

        thumbnail_local_path = os.path.join(self.images_store, 'thumbs', image_file_path.replace('full', 'small'))
        self._upload_file(thumbnail_local_path, os.path.join('images', 'thumbnails', object_name), 'image/jpeg')

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
            self.process_image_files(item)
            self.persist(item)

            return item
        except:
            for key,val in item.items():
                item[key] = str(val)
            spider.logger.error(f'Error while processing item: {json.dumps(item)}',
                                exc_info=True)
            raise
