import logging
import time
import glob
import os
import re
import socket
import traceback

from avocado.core import exceptions

from utils_misc import *
from . import remote
from . import data_dir
from . import utils_misc

class BaseVM(object):

    """
    Base class for ASM and ARM VM subclasses.

    This class should not be used directly, that is, do not attempt to
    instantiate and use this class. Instead, one should implement a subclass
    that implements, at the very least, all methods defined right after the
    the comment blocks that are marked with:

    "Public API - *must* be reimplemented with Azure specific code"

    and

    "Protected API - *must* be reimplemented with Azure specific classes"

    The current proposal regarding methods naming convention is:

    - Public API methods: named in the usual way, consumed by tests
    - Protected API methods: name begins with a single underline, to be
      consumed only by BaseVM and subclasses
    - Private API methods: name begins with double underline, to be consumed
      only by the VM subclass itself (usually implements Azure specific
      functionality)

    So called "protected" methods are intended to be used only by VM classes,
    and not be consumed by tests. Theses should respect a naming convention
    and always be preceded by a single underline.

    Currently most (if not all) methods are public and appears to be consumed
    by tests. It is a ongoing task to determine whether  methods should be
    "public" or "protected".
    """

    #
    # Timeout definition. This is being kept inside the base class so that
    # sub classes can change the default just for themselves
    #
    DEFAULT_TIMEOUT = 240
    LOGIN_TIMEOUT = 30
    LOGIN_WAIT_TIMEOUT = 240
    COPY_FILES_TIMEOUT = 600
    RESTART_TIMEOUT = 240
    DELETE_TIMEOUT = 240

    def __init__(self, name, size, params):
        self.name = name
        self.size = size
        self.params = params
        self.exist = False
        self.session = []

    #
    # Public API - could be reimplemented with virt specific code
    #
    
    def get_public_address(self):
        """
        Get the public IP address

        :return:
        """
        return self.params("VirtualIPAddresses")[0]("address")

    def get_ssh_port(self):
        """
        Get the ssh port

        :return:
        """
        raise NotImplementedError

    def get_params(self):
        """
        Return the VM's params dict. Most modified params take effect only
        upon VM.create().
        """
        return self.params

    def login(self, timeout=LOGIN_TIMEOUT,
              username=None, password=None):
        """
        Log into the guest via SSH.
        If timeout expires while waiting for output from the guest (e.g. a
        password prompt or a shell prompt) -- fail.

        :param timeout: Time (seconds) before giving up logging into the
                guest.
        :param username:
        :param password:
        :return: A ShellSession object.
        """
        if not username:
            username = self.params.get("username", "")
        if not password:
            password = self.params.get("password", "")
        prompt = self.params.get("shell_prompt", "[\#\$]")
        linesep = eval("'%s'" % self.params.get("shell_linesep", r"\n"))
        client = self.params.get("shell_client", "ssh")
        address = self.get_public_address()
        port = self.get_ssh_port()
        log_filename = ("session-%s-%s.log" %
                        (self.name, utils_misc.generate_random_string(4)))
        session = remote.remote_login(client, address, port, username,
                                      password, prompt, linesep,
                                      log_filename, timeout)
        session.set_status_test_command(self.params.get("status_test_command",
                                                        ""))
        self.remote_sessions.append(session)
        return session

    def remote_login(self, timeout=LOGIN_TIMEOUT,
                     username=None, password=None):
        """
        Alias for login() for backward compatibility.
        """
        return self.login(timeout, username, password)

    def copy_files_to(self, host_path, guest_path, limit="",
                      verbose=False,
                      timeout=COPY_FILES_TIMEOUT,
                      username=None, password=None):
        """
        Transfer files to the remote host(guest).

        :param host_path: Host path
        :param guest_path: Guest path
        :param limit: Speed limit of file transfer.
        :param verbose: If True, log some stats using logging.debug (RSS only)
        :param timeout: Time (seconds) before giving up on doing the remote
                copy.
        """
        logging.info("sending file(s) to '%s'", self.name)
        if not username:
            username = self.params.get("username", "")
        if not password:
            password = self.params.get("password", "")
        client = self.params.get("file_transfer_client", "ssh")
        address = self.get_public_address()
        port = self.get_ssh_port()
        log_filename = ("transfer-%s-to-%s-%s.log" %
                        (self.name, address,
                         utils_misc.generate_random_string(4)))
        remote.copy_files_to(address, client, username, password, port,
                             host_path, guest_path, limit, log_filename,
                             verbose, timeout)
        utils_misc.close_log_file(log_filename)

    def copy_files_from(self, guest_path, host_path, nic_index=0, limit="",
                        verbose=False,
                        timeout=COPY_FILES_TIMEOUT,
                        username=None, password=None):
        """
        Transfer files from the guest.

        :param host_path: Guest path
        :param guest_path: Host path
        :param limit: Speed limit of file transfer.
        :param verbose: If True, log some stats using logging.debug (RSS only)
        :param timeout: Time (seconds) before giving up on doing the remote
                copy.
        """
        logging.info("receiving file(s) to '%s'", self.name)
        if not username:
            username = self.params.get("username", "")
        if not password:
            password = self.params.get("password", "")
        client = self.params.get("file_transfer_client")
        address = self.get_public_address()
        port = self.get_ssh_port()
        log_filename = ("transfer-%s-from-%s-%s.log" %
                        (self.name, address,
                         utils_misc.generate_random_string(4)))
        remote.copy_files_from(address, client, username, password, port,
                               guest_path, host_path, limit, log_filename,
                               verbose, timeout)
        utils_misc.close_log_file(log_filename)