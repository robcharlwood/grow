"""Tests for Google Sheets translations."""

import unittest
import mock
from nose.plugins import skip
from grow.preprocessors import google_drive
from grow.common import oauth
from grow.pods import pods
from grow.pods import storage
from grow.testing import testing
from . import google_sheets


class GoogleSheetsTranslatorTestCase(unittest.TestCase):

    def setUp(self):
        dir_path = testing.create_test_pod_dir()
        self.pod = pods.Pod(dir_path, storage=storage.FileStorage)

    def test_upload_translations(self):
        credentials, _ = oauth.get_credentials_and_storage(
            scope=google_sheets.OAUTH_SCOPE,
            storage_key=google_drive.STORAGE_KEY)
        if not credentials:
            text = ('Skipping Google Sheets Translator test'
                    ' because we don\'t have auth keys. Run'
                    ' `grow upload_translations` or `grow download_translations`'
                    ' to acquire auth keys and re-run the test.')
            raise skip.SkipTest(text)
        translator = self.pod.get_translator('google_sheets')
        translator.upload(locales=['de'])


class GoogleSheetsTranslatorMockTestCase(unittest.TestCase):

    def _get_batch_requests(self, mocked):
        requests = []
        for args, kwargs in mocked.call_args_list:
            requests += kwargs['body']['requests']
        return requests

    def _mock_drive_service(self, create=None):
        mock_service = mock.Mock()

        mock_permissions = mock.Mock()
        mock_service.permissions.return_value = mock_permissions

        mock_permissions_create = mock.Mock()
        mock_permissions.create.return_value = mock_permissions_create

        mock_permissions_create.execute.return_value = create

        return {
            'service': mock_service,
            'permissions': mock_permissions,
            'permissions.create': mock_permissions_create,
        }

    def _mock_sheets_service(self, create=None, get=None):
        mock_service = mock.Mock()

        mock_spreadsheets = mock.Mock()
        mock_service.spreadsheets.return_value = mock_spreadsheets

        mock_batch_update = mock.Mock()
        mock_spreadsheets.batchUpdate = mock_batch_update

        mock_create = mock.Mock()
        mock_create.execute.return_value = create
        mock_spreadsheets.create.return_value = mock_create

        mock_get = mock.Mock()
        mock_get.execute.return_value = get
        mock_spreadsheets.get.return_value = mock_get

        return {
            'service': mock_service,
            'spreadsheets': mock_spreadsheets,
            'spreadsheets.batchUpdate': mock_batch_update,
            'spreadsheets.create': mock_create,
            'spreadsheets.get': mock_get,
        }

    def _setup_mocks(self, sheets_create=None, sheets_get=None):
        if sheets_create is None:
            sheets_create = {
                'spreadsheetId': '98765',
                'sheets': [
                    {
                        'properties': {
                            'sheetId': '1234',
                            'title': 'es',
                        }
                    }
                ]
            }
        if sheets_get is None:
            sheets_get = {
                'spreadsheetId': 76543,
            }

        mock_drive_service = self._mock_drive_service()
        mock_sheets_service = self._mock_sheets_service(
            create=sheets_create, get=sheets_get)

        return mock_drive_service, mock_sheets_service

    def setUp(self):
        dir_path = testing.create_test_pod_dir()
        self.pod = pods.Pod(dir_path, storage=storage.FileStorage)

    @mock.patch.object(google_sheets.GoogleSheetsTranslator, '_generate_new_sheet_id')
    @mock.patch.object(google_sheets.GoogleSheetsTranslator, '_create_service')
    @mock.patch.object(google_drive.BaseGooglePreprocessor, 'create_service')
    def test_create_sheet(self, mock_service_drive, mock_service_sheets, mock_new_sheet_id):
        mock_drive_service, mock_sheets_service = self._setup_mocks()
        mock_service_drive.return_value = mock_drive_service['service']
        mock_service_sheets.return_value = mock_sheets_service['service']
        mock_new_sheet_id.side_effect = [765, 654, 543, 432, 321]

        translator = self.pod.get_translator('google_sheets')
        translator.upload(locales=['de'])

        requests = self._get_batch_requests(
            mock_sheets_service['spreadsheets.batchUpdate'])

        # Creates the sheet.
        self.assertIn({
            'addSheet': {
                'properties': {
                    'gridProperties': {
                      'columnCount': 4,
                      'rowCount': 2,
                      'frozenColumnCount': 1,
                      'frozenRowCount': 1
                      },
                    'sheetId': 765,
                    'title': 'de'
                }
            }
        }, requests)

        # Formats the columns.
        self.assertIn({
            'updateDimensionProperties': {
                'fields': 'pixelSize',
                'range': {
                    'endIndex': 3,
                    'startIndex': 0,
                    'sheetId': 765,
                    'dimension': 'COLUMNS'
                },
                'properties': {
                    'pixelSize': 400
                }
            }
        }, requests)
        self.assertIn({
            'updateDimensionProperties': {
                'fields': 'pixelSize',
                'range': {
                    'endIndex': 4,
                    'startIndex': 3,
                    'sheetId': 765,
                    'dimension': 'COLUMNS'
                },
                'properties': {
                    'pixelSize': 200
                }
            }
        }, requests)
        self.assertIn({
            'updateDimensionProperties': {
                'fields': 'hiddenByUser',
                'range': {
                    'endIndex': 3,
                    'startIndex': 2,
                    'sheetId': 765,
                    'dimension': 'COLUMNS'
                },
                'properties': {
                    'hiddenByUser': False
                }
            }
        }, requests)

    @mock.patch.object(google_sheets.GoogleSheetsTranslator, '_create_service')
    @mock.patch.object(google_drive.BaseGooglePreprocessor, 'create_service')
    def test_update_meta(self, mock_service_drive, mock_service_sheets):
        mock_drive_service, mock_sheets_service = self._setup_mocks(sheets_get={
            'spreadsheetId': 'A1B2C3D4E5F6',
            'sheets': [{
                'properties': {
                    'title': 'de',
                    'sheetId': 765,
                },
            }]
        })
        mock_service_drive.return_value = mock_drive_service['service']
        mock_service_sheets.return_value = mock_sheets_service['service']

        translator = self.pod.get_translator('google_sheets')
        self.pod.write_yaml(translator.TRANSLATOR_STATS_PATH, {
            'google_sheets': {
                'de': {
                    'ident': 'A1B2C3D4E5F6',
                    'source_lang': 'en',
                    'uploaded': '2017-06-02T13:17:57.727879',
                    'url': 'https://docs.google.com/spreadsheets/d/A1B2C3D4E5F6#gid=12345',
                },
            },
        })
        translator.update_meta(locales=['de'])

        requests = self._get_batch_requests(
            mock_sheets_service['spreadsheets.batchUpdate'])

        # Style the header cells.
        self.assertIn({
            'repeatCell': {
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {
                            'bold': True
                        },
                        'backgroundColor': {
                            'blue': 0.933,
                            'green': 0.933,
                            'red': 0.933
                        }
                    }
                },
                'fields': 'userEnteredFormat',
                'range': {
                    'endRowIndex': 1,
                    'startRowIndex': 0,
                    'sheetId': 765,
                    'startColumnIndex': 0
                }
            }
        }, requests)

        # Wrap translations and comments.
        self.assertIn({
            'repeatCell': {
                'cell': {
                    'userEnteredFormat': {
                        'wrapStrategy': 'WRAP'
                    }
                },
                'fields': 'userEnteredFormat',
                'range': {
                    'endColumnIndex': 3,
                    'sheetId': 765,
                    'startColumnIndex': 0,
                    'startRowIndex': 1
                }
            }
        }, requests)

        # Muted syles on locations.
        self.assertIn({
            'repeatCell': {
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {
                            'foregroundColor': {
                                'blue': 0.6196,
                                'green': 0.6196,
                                'red': 0.6196
                            }
                        },
                        'wrapStrategy': 'WRAP'
                    }
                },
                'fields': 'userEnteredFormat',
                'range': {
                    'endColumnIndex': 4,
                    'sheetId': 765,
                    'startColumnIndex': 2,
                    'startRowIndex': 1
                }
            }
        }, requests)

        # Conditional formatting for missing translations.
        self.assertIn({
            'addConditionalFormatRule': {
                'index': 0,
                'rule': {
                    'ranges': [{
                        'endColumnIndex': 2,
                        'sheetId': 765,
                        'startColumnIndex': 1,
                        'startRowIndex': 1
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'BLANK'
                        },
                        'format': {
                            'backgroundColor': {
                                'blue': 0.964,
                                'green': 0.905,
                                'red': 0.929
                            }
                        }
                    }
                }
            }
        }, requests)

        # Protect source values.
        self.assertIn({
            'addProtectedRange': {
                'protectedRange': {
                    'warningOnly': True,
                    'protectedRangeId': 1000766,
                    'range': {
                        'endColumnIndex': 1,
                        'sheetId': 765,
                        'startColumnIndex': 0,
                        'startRowIndex': 1
                    },
                    'description': 'Original strings can only be edited in the source files.'
                }
            }
        }, requests)

        # Protect auto comments.
        self.assertIn({
            'addProtectedRange': {
                'protectedRange': {
                    'warningOnly': True,
                    'protectedRangeId': 1000767,
                    'range': {
                        'endColumnIndex': 3,
                        'sheetId': 765,
                        'startColumnIndex': 2,
                        'startRowIndex': 1
                    },
                    'description': 'Comment strings can only be edited in the source files.'
                }
            }
        }, requests)

        # Protect locations.
        self.assertIn({
            'addProtectedRange': {
                'protectedRange': {
                    'warningOnly': True,
                    'protectedRangeId': 1000768,
                    'range': {
                        'endColumnIndex': 4,
                        'sheetId': 765,
                        'startColumnIndex': 3,
                        'startRowIndex': 1
                    },
                    'description': 'Source strings can only be edited in the source files.'
                }
            }
        }, requests)

        # Filter View for Untranslated Strings.
        self.assertIn({
            'addFilterView': {
                'filter': {
                    'range': {
                        'endColumnIndex': 4,
                        'sheetId': 765,
                        'startColumnIndex': 0,
                        'startRowIndex': 0
                    },
                    'criteria': {
                        '1': {
                            'condition': {
                                'type': 'BLANK'
                            }
                        }
                    },
                    'filterViewId': 3300766,
                    'title': 'Untranslated Strings'
                }
            }
        }, requests)

        # Filter View for content paths.
        self.assertIn({
            'addFilterView': {
                'filter': {
                    'range': {
                        'endColumnIndex': 4,
                        'sheetId': 765,
                        'startColumnIndex': 0,
                        'startRowIndex': 0
                    },
                    'criteria': {
                        '3': {
                            'condition': {
                                'values': [{
                                    'userEnteredValue': u'/views/home.html'
                                }],
                                'type': 'TEXT_CONTAINS'
                            }
                        }
                    },
                    'filterViewId': 63754494,
                    'title': u'/views/home.html'
                }
            }
        }, requests)


if __name__ == '__main__':
    unittest.main()
