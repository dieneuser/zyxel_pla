"""DataUpdateCoordinator for Zyxel PLA."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _parse_uptime_to_boot_time(uptime_str: str | None) -> datetime | None:
    """Parse uptime like '218 days, 2h 58m 21s' into datetime boot timestamp."""
    if not uptime_str:
        return None

    days = hours = minutes = seconds = 0

    # Examples: "218 days, 2h 58m 21s"  or  "2h 58m 21s"  or  "5 days, 0h 0m 12s"
    m_days = re.search(r"(\d+)\s*days?", uptime_str, re.IGNORECASE)
    if m_days:
        days = int(m_days.group(1))

    m_h = re.search(r"(\d+)\s*h", uptime_str, re.IGNORECASE)
    if m_h:
        hours = int(m_h.group(1))

    m_m = re.search(r"(\d+)\s*m", uptime_str, re.IGNORECASE)
    if m_m:
        minutes = int(m_m.group(1))

    m_s = re.search(r"(\d+)\s*s", uptime_str, re.IGNORECASE)
    if m_s:
        seconds = int(m_s.group(1))

    delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return dt_util.now() - delta


class ZyxelPLACoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that fetches data from the Zyxel PLA web interface."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        password: str,
        name: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host.rstrip("/")
        self.password = password
        self.device_name = name or f"Zyxel PLA ({host})"
        self._session: aiohttp.ClientSession | None = None
        self._cookies: dict[str, str] = {}

    async def _async_get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self._session

    async def async_close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _login(self) -> None:
        """Perform login and store cookies."""
        session = await self._async_get_session()
        url = f"http://{self.host}/"

        data = {
            ".PASSWORD": self.password,
            ".CSRFTOKEN": "",
            ".REDIRECT": "/",
        }

        async with session.post(url, data=data) as resp:
            if resp.status >= 400:
                raise UpdateFailed(f"Login failed with status {resp.status}")
            # Cookies are automatically stored in the session
            text = await resp.text()
            if "password" in text.lower() and "login" in text.lower():
                # Still on login page → wrong password
                raise UpdateFailed("Invalid password")

    async def _fetch_page(self, path: str) -> str:
        """Fetch a page (will re-login if necessary)."""
        session = await self._async_get_session()
        url = f"http://{self.host}/{path.lstrip('/')}"

        async with session.get(url) as resp:
            if resp.status == 401 or resp.status == 403:
                await self._login()
                async with session.get(url) as resp2:
                    resp2.raise_for_status()
                    return await resp2.text()
            resp.raise_for_status()
            text = await resp.text()
            # Heuristic: if we got redirected back to login
            if 'name=".PASSWORD"' in text or "login" in text.lower()[:500]:
                await self._login()
                async with session.get(url) as resp2:
                    resp2.raise_for_status()
                    return await resp2.text()
            return text

    def _parse_device_html(self, html: str) -> dict[str, Any]:
        """Parse device.html."""
        soup = BeautifulSoup(html, "lxml")
        data: dict[str, Any] = {}

        def get_by_id(elem_id: str) -> str | None:
            element = soup.find(id=elem_id)
            return element.get_text(strip=True) if element else None

        data["device_name"] = get_by_id("device_hw_name")
        data["device_description"] = get_by_id("device_hw_description")
        data["manufacturer"] = get_by_id("device_hw_manufacturer")
        data["serial_number"] = get_by_id("device_hw_serialnumber")
        data["mac"] = get_by_id("device_hw_macaddress")
        data["hw_version"] = get_by_id("device_hw_rev")
        data["fw_version"] = get_by_id("device_sw_version")

        raw_uptime = get_by_id("device_sw_uptime")
        data["uptime_raw"] = raw_uptime
        data["uptime"] = _parse_uptime_to_boot_time(raw_uptime)

        return data

    def _parse_ghn_html(self, html: str) -> dict[str, Any]:
        """Parse ghn.html – extract own info + connection rates."""
        soup = BeautifulSoup(html, "lxml")
        data: dict[str, Any] = {}

        def get_by_id(elem_id: str) -> str | None:
            element = soup.find(id=elem_id)
            return element.get_text(strip=True) if element else None

        data["mac"] = get_by_id("ghn_basic_mac") or data.get("mac")
        data["device_id"] = get_by_id("ghn_basic_did")
        data["node_type"] = get_by_id("ghn_basic_nodetype")
        data["domain_name"] = None
        domain_input = soup.find(id="ghn_basic_domain")
        if domain_input and domain_input.has_attr("value"):
            data["domain_name"] = domain_input["value"]

        # Connection rates from the JavaScript arrays
        # The page embeds:
        # var mymac='...';
        # var pcmastr="00:00:00:00:00:00,98:0d:...,98:0d:...";
        # var pcptx=new Array(0,0,3086);
        # var pcprx=new Array(0,0,4182);
        # var pcdids=new Array(0,1,2);

        mymac_match = re.search(r"var mymac\s*=\s*'([^']+)'", html)
        pcmastr_match = re.search(r'var pcmastr\s*=\s*"([^"]+)"', html)
        pcptx_match = re.search(r"var pcptx\s*=\s*new Array\(([^)]+)\)", html)
        pcprx_match = re.search(r"var pcprx\s*=\s*new Array\(([^)]+)\)", html)
        pcdids_match = re.search(r"var pcdids\s*=\s*new Array\(([^)]+)\)", html)

        connections: list[dict[str, Any]] = []

        if mymac_match and pcmastr_match and pcptx_match and pcprx_match:
            mymac = mymac_match.group(1).lower()
            macs = [m.strip().lower() for m in pcmastr_match.group(1).split(",")]
            txs = [int(x.strip()) for x in pcptx_match.group(1).split(",")]
            rxs = [int(x.strip()) for x in pcprx_match.group(1).split(",")]
            dids = []
            if pcdids_match:
                dids = [int(x.strip()) for x in pcdids_match.group(1).split(",")]

            for i, mac in enumerate(macs):
                if mac == "00:00:00:00:00:00" or mac == mymac:
                    continue
                # Convert the internal units: Math.floor(value * 32 / 1000)
                tx_mbps = (txs[i] * 32) // 1000 if i < len(txs) else 0
                rx_mbps = (rxs[i] * 32) // 1000 if i < len(rxs) else 0
                did = dids[i] if i < len(dids) else None

                connections.append(
                    {
                        "mac": mac,
                        "device_id": did,
                        "phy_tx": tx_mbps,
                        "phy_rx": rx_mbps,
                    }
                )

        data["connections"] = connections

        # For convenience also expose the first (usually only) remote link
        if connections:
            data["remote_mac"] = connections[0]["mac"]
            data["remote_device_id"] = connections[0]["device_id"]
            data["phy_tx"] = connections[0]["phy_tx"]
            data["phy_rx"] = connections[0]["phy_rx"]
        else:
            data["remote_mac"] = None
            data["remote_device_id"] = None
            data["phy_tx"] = 0
            data["phy_rx"] = 0

        return data

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and parse both pages."""
        try:
            # Login is performed lazily inside _fetch_page if needed
            device_html = await self._fetch_page("device.html")
            ghn_html = await self._fetch_page("ghn.html")

            data = self._parse_device_html(device_html)
            ghn_data = self._parse_ghn_html(ghn_html)

            # Merge – ghn may overwrite mac if present
            data.update({k: v for k, v in ghn_data.items() if v is not None})

            data["host"] = self.host
            return data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching Zyxel PLA data")
            raise UpdateFailed(f"Unexpected error: {err}") from err
