
import scrapy

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
