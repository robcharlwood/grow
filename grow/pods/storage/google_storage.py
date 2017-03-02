try:
    import cloudstorage
    from cloudstorage import cloudstorage_api
except ImportError:
    # Not running in GAE runtime.
    cloudstorage = None

try:
    from google.appengine.ext import blobstore
except ImportError:
    blobstore = None

import os
import jinja2
import logging
import mimetypes
from grow.pods.storage import base_storage
from grow.pods.storage import errors


class CloudStorage(base_storage.BaseStorage):

    is_cloud_storage = True

    @staticmethod
    def open(filename, *args, **kwargs):
        if 'mode' in kwargs:
            # cloudstorage doesnt differentiate between reading standard files
            # and binary files and throws an exception - so if we are passed
            # rb then we just convert to r.
            if kwargs['mode'] is None or kwargs['mode'] == 'rb':
                kwargs['mode'] = 'r'
        try:
            return cloudstorage.open(filename, *args, **kwargs)
        except cloudstorage.NotFoundError:
            logging.error(filename)
            raise IOError('File {} not found.'.format(filename))

    @staticmethod
    def read(filename):
        try:
            return cloudstorage.open(filename).read()
        except cloudstorage.NotFoundError as e:
            logging.error(filename)
            raise IOError(str(e))

    @staticmethod
    def modified(filename):
        try:
            return cloudstorage.stat(filename).st_ctime
        except cloudstorage.NotFoundError:
            logging.error(filename)
            raise IOError('File {} not found.'.format(filename))

    @staticmethod
    def stat(filename):
        try:
            return cloudstorage.stat(filename)
        except cloudstorage.NotFoundError:
            raise IOError('File {} not found.'.format(filename))

    @staticmethod
    def listdir(filename, recursive=True):
        bucket, prefix = filename[1:].split('/', 1)
        bucket = '/' + bucket
        names = set()
        page_size = 20
        items = cloudstorage.listbucket(
            bucket, prefix=prefix, max_keys=page_size)
        while True:
            count = 0
            for item in items:
                count += 1
                name = item.filename[len(bucket) + len(prefix) + 1:]
                if name and (recursive or '/' not in name):
                    names.add(name)
            if count != page_size or count == 0:
                break
            items = cloudstorage.listbucket(
                bucket, prefix=prefix, max_keys=page_size,
                marker=item.filename)
        return list(names)

    @staticmethod
    def JinjaLoader(path):
        path = CloudStorage.normalize_path(path)
        return CloudStorageLoader(path)

    @staticmethod
    def normalize_path(path):
        if '..' in path:
            raise errors.PathError('".." not allowed in path: {}'.format(path))
        if not path.startswith('/'):
            return '/' + path
        return path

    @classmethod
    def write(cls, path, content, options=None, content_type=None):
        if isinstance(content, unicode):
            content = content.encode('utf-8')
        path = cls.normalize_path(path)
        ctype = content_type or mimetypes.guess_type(path)[0] or 'text/html'
        file_obj = cls.open(
            path, mode='w', options=options, content_type=ctype)
        file_obj.write(content)
        file_obj.close()
        return file_obj

    @classmethod
    def delete(cls, path):
        path = CloudStorage.normalize_path(path)
        try:
            cloudstorage.delete(path)
        except cloudstorage.NotFoundError:
            logging.error(path)
            raise IOError('File {} not found.'.format(path))

    @staticmethod
    def exists(filename):
        try:
            cloudstorage.stat(filename)
            return True
        except cloudstorage.NotFoundError:
            return False

    @staticmethod
    def copy_to(path, target_path):
        # TODO(jeremydw): Replace
        return cloudstorage_api._copy2(path, target_path)

    @staticmethod
    def move_to(path, target_path):
        CloudStorage.copy_to(path, target_path)
        cloudstorage.delete(path)

    @staticmethod
    def update_headers(headers, path):
        if blobstore is None:
            raise Exception('Cannot use blobstore outside App Engine environment.')
        blob_key = blobstore.create_gs_key('/gs' + path)
        headers['X-AppEngine-BlobKey'] = blob_key


class CloudStorageLoader(jinja2.BaseLoader):

    def __init__(self, path):
        self.path = path

    def get_source(self, environment, template):
        path = os.path.join(self.path, template.lstrip('/'))
        try:
            source = CloudStorage.read(path)
        # Our CloudStorage class methods raise an IOError rather than the 
        # cloudstorage default of NotFoundError. We do this for compatibility
        # with the rest of the code base which always assumes files are being 
        # read and written to from real / local disk space. So catch IOError instead
        except IOError:
            raise jinja2.TemplateNotFound(template)
        # TODO(jeremydw): Make this function properly.
        source = source.decode('utf-8')
        return source, path, lambda: True
#    return source, path, lambda: mtime == CloudStorage.modified(path)
