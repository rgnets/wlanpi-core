import json
import logging
import re

from wlanpi_core.models.command_result import CommandResult
from wlanpi_core.services.network.namespace.models.network_namespace_errors import NetworkNamespaceNotFoundError, \
    NetworkNamespaceError
from wlanpi_core.utils.general import run_command

# log = logging.getLogger("uvicorn")

class NetworkNamespace():
    _logger = logging.getLogger("NetworkNamespace")
    def __init__(self, name: str ):
        # super().__init__(error_msg)

        self.name = name

    @staticmethod
    def create(name: str) -> CommandResult:
        """
        Attempts to create a network namespace
        """
        return run_command(f"ip -j netns add {name}".split())

    @staticmethod
    def list_namespaces() -> list:
        """ Lists all known network namespaces """
        result = run_command(f"ip -j netns list".split(), raise_on_fail=False)
        if not result.success:
            raise NetworkNamespaceError(f"Error listing namespaces: {result.error}")
        return result.output_from_json() or []

    @staticmethod
    def namespace_exists(name: str) -> bool:
        namespaces = NetworkNamespace.list_namespaces()
        return name in [ns['name'] for ns in namespaces]

    @staticmethod
    def get_interfaces_in_namespace(name: str) -> list:
        return run_command(f"ip netns exec {name} jc ifconfig -a".split()).output_from_json()

    @staticmethod
    def destroy_namespace(namespace_name: str):
        if not NetworkNamespace.namespace_exists(namespace_name):
            raise NetworkNamespaceNotFoundError()
        NetworkNamespace._logger.info(f"Asked to destroy namespace {namespace_name}")
        NetworkNamespace._logger.info(f"Killing old processes in {namespace_name}")

        # This particular subcommand doesn't support JSON mode.
        pids = run_command(f"ip netns pids {namespace_name}".split()).output.split("\n")
        pids = list(filter(None, pids))

        for pid in pids:
            NetworkNamespace._logger.info(f"Killing process {pid}")
            res = run_command(f"ip netns exec {namespace_name} kill {pid}".split(), raise_on_fail=False)
            if not res.success:
                raise NetworkNamespaceError(f"Failed to kill process {pid} while destroying namespace {namespace_name}")

        NetworkNamespace._logger.info(f"Moving interfaces out of {namespace_name}")

        for interface in NetworkNamespace.get_interfaces_in_namespace(namespace_name):
            print(interface)
            NetworkNamespace._logger.info(f"Moving interface {interface} out of {namespace_name}")


            if interface['name'].startswith('wlan'):
                # Get phy num of interface
                res = run_command(f"ip netns exec {namespace_name} iw dev {interface['name']} info".split())
                phynum = re.findall( r'wiphy ([0-9]+)', res.output)[0]
                phy = f"phy{phynum}"

                res = run_command(f"ip netns exec {namespace_name} iw phy {phy} set netns 1".split(),
                                  raise_on_fail=False)
                if not res.success:
                    raise NetworkNamespaceError(f"Failed to move wireless interface {interface['name']} to default namespace: {res.error}")

            elif interface['name'].startswith('eth'):
                res = run_command(f"ip netns exec {namespace_name} ip link set '{interface['name']}' netns 1".split(),
                                  raise_on_fail=False)
                if not res.success:
                    raise NetworkNamespaceError(f"Failed to move wired interface {interface['name']} to default namespace: {res.error}")

            elif interface['name'].startswith('lo'):
                NetworkNamespace._logger.info(f"Ignoring loopback interface {interface['name']}")
            else:
                raise NetworkNamespaceError(f"Don't know how to move {interface['name']} to default namespace.")

        NetworkNamespace._logger.info(f"Deleting namespace {namespace_name}")
        res = run_command(f"ip netns del {namespace_name}".split(),
                          raise_on_fail=False)
        if not res.success:
            raise NetworkNamespaceError(f"Unable to destroy namespace {namespace_name} {res.error}")

    @staticmethod
    def processes_using_namespace(namespace_name: str):
        result = run_command(f"ip netns pids {namespace_name}".split(), raise_on_fail=False)
        if not result.success:
            raise NetworkNamespaceError(f"Error getting namespace processes: {result.error}")
        return list(filter(None, result.output.split('\n') or []))
