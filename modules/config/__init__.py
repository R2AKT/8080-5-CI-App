"""Конфигурация устройств и профили систем."""
__all__ = ['DeviceConfig', 'DeviceFactory', 'SYSTEM_PROFILES', 'get_profile', 'get_profile_names']

from .device_config import DeviceConfig, DeviceFactory
from .system_profiles import SYSTEM_PROFILES, get_profile, get_profile_names
