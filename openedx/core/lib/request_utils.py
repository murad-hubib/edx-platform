""" Utility functions related to HTTP requests """
import re
import logging
from urlparse import urlparse
import crum

from django.conf import settings
from django.core.handlers.base import BaseHandler
from django.test.client import RequestFactory

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

log = logging.getLogger(__name__)

# accommodates course api urls, excluding any course api routes that do not fall under v*/courses, such as v1/blocks.
COURSE_REGEX = re.compile(r'^(.*?/courses/)(?!v[0-9]+/[^/]+){}'.format(settings.COURSE_ID_PATTERN))


def get_request_or_stub():
    """
    Return the current request or a stub request.

    If called outside the context of a request, construct a fake
    request that can be used to build an absolute URI.

    This is useful in cases where we need to pass in a request object
    but don't have an active request (for example, in tests, celery tasks, and XBlocks).
    """
    request = crum.get_current_request()

    if request is None:

        # The settings SITE_NAME may contain a port number, so we need to
        # parse the full URL.
        full_url = "http://{site_name}".format(site_name=settings.SITE_NAME)
        parsed_url = urlparse(full_url)

        # Construct the fake request.  This can be used to construct absolute
        # URIs to other paths.
        return RequestFactory(
            SERVER_NAME=parsed_url.hostname,
            SERVER_PORT=parsed_url.port or 80,
        ).get("/")

    else:
        return request


def safe_get_host(request):
    """
    Get the host name for this request, as safely as possible.

    If ALLOWED_HOSTS is properly set, this calls request.get_host;
    otherwise, this returns whatever settings.SITE_NAME is set to.

    This ensures we will never accept an untrusted value of get_host()
    """
    if isinstance(settings.ALLOWED_HOSTS, (list, tuple)) and '*' not in settings.ALLOWED_HOSTS:
        return request.get_host()
    else:
        return configuration_helpers.get_value('site_domain', settings.SITE_NAME)


def course_id_from_url(url):
    """
    Extracts the course_id from the given `url`.
    """
    if not url:
        return None
    # Ignore query string
    url = url.split('?')[0]

    match = COURSE_REGEX.match(url)

    if match is None:
        return None

    course_id = match.group('course_id')

    if course_id is None:
        return None

    try:
        return CourseKey.from_string(course_id)
    except InvalidKeyError:
        log.warning(
            'unable to parse course_id "{}"'.format(course_id),
            exc_info=True
        )
        return None


class RequestMock(RequestFactory):
    """
    RequestMock is used to create generic/dummy request objects in
    scenarios where a regular request might not be available for use
    """
    def request(self, **request):
        "Construct a generic request object."
        request = RequestFactory.request(self, **request)
        handler = BaseHandler()
        handler.load_middleware()
        for middleware_method in handler._request_middleware:
            if middleware_method(request):
                raise Exception("Couldn't create request mock object - "
                                "request middleware returned a response")
        return request


class RequestMockWithoutMiddleware(RequestMock):
    """
    RequestMockWithoutMiddleware is used to create generic/dummy request
    objects in scenarios where a regular request might not be available for use.
    It's similiar to its parent except for the fact that it skips the loading
    of middleware.
    """
    def request(self, **request):
        "Construct a generic request object."
        request = RequestFactory.request(self, **request)
        if not hasattr(request, 'session'):
            request.session = {}
        return request
