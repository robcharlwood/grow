from . import utils
from grow.common import sdk_utils
from grow.testing import testing
import copy
import mock
import semantic_version
import unittest


class UtilsTestCase(unittest.TestCase):

    def test_walk(self):
        data = {
          'foo': 'bar',
          'bam': {
            'foo': 'bar2',
            'foo2': ['bar3', 'bar4'],
          }
        }
        expected = {
          'foo3': 'bar',
          'bam3': {
            'foo3': 'bar2',
            'foo23': ['bar3', 'bar4'],
          }
        }
        def callback(key):
          return key + '3'
        utils.update_keys_in_structure(data, callback)
        print 'expected', expected
        print 'actual', data
        self.assertDictEqual(expected, data)

#    def test_walk(self):
#        data = {
#          'foo': 'bar',
#          'bam': {
#            'foo': 'bar2',
#            'foo2': ['bar3', 'bar4'],
#          }
#        }
#
#        actual = []
#        def callback(node, key):
#            if isinstance(node, dict):
#                if isinstance(node[key], basestring):
#                    actual.append(node[key])
#            else:
#                print 'node', node
#                for item in node:
#                    actual.append(key)
#        utils.walk(data, callback)
#
#        expected = ['bar', 'bar2', 'bar3', 'bar4']
#        print 'expected', expected
#        print 'actual', actual
#        self.assertItemsEqual(expected, actual)

    def test_parse_yaml(self):
        pod = testing.create_test_pod()
        content = pod.read_file('/data/constructors.yaml')
        result = utils.parse_yaml(content, pod=pod)
        doc = pod.get_doc('/content/pages/home.yaml')
        self.assertEqual(doc, result['doc'])
        expected_docs = [
            pod.get_doc('/content/pages/home.yaml'),
            pod.get_doc('/content/pages/about.yaml'),
            pod.get_doc('/content/pages/home.yaml'),
        ]
        self.assertEqual(expected_docs, result['docs'])

    def test_version_enforcement(self):
        with mock.patch('grow.pods.pods.Pod.grow_version',
                        new_callable=mock.PropertyMock) as mock_version:
            this_version = sdk_utils.get_this_version()
            gt_version = '>{0}'.format(semantic_version.Version(this_version))
            mock_version.return_value = gt_version
            with self.assertRaises(sdk_utils.LatestVersionCheckError):
                testing.create_test_pod()

    def test_untag_fields(self):
        fields_to_test = {
            'title': 'value-none',
            'title@fr': 'value-fr',
            'list': [
                {
                    'list-item-title': 'value-none',
                    'list-item-title@fr': 'value-fr',
                },
            ],
            'nested': {
                'nested-title@': 'value-none',
            },
            'nested-fr': {
                'nested-title@': 'value-fr',
            },
            'list@de': [
                'list-item-de',
            ]
        }
        fields = copy.deepcopy(fields_to_test)
        self.assertDictEqual({
            'title': 'value-fr',
            'list': [{'list-item-title': 'value-fr'},],
            'nested': {'nested-title': 'value-fr',},
        }, utils.untag_fields(fields, locale='fr'))
        fields = copy.deepcopy(fields_to_test)
        self.assertDictEqual({
            'title': 'value-none',
            'list': ['list-item-de',],
            'nested': {'nested-title': 'value-none',},
        }, utils.untag_fields(fields, locale='de'))


if __name__ == '__main__':
    unittest.main()
