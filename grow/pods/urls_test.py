from . import errors
from . import urls
from grow.pods import pods
from grow.testing import testing
import os
import unittest


class UrlTest(unittest.TestCase):

    def setUp(self):
        dir_path = testing.create_test_pod_dir()
        self.pod = pods.Pod(dir_path)

    def test_string(self):
        path = '/foo/'
        url = urls.Url(path, host=None)
        self.assertRaises(urls.UrlValueError, str, url)
        self.assertEqual('/foo/', url.path)
        url = urls.Url(path, host='example.com')
        self.assertEqual('http://example.com/foo/', str(url))

        # Verify default environment behavior.
        pod = testing.create_pod()
        pod.write_yaml('/podspec.yaml', {})
        pod.write_yaml('/content/pages/_blueprint.yaml', {
            '$view': '/views/base.html',
            '$path': '/{base}/',
        })
        pod.write_yaml('/content/pages/foo.yaml', {})
        pod.write_file('/views/base.html', '{{doc.url}}')
        controller, params = pod.match('/foo/')

        # Verify error raised when no host is set.
        try:
            content = controller.render(params)
        except errors.BuildError as e:
            self.assertTrue(isinstance(e.exception, urls.UrlValueError))

        # Verify no error is raised when host correctly set.
        pod.env.host = 'example.com'
        content = controller.render(params)
        self.assertEqual('http://example.com/foo/', content)

    def test_relative_path(self):
        relative_path = urls.Url.create_relative_path(
            '/foo/bar/baz/', relative_to='/test/dir/')
        self.assertEqual('../../foo/bar/baz/', relative_path)

        relative_path = urls.Url.create_relative_path(
            '/foo/bar/baz/', relative_to='/test/dir/foo/')
        self.assertEqual('../../../foo/bar/baz/', relative_path)

        relative_path = urls.Url.create_relative_path(
            '/', relative_to='/test/dir/foo/')
        self.assertEqual('../../../', relative_path)

        relative_path = urls.Url.create_relative_path(
            '/foo/bar/', relative_to='/')
        self.assertEqual('./foo/bar/', relative_path)

        relative_path = urls.Url.create_relative_path(
            '/foo/bar/', relative_to='/foo/')
        self.assertEqual('./bar/', relative_path)

        relative_path = urls.Url.create_relative_path(
            'http://www.example.com/', relative_to='/foo/')
        self.assertEqual('http://www.example.com/', relative_path)

        relative_path = urls.Url.create_relative_path(
            'https://www.example.com/', relative_to='/foo/')
        self.assertEqual('https://www.example.com/', relative_path)

        url = urls.Url('/foo/')
        relative_path = urls.Url.create_relative_path(
            url, relative_to='/foo/')
        self.assertEqual('./', relative_path)

        url = urls.Url('/foo/test.html')
        relative_path = urls.Url.create_relative_path(
            url, relative_to='/foo/')
        self.assertEqual('./test.html', relative_path)

        url = urls.Url('/test.html')
        relative_path = urls.Url.create_relative_path(
            url, relative_to='/foo/')
        self.assertEqual('../test.html', relative_path)


if __name__ == '__main__':
    unittest.main()
