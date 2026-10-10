"""Sensor platform for Zyxel PLA."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZyxelPLACoordinator

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="mac",
        translation_key="mac",
        icon="mdi:network",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="serial_number",
        translation_key="serial_number",
        icon="mdi:barcode",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="fw_version",
        translation_key="fw_version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="hw_version",
        translation_key="hw_version",
        icon="mdi:memory",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="device_name",
        translation_key="device_name",
        icon="mdi:router",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="device_description",
        translation_key="device_description",
        icon="mdi:information",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="manufacturer",
        translation_key="manufacturer",
        icon="mdi:factory",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    SensorEntityDescription(
        key="node_type",
        translation_key="node_type",
        icon="mdi:sitemap",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="device_id",
        translation_key="device_id",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="domain_name",
        translation_key="domain_name",
        icon="mdi:lan",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="phy_tx",
        translation_key="phy_tx",
        icon="mdi:upload-network",
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
    ),
    SensorEntityDescription(
        key="phy_rx",
        translation_key="phy_rx",
        icon="mdi:download-network",
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
    ),
    SensorEntityDescription(
        key="remote_mac",
        translation_key="remote_mac",
        icon="mdi:network",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="remote_device_id",
        translation_key="remote_device_id",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zyxel PLA sensors based on a config entry."""
    coordinator: ZyxelPLACoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        ZyxelPLASensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)


class ZyxelPLASensor(CoordinatorEntity[ZyxelPLACoordinator], SensorEntity):
    """Representation of a Zyxel PLA sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZyxelPLACoordinator,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.host}_{description.key}"

        # Device info for grouping
        mac = coordinator.data.get("mac") if coordinator.data else None
        serial = coordinator.data.get("serial_number") if coordinator.data else None
        model_name = coordinator.data.get("device_name", "PLA6457") if coordinator.data else "PLA6457"
        node_type = coordinator.data.get("node_type") if coordinator.data else None
        if node_type:
            model_name = f"{model_name} ({node_type})"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            name=coordinator.device_name,
            manufacturer=coordinator.data.get("manufacturer", "Zyxel") if coordinator.data else "Zyxel",
            model=model_name,
            sw_version=coordinator.data.get("fw_version") if coordinator.data else None,
            hw_version=coordinator.data.get("hw_version") if coordinator.data else None,
            serial_number=serial,
            configuration_url=f"http://{coordinator.host}/",
        )
        if mac:
            self._attr_device_info["connections"] = {("mac", mac)}

    @property
    def native_value(self) -> str | int | float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get(self.entity_description.key)
        return value
