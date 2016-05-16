#!/usr/bin/env python
"""mockups.py - Testing mockups
"""
from StringIO import StringIO
from copy import deepcopy
import mock
import pytest

from fabric.state import env


class FabricMock(mock.MagicMock):
    """A Mock object that also records the state of the fabric 'env' when it is
    called
    """
    def __init__(self, *args, **kwargs):
        """All arguments are passed to MagickMock()"""
        super(FabricMock, self).__init__(*args, **kwargs)
        self.call_env_list = []
        self.call_env = None

    def __call__(_mock_self, *args, **kwargs):
        """Record env before passing call to superclass"""
        newenv = deepcopy(env)
        _mock_self.call_env_list.append(newenv)
        _mock_self.call_env = newenv
        return super(FabricMock, _mock_self).__call__(*args, **kwargs)

    def reset_mock(self):
        """Reset mock state"""
        self.call_env_list = []
        self.call_env = None
        return super(FabricMock, self).reset_mock()


class CTXStringIO(StringIO):
    """A version of StringIO which is also a context manager so it can simulate
    'file'"""
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def open_mockup(file_dict, ns='__builtin__'):
    """Mockup the open builtin (only for file reads)

    :param Mapping file_dict: A mapping from file names to file content to
                              simulate for the opened file, or an exception to
                              raise when trying to open it. Any file being
                              opened which is not in this dict will raise a "No
                              such file" excpetion.
    :param str ns:            The namespace to patch the 'open' function in, by
                              default it would be '__builtin__'
    :rtype: mock.patcher
    :returns: A patcher object that patches the open function
    """
    def _open(name, mode=None, buffering=None):
        content = file_dict.get(
            name,
            IOError(2, "No such file or directory: '{0}'".format(name))
        )
        if isinstance(content, BaseException):
            raise content
        return CTXStringIO(content)

    return mock.patch('.'.join((ns, 'open')), side_effect=_open)


def mockup_to_fixture(mockup_patcher):
    """Convert a mock-sytle mockup to a pytest fixture

    :param object mockup_patcher: A context manager to patch and unpatch
                                  objects as needed by the mockup
    :rtype: Callable
    :returns: A pytest fixture function that will setup and return the mockup
              when called, and tear it down when the test ends
    """
    @pytest.fixture
    def fixture(request):
        def finalizer():
            mockup_patcher.__exit__(None, None, None)

        request.addfinalizer(finalizer)
        return mockup_patcher.__enter__()

    return fixture
