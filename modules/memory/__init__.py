"""Модули памяти i8080-5 CI."""
__all__ = ['IOBus', 'MemoryBus', 'MemoryRegion', 'RAMRegion', 'ROMRegion', 'BankedRegion', 'BankedROMRegion', 'ShadowROMRegion', 'PagedRegion', 'SegmentedRegion', 'SegmentedPagedRegion']

from .memory_bus import IOBus, MemoryBus, MemoryRegion, RAMRegion, ROMRegion
from .banked import BankedRegion, BankedROMRegion
from .shadow import ShadowROMRegion
from .paged import PagedRegion
from .segmented import SegmentedRegion
from .segmentedpaged import SegmentedPagedRegion