import json
import logging
from datetime import datetime, timedelta

from django.test import TestCase, RequestFactory


class TestAjaxView(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()

    def get_controller(self, suppress_logging=False):
        from ajaxview import AjaxView, ajax

        # Avoid printing traceback to log, since it's expected
        import logging
        if suppress_logging:
            logger = logging.Logger('test')
            logger.setLevel(100)
        else:
            logger = logging

        class MyAjaxController(AjaxView):
            def get_logger(self):
                return self.logger

            @ajax
            def sum_numbers(self, numbers):
                return sum(numbers)

            @ajax
            def sum_numbers_server_error(self, numbers):
                raise ValueError('I suck')

            @ajax
            def sum_numbers_client_error(self, numbers):
                raise self.ClientError('You suck')

            @ajax
            def add_days(self, when: datetime, days):
                return when + timedelta(days=days)

        MyAjaxController.logger = logger
        return MyAjaxController

    def test_rendering(self):
        MyAjaxController = self.get_controller()

        ct = MyAjaxController(request=self.factory.get('/test'))
        self.assertTrue(ct.get_context_data()['ajax_view'].strip().startswith('<script>'))

    def test_working_function(self):
        """
        Just tests that the working function is there
        """
        self.assert_call_result('sum_numbers', {'numbers': [1, 2, 3]}, 200, {
            'response_type': 'complete',
            'return_value': 6
        })

    def test_bad_request_missing_args(self):
        MyAjaxController = self.get_controller()

        ct = MyAjaxController(request=self.factory.get('/test'))
        request = self.factory.post('/test', {
            'func': 'sum_numbers',
        }, content_type='application/json')
        response = ct.post(request=request)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['response_type'], 'invalid-request')
        self.assertEqual(data['errors'], ['No args specified'])

        request = self.factory.post('/test', {
            'args': {'numbers': [1, 2, 3]}
        }, content_type='application/json')

        response = ct.post(request=request)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['response_type'], 'invalid-request')
        self.assertEqual(data['errors'], ['No func specified'])

    def test_client_error(self):
        self.assert_call_result('sum_numbers_client_error', {'numbers': [1, 2, 3]}, 400, {
            'response_type': 'client-error',
            'errors': ['You suck']
        })

    def test_server_error(self):
        self.assert_call_result('sum_numbers_server_error', {'numbers': [1, 2, 3]}, 500, {
            'response_type': 'server-error'
        }, suppress_logging=True)

    def test_no_such_function(self):
        self.assert_call_result('does_not_exist', {'foo': 'bar'}, 400, {
            'response_type': 'invalid-request',
            'errors': ['No such ajax function: does_not_exist']
        })

    def test_positional_args(self):
        self.assert_call_result('sum_numbers', [1, 2, 3], 400, {
            'response_type': 'invalid-request',
            'errors': ['args must be dict']
        })

    def test_not_json(self):
        MyAjaxController = self.get_controller()

        request = self.factory.post('/test', 'your mom uses Linux', content_type='application/json')
        ct = MyAjaxController(request=request)
        response = ct.post(request=request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['response_type'], 'invalid-request')
        self.assertEqual(data['errors'], ['Cannot parse JSON body'])

    def test_datetime_serialization(self):
        self.assert_call_result('add_days', {'when': '2020-12-14T00:45:08.651Z', 'days': 5}, 200, {
            'response_type': 'complete',
            'return_value': '2020-12-19T00:45:08.651'
        })

    def assert_call_result(self, function_name, function_args, http_status, data_values, suppress_logging=False):
        MyAjaxController = self.get_controller(suppress_logging=suppress_logging)

        request = self.factory.post('/test', {
            'args': function_args,
            'func': function_name,
        }, content_type='application/json')

        ct = MyAjaxController(request=request)
        response = ct.post(request=request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, http_status)
        for k, v in data_values.items():
            self.assertEqual(data[k], v)

    def test_get_logging(self):
        from ajaxview import AjaxView

        class MyAjaxController(AjaxView):
            pass

        ct = MyAjaxController()
        logger = ct.get_logger()
        assert logger is logging
