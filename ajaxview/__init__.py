import inspect
import json
import logging
from datetime import datetime

from django.http import JsonResponse, HttpRequest
from django.template.context_processors import csrf
from django.template.loader import render_to_string
from django.views.generic import TemplateView

from . import exceptions


def ajax(fn):
    fn.is_ajax = True
    return fn


class AjaxViewMeta(type):
    def __new__(cls, name, bases, dct):
        class_instance = super().__new__(cls, name, bases, dct)

        ajax_methods = {}
        ajax_methods_js = {}  # Handy for rendering in templates
        ajax_datetime_params = {}

        # Load stuff from super-classes
        for base_class in bases:
            if hasattr(base_class, 'ajax_methods'):
                ajax_methods.update(base_class.ajax_methods)
            if hasattr(base_class, 'ajax_methods_js'):
                ajax_methods_js.update(base_class.ajax_methods_js)
            if hasattr(base_class, 'ajax_datetime_params'):
                ajax_datetime_params.update(base_class.ajax_datetime_params)

        for k, v in dct.items():
            if callable(v) and getattr(v, 'is_ajax', False):
                sig = inspect.signature(v)
                args = list(sig.parameters.keys())
                if args[0] == 'self' or args[0] == 'cls':
                    args = args[1:]
                ajax_methods[k] = args
                ajax_datetime_params[k] = []
                ajax_methods_js[k] = ','.join(args)
                for arg, param in sig.parameters.items():
                    if param.annotation is datetime:
                        ajax_datetime_params[k].append(arg)

        class_instance.ajax_methods = ajax_methods
        class_instance.ajax_methods_js = ajax_methods_js
        class_instance.ajax_datetime_params = ajax_datetime_params
        return class_instance


class AjaxView(TemplateView, metaclass=AjaxViewMeta):
    ajax_function_name = 'ajax'
    ClientError = exceptions.ClientError

    def get_logger(self):
        return logging

    def get_context_data(self, **kwargs):
        kwargs.setdefault('ajax_view', self.render_page_head())
        return super().get_context_data(**kwargs)

    def render_bad_request(self, error):
        return JsonResponse({
            'response_type': 'invalid-request',
            'errors': [error]
        }, status=400)

    def render_client_error(self, exception_instance):
        error = exception_instance.args

        return JsonResponse({
            'response_type': 'client-error',
            'errors': list(error)
        }, status=400)

    def render_server_error(self, exception_instance):
        return JsonResponse({
            'response_type': 'server-error',
        }, status=500)

    def render_user_response(self, return_value):
        return JsonResponse(data={
            'response_type': 'complete',
            'return_value': return_value
        })

    def render_page_head(self):
        context = dict(
            csrf_token=csrf(self.request)['csrf_token'],
            ajax_function_name=self.ajax_function_name,
            methods=self.ajax_methods_js
        )

        return render_to_string('ajax_headers.html', context)

    def post(self, request: HttpRequest, *args, **kwargs):
        try:
            input_data = json.loads(request.body)
        except:
            return self.render_bad_request('Cannot parse JSON body')

        func = input_data.get('func', None)
        arguments = input_data.get('args', None)

        if not func:
            return self.render_bad_request('No func specified')

        if arguments is None:
            return self.render_bad_request('No args specified')

        if not isinstance(arguments, dict):
            return self.render_bad_request('args must be dict')

        # Convert any datetimes
        if func in self.ajax_datetime_params:
            for k, v in arguments.copy().items():
                if k in self.ajax_datetime_params[func]:
                    arguments[k] = datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%fZ')

        if func in self.ajax_methods:
            try:
                data = getattr(self, func)(**arguments)
            except self.ClientError as e:
                return self.render_client_error(e)
            except Exception as e:
                self.get_logger().exception(f'Error processing {func}')
                return self.render_server_error(e)
            else:
                return self.render_user_response(data)
        else:
            return self.render_bad_request(f'No such ajax function: {func}')

__all__ = ['AjaxView', 'ajax']
