"""HA Unified Remote Integration"""
import logging as log
from datetime import timedelta

from requests import ConnectionError

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from custom_components.unified_remote.cli.connection import Connection
from custom_components.unified_remote.cli.remotes import Remotes
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_HOSTS, CONF_NAME
from homeassistant.helpers.event import track_time_interval
from custom_components.unified_remote.cli.computer import Computer

DOMAIN = "unified_remote"
CONF_RETRY = "retry_delay"

COMPUTER_SCHEMA = vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=''): cv.string,
                    vol.Required(CONF_HOST, default="localhost"): cv.string,
                    vol.Optional(CONF_PORT, default="9510"): cv.port,
                }
            )

def computer_schema_list(value):
    if isinstance(value, list) and value != []:    
        if all(isinstance(n, COMPUTER_SCHEMA) for n in value):
            return value
    raise vol.Invalid('Not a list of computers')


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOSTS): computer_schema_list,
                vol.Optional(CONF_RETRY, default=120): int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

DEFAULT_NAME = ""

_LOGGER = log.getLogger(__name__)

REMOTE_FILE_PATH = "/config/custom_components/unified_remote/cli/remotes.yml"

try:
    REMOTES = Remotes(REMOTE_FILE_PATH)
    _LOGGER.info("Remotes loaded sucessful")
except FileNotFoundError:
    _LOGGER.error(f"Remotes file not found. Path:{REMOTE_FILE_PATH}")
# Handle with Remote parsing error.
except AssertionError as remote_error:
    _LOGGER.error(str(remote_error))
except Exception as error:
    _LOGGER.error(str(error))

COMPUTERS = []

def init_computers(hosts):
    for computer in hosts:
        name = computer.get(CONF_NAME)
        host = computer.get(CONF_HOST)
        port = computer.get(CONF_PORT)

        if name == '':
            name = host
        try:
            COMPUTERS.append(Computer(name, host, port))
        except (AssertionError, Exception):
            return False
    return True

def validate_response(response):
    """Validate keep alive packet to check if reconnection is needed"""
    out = response.content.decode("ascii")
    status = response.status_code
    flag = 0
    if status != 200:
        _LOGGER.error(
            f"Keep alive packet was failed. Status code: {status}. Response: {out}"
        )
        flag = 1
    else:
        errors = ["Not a valid connection", "No UR"]
        for error in errors:
            if error in out:
                flag = 1
                break
    if flag == 1:
        raise ConnectionError()


def setup(hass, config):
    """Setting up Unified Remote Integration"""
    # Fetching configuration entries.
    hosts = config[DOMAIN].get(CONF_HOSTS)
    retry_delay = config[DOMAIN].get(CONF_RETRY)
    if retry_delay > 120:
        retry_delay = 120

    init_computers(hosts)

    # TODO: PAREI AQUI
    def keep_alive(call):
        """Keep host listening our requests"""
        try:
            response = CONNECTION.exe_remote("", "")
            _LOGGER.debug("Keep alive packet sent")
            _LOGGER.debug(
                f"Keep alive packet response: {response.content.decode('ascii')}"
            )
            validate_response(response)
        # If there's an connection error, try to reconnect.
        except ConnectionError:
            try:
                _LOGGER.debug(f"Trying to reconnect with {host}")
                connect(host, port)
            except Exception as error:
                _LOGGER.debug(
                    f"Unable to connect with {host}. Headers: {CONNECTION.get_headers()}"
                )
                _LOGGER.debug(f"Error: {error}")
                pass

    def handle_call(call):
        """Handle the service call."""
        # Fetch service data.
        remote_name = call.data.get("remote", DEFAULT_NAME)
        remote_id = call.data.get("remote_id", DEFAULT_NAME)
        action = call.data.get("action", DEFAULT_NAME)

        # Allows user to pass remote id without declaring it on remotes.yml
        if remote_id is not None:
            if not (remote_id == "" or action == ""):
                call_remote(remote_id, action)
                return None

        # Check if none or empty service data was parsed.
        if not (remote_name == "" or action == ""):
            remote = REMOTES.get_remote(remote_name)
            # Check if remote was declared on remotes.yml.
            if remote is None:
                _LOGGER.warning(
                    f"Remote {remote_name} not found Please check your remotes.yml"
                )
                return None
            # Fetch remote id.
            remote_id = remote["id"]
            # Check if given action exists in remote control list.
            if action in remote["controls"]:
                call_remote(remote_id, action)
            else:
                # Log if called remote doens't exists on remotes.yml.
                _LOGGER.warning(
                    f'Action "{action}" doesn\'t exists for remote {remote_name} Please check your remotes.yml'
                )

    # Register remote call service.
    hass.services.register(DOMAIN, "call", handle_call)
    # Set "keep_alive()" function to be called every 2 minutes (120 seconds).
    # 2 minutes (120 seconds) are the max interval to keep connection alive.
    # So you can just decrease this delay, otherwise, the connection will not
    # be persistent.
    track_time_interval(hass, keep_alive, timedelta(seconds=retry_delay))

    return True
