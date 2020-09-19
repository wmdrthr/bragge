import logging
import os

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import boto3


settings = get_project_settings()

def configure_logging():

    # ensure log directory exists
    os.makedirs(os.path.join(settings.get('BASEDIR'), 'logs'), exist_ok = True)

    # disable some logging (mostly AWS SDK debug logging)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('nose').setLevel(logging.WARNING)
    logging.getLogger('s3transfer').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


# upload logs to storage (if configured)
def upload_logs():

    bucket_name = settings.get('BUCKET_NAME')
    if bucket_name is None:
        return

    credentials = settings.get('CREDENTIALS')
    s3 = boto3.session.Session().resource('s3', **credentials)

    log_file = settings.get('LOG_FILE')
    log_obj = s3.Object(bucket_name, os.path.join('logs', os.path.basename(log_file)))
    with open(log_file, 'rb') as f:
        log_obj.put(Body = f, ContentType = 'text/plain')


def main():

    configure_logging()

    process = CrawlerProcess(settings)
    process.crawl('bragge')
    process.start()

    upload_logs()


if __name__=='__main__':

    main()
