#!/usr/bin/env python
#
from functools import wraps

from ovirtsdk.api import API as oVirtApi
from ovirtsdk.infrastructure.errors import RequestError as oVirtReqErr

from fabric.api import env
from fabric.utils import abort
from fabric_ovirt.lib.utils import TTY, puts


def input_if_tty(prompt, err_msg):
    """
    Propmet for a value if we have TTY, otherwise print an error message

    :param str prompt: Prompt to show when we have TTY
    :param str err_msg: Error to show when there is no TTY

    :returns: The value we got from the user
    :rtype: str
    """
    if TTY:
        return raw_input(prompt)
    else:
        abort(err_msg)


def get_from_env_or_input(key, prompt, err_msg):
    """
    Get a value from 'env' or prompt for it if its not there and we have a TTY
    If we got a value from the user, we store it in 'env' for the next time the
    function is called

    :param str key: Ket for the value in 'env'
    :param str prompt: Prompt to show when we have TTY
    :param str err_msg: Error to show when there is no TTY

    :returns: The value we got
    :rtype: str
    """
    return (
        env.get(key)
        or env.setdefault(key, input_if_tty(prompt=prompt, err_msg=err_msg))
    )


def ovirt_defaults(func):
    """
    Decorator to pass the defaults oVirt credentails to the function

    All the default params will be passed as keyword arguments. positional
    arguments will be respected
    """
    @wraps(func)
    def newfunc(*args, **kwargs):
        kwargs['ovirt_engine'] = (
            kwargs.get('ovirt_engine')
            or get_from_env_or_input(
                key='OVIRT_ENGINE',
                prompt='oVirt engine URL: ',
                err_msg='Please provide OVIRT_ENGINE inside the febricrc file.'
            )
        )
        kwargs['ovirt_user'] = (
            kwargs.get('ovirt_user')
            or get_from_env_or_input(
                key='OVIRT_USER',
                prompt='oVirt username: ',
                err_msg='Please provide OVIRT_USER inside the febricrc file.'
            )
        )
        kwargs['ovirt_pass'] = (
            kwargs.get('ovirt_pass')
            or get_from_env_or_input(
                key='OVIRT_PASS',
                prompt='oVirt password: ',
                err_msg='Please provide OVIRT_PASS inside the febricrc file.'
            )
        )
        kwargs.setdefault(
            'ovirt_insecure',
            env.setdefault('OVIRT_INSECURE', True)
        )
        return func(*args, **kwargs)
    return newfunc


def ovirt_task(func):
    """
    Decorator to take care of connecting to oVirt

    The decorated function will be passwd 1 parameter called 'ovirt' that will
    contain an already-connected oVirt API object.
    The resulting function will accept 4 named parameters for specifying
    connection details and will also fill in those arguments with default
    values from the environemnt.
    """
    @wraps(func)
    def newfunc(*args, **kwargs):
        api_params = dict(
            url=kwargs.pop('ovirt_engine'),
            username=kwargs.pop('ovirt_user'),
            password=kwargs.pop('ovirt_pass'),
            insecure=kwargs.pop('ovirt_insecure'),
        )
        if (
            'ovirt_connection' not in env or
            env.ovirt_connection_params != api_params
        ):
            try:
                env.ovirt_connection = oVirtApi(**api_params)
            except oVirtReqErr as e:
                abort(
                    "Failed to connect to oVirt\nstatus={0}\nreason={1}"
                    .format(e.status, e.reason)
                )
            env.ovirt_connection_params = api_params
        kwargs['ovirt'] = env.ovirt_connection
        return func(*args, **kwargs)

    return ovirt_defaults(newfunc)


class oVirtObjectType(object):
    """Class for desbribing oVirt object types and performing generic operations
    on them
    """
    @classmethod
    def add_type(cls, ootype):
        """Collect instances of this class in a dict keyed by name

        :param oVirtObjectType ootype: an instance
        """
        if not hasattr(cls, 'all_types'):
            cls.all_types = dict()
        cls.all_types[ootype.name] = ootype

    def __init__(self, name, plural, fields=None, default_fields=None):
        """
        Initialize an oVirt object type descriptor

        :param str name: The name of the oVirt object type
        :param str plural: The plural form of the object type name, will be
                           used to look for apropriate functions in the oVirt
                           API
        :param dict fields: A mapping of object field names to text table cell
                            width needed to show values of the field
        :param str default_fields: A colon separated ordered list of fileds
                                   that will be shown if the user doesn't
                                   explicitly specify others
        """
        self.name = name
        self.plural = plural
        self.fields = fields or dict(id=36, name=40)
        self.default_fields = default_fields or 'id:name'
        self.add_type(self)

    def print_table(self, obj_list, show=None, headers='yes'):
        """
        Print a table of oVirt objects of the type from the passed list

        :param iterable obj_list: The list of objects to print as a talbe
        :param str show: A colon (:) separated list of object fields to show,
                         will fallback to self.default_fields if unspecified

        See the 'query' task for description of other parameters
        """
        show = show or self.default_fields
        format_str = ' '.join(
            '{{{0}:{1}}}'.format(field, max(self.fields[field], len(field)))
            for field in show.split(':')
            if field in self.fields
        )
        if headers == 'yes':
            puts(format_str.format(
                **dict((field, field.upper()) for field in self.fields)
            ).rstrip())
        for obj in obj_list:
            puts(format_str.format(
                **dict((field, getattr(obj, field)) for field in self.fields)
            ).rstrip())

    def _get_obj_attr(self, obj, field):
        """
        Get an attribute of an oVirt object
        """
        if hasattr(obj, field):
            return getattr(obj, field)
        elif hasattr(obj, 'get_' + field):
            return getattr(obj, 'get_' + field)()

    def query(self, ovirt, oquery):
        """
        Query oVirt for objects of the type

        :param oVirtApi ovirt: a connected oVirt API object
        :param str oquery: a query string to pass to oVirt

        :returns: a List of oVirt obejcts matching the query
        :rtype: list
        """
        obj_api = getattr(ovirt, self.plural)
        return obj_api.list(oquery)


oVirtObjectType(
    name='vm', plural='vms',
    fields=dict(id=36, name=40, memory=11),
    default_fields='id:name:memory',
)
oVirtObjectType(
    name='template', plural='templates',
    fields=dict(id=36, name=40, memory=11),
    default_fields='id:name:memory',
)
oVirtObjectType(
    name='disk', plural='disks',
    fields=dict(
        id=36, name=40, format=8, type_=8, interface=8, size=15,
        provisioned_size=15,
    ),
    default_fields='id:name:format:type_:interface:size',
)
oVirtObjectType(name='cluster', plural='clusters')
oVirtObjectType(name='storagedomain', plural='storagedomains')
oVirtObjectType(
    name='vmpool', plural='vmpools',
    fields=dict(id=36, name=40, size=4, prestarted_vms=4),
    default_fields='id:name:size:prestarted_vms',
)
oVirtObjectType(
    name='host', plural='hosts',
    fields=dict(id=36, name=40, address=40, memory=11, type_=8),
    default_fields='id:name:address:memory:type_',
)
