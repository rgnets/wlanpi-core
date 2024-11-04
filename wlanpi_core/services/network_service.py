import logging
from enum import Enum
from typing import Optional


from wlanpi_core.models.network.wlan.exceptions import WlanDBUSException
from wlanpi_core.models.network.wlan.wlan_dbus import WlanDBUS
from wlanpi_core.models.network.wlan.wlan_dbus_interface import WlanDBUSInterface
from wlanpi_core.models.validation_error import ValidationError
from wlanpi_core.schemas import network


"""
These are the functions used to deliver the API
"""


async def get_systemd_network_interfaces(timeout: int):
    """
    Queries systemd via dbus to get a list of the available interfaces.
    """
    try:
        wlan_dbus = WlanDBUS()
        available_interfaces = wlan_dbus.get_systemd_network_interfaces(timeout=timeout)
        logging.info(f"Available interfaces: {available_interfaces}")
        return {"interfaces": available_interfaces}
    except WlanDBUSException as err:
        # Need to Split exceptions into validation and actual failures
        raise ValidationError(str(err), status_code=400) from err


async def get_wireless_network_scan_async(
    scan_type: Enum(*WlanDBUSInterface.ALLOWED_SCAN_TYPES), interface: str, timeout:int
):
    """
    Queries systemd via dbus to get a scan of the available networks.
    """
    try:
        wlan_dbus = WlanDBUS()
        clean_scan_type = scan_type.strip().lower() if scan_type else None
        if not clean_scan_type or (clean_scan_type not in WlanDBUSInterface.ALLOWED_SCAN_TYPES):
            raise ValidationError(
                f"scan type must be one of: {', '.join(WlanDBUSInterface.ALLOWED_SCAN_TYPES)}",
                status_code=400
            )

        interface_obj = wlan_dbus.get_interface(interface)
        return {"nets": await interface_obj.get_network_scan(scan_type, timeout=timeout)}
    except [WlanDBUSException, ValueError] as err:
        # Need to Split exceptions into validation and actual failures
        raise ValidationError(str(err), status_code=400) from err

async def add_wireless_network(
    interface: str,
    net_config: network.WlanConfig,
    remove_all_first: bool,
    timeout: Optional[int],
):
    """
    Uses wpa_supplicant to connect to a WLAN network.
    """
    try:
        wlan_dbus = WlanDBUS()
        return await wlan_dbus.get_interface(interface).add_network(wlan_config=net_config, remove_others=remove_all_first, timeout=timeout)
    except ValueError as error:
        raise ValidationError(f"{error}", status_code=400)


async def get_current_wireless_network_details(
    interface: str, timeout: int
):
    """
    Queries systemd via dbus to get a scan of the available networks.
    """
    try:
        wlan_dbus = WlanDBUS()
        return wlan_dbus.get_interface(interface).get_current_network_details()
    except WlanDBUSException as err:
        raise ValidationError(str(err), status_code=400) from err

