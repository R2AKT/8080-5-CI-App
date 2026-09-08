try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


class DeviceConfig:
    """Парсер TOML-конфигурации устройств"""

    def __init__(self) -> None:
        self.system_name: str = ""
        self.cpu: str = "i8080"
        self.clock_mhz: float = 2.5
        self.memory_regions: list = []  # [{type, start, end, name, file, ...}]
        self.devices: list = []         # [{type, name, base_port, ...}]

    def load_from_dict(self, config_dict: dict) -> None:
        """Загрузить конфигурацию из dict (внешний профиль)"""
        system_cfg = config_dict.get("system", {})
        self.system_name = system_cfg.get("name", "Custom")
        self.cpu = system_cfg.get("cpu", "i8080")
        self.clock_mhz = system_cfg.get("clock_mhz", 2)

        self.memory_regions = config_dict.get("memory", {}).get("regions", [])
        self.devices = config_dict.get("devices", [])

        errors = self.validate()
        if errors:
            raise ValueError("Ошибки конфигурации:\n" + "\n".join(errors))
        
    def load_from_file(self, path):
        """Загрузить конфигурацию из TOML-файла"""
        if tomllib is None:
            raise ImportError("tomllib/tomli не установлен. Установите: pip install tomli")
        with open(path, 'rb') as f:
            data = tomllib.load(f)
        self._parse(data)
        return self

    def load_from_string(self, toml_string):
        """Загрузить конфигурацию из TOML-строки"""
        if not toml_string or not toml_string.strip():
            # Пустая строка — создаём пустую конфигурацию
            self.system_name = "Empty System"
            self.cpu = "i8080"
            self.clock_mhz = 2
            self.memory_regions = []
            self.devices = []
            return
        
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                # Если нет tomllib, создаём пустую конфигурацию
                self.system_name = "Empty System"
                self.cpu = "i8080"
                self.clock_mhz = 2
                self.memory_regions = []
                self.devices = []
                return
        
        try:
            data = tomllib.loads(toml_string)
            self._parse(data)
        except Exception as e:
            # При ошибке парсинга создаём пустую конфигурацию
            self.system_name = "Empty System"
            self.cpu = "i8080"
            self.clock_mhz = 2
            self.memory_regions = []
            self.devices = []

    def _parse(self, data):
        """Парсинг конфигурации из словаря"""
        # Защита от пустых или некорректных данных
        if not data or not isinstance(data, dict):
            self.system_name = "Empty System"
            self.cpu = "i8080"
            self.clock_mhz = 2
            self.memory_regions = []
            self.devices = []
            return

        # Секция [system]
        system = data.get("system", {})
        if not isinstance(system, dict):
            system = {}
        self.system_name = system.get("name", "Empty System")
        self.cpu = system.get("cpu", "i8080")
        self.clock_mhz = system.get("clock_mhz", 2)

        # Секция [memory]
        memory = data.get("memory", {})
        if not isinstance(memory, dict):
            memory = {}
        
        regions = memory.get("regions", [])
        if not isinstance(regions, list):
            regions = []
        
        self.memory_regions = []
        for mem in regions:
            if not isinstance(mem, dict):
                continue  # Пропускаем некорректные записи
            self.memory_regions.append({
                "type": mem.get("type", "ram"),
                "start": mem.get("start", 0),
                "end": mem.get("end", 0xFFFF),
                "name": mem.get("name", "RAM"),
                "file": mem.get("file", None),
            })

        # Секция [devices]
        devices = data.get("devices", [])
        if not isinstance(devices, list):
            devices = []
        
        self.devices = []
        for dev in devices:
            if not isinstance(dev, dict):
                continue
            self.devices.append(dev)

    @staticmethod
    def _parse_addr(value) -> int:
        """Парсинг адреса: '0x1234', '0X1234', 0x1234, 4660"""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            value = value.strip()
            if value.lower().startswith("0x"):
                return int(value, 16)
            return int(value)
        return int(value)

    def validate(self) -> list:
        """Проверка конфигурации на конфликты адресов"""
        errors = []
        # Проверка конфликтов портов
        port_ranges = []
        for dev in self.devices:
            dev_type = dev.get("type", "")
            base = dev.get("base_port", 0)
            port_count = DeviceFactory.get_port_count(dev_type)
            end_port = base + port_count - 1
            port_ranges.append((base, end_port, dev.get("name", dev_type)))

        # Проверка пересечений
        for i in range(len(port_ranges)):
            for j in range(i + 1, len(port_ranges)):
                s1, e1, n1 = port_ranges[i]
                s2, e2, n2 = port_ranges[j]
                if s1 <= e2 and s2 <= e1:
                    errors.append(
                        f"Конфликт портов: {n1} [{s1:02X}-{e1:02X}] "
                        f"пересекается с {n2} [{s2:02X}-{e2:02X}]"
                    )
        return errors

    def to_dict(self) -> dict:
        """Конфигурация в виде словаря (для отладки)"""
        return {
            "system": {
                "name": self.system_name,
                "cpu": self.cpu,
                "clock_mhz": self.clock_mhz,
            },
            "memory": self.memory_regions,
            "devices": self.devices,
        }


class DeviceFactory:
    """Фабрика устройств: создаёт устройства из конфигурации"""

    # Размер портов для каждого типа устройства
    PORT_COUNTS = {
        "i8251": 2,             # USART: Data + Control
        "i8253": 4,             # PIT: 3 канала + Control
        "i8255": 4,             # PPI: порты A, B, C, Control
        "i8237": 16,            # DMA: 16 портов
        "i8257": 16,            # DMA: 16 портов
        "i8259": 2,             # PIC: 2 порт
        "i8259a": 2,            # PIC: 2 порта
        "i8272": 4,             # FDC: 4 порта
        "i8275": 2,             # CRT: 2 порта
        "i8276": 2,             # CRT: 2 порта
        "i8279": 2,             # Клавиатура/дисплей: 2 порта
        "am9511": 2,            # APU: Data + Command
        "i512vi1": 2,           # RTC: Address + Data
        "i16550": 8,            # UART: 8 регистров
        "ch376s": 2,            # USB: Data + Command
        "cf_ide": 8,            # CF IDE: 8 портов
        "lcd1602": 2,           # LCD: Data + Control
        "lcd2004": 2,           # LCD: Data + Control
        "tft8080": 2,           # TFT: 2 порта
        "keyboard8x8": 0,       # Клавиатура: не занимает порты (подключается к 8255)
        "keyboard8279": 0,      # Клавиатура (подключается через 8279)
        "cube3d": 0,            # Куб 8×8×8: не занимает порты (подключается к 8255)
        "discrete_video": 0,    # Дискретное видео: не занимает порты
        "bitmap_video": 0,      # Графика: не занимает порты
    }

    @classmethod
    def get_port_count(cls, device_type: str) -> int:
        """Размер портов для типа устройства"""
        return cls.PORT_COUNTS.get(device_type, 2)

    @classmethod
    def create_device(cls, dev_config: dict, memory_bus=None):
        """Создать устройство из конфигурации"""
        dev_type = dev_config.get("type", "")
        name = dev_config.get("name", dev_type)
        base_port = dev_config.get("base_port", 0)

        device = cls._create_instance(dev_type, base_port, name)

        # === Параметры для 8275/8276 (ВГ75) ===
        if device is not None and dev_type in ("i8275", "i8276"):
            if "video_addr" in dev_config:
                device.display_buffer_addr = dev_config["video_addr"]
            cls._apply_optional_params(device, dev_config,
                                       ("chars_per_line", "lines_per_screen", "char_height"))

        # === Параметры для дискретного видео (Микро-80) ===
        if device is not None and dev_type == "discrete_video":
            if "video_addr" in dev_config:
                device.video_addr = dev_config["video_addr"]
            if "attr_addr" in dev_config:
                device.attr_addr = dev_config["attr_addr"]
            cls._apply_optional_params(device, dev_config,
                                       ("chars_per_line", "lines_per_screen", "char_height"))

        # === Параметры для графического видео (Специалист) ===
        if device is not None and dev_type == "bitmap_video":
            if "video_addr" in dev_config:
                device.video_addr = dev_config["video_addr"]
            cls._apply_optional_params(device, dev_config,
                                       ("width", "height", "planes", "bit0_left"))

        # === ОБЩИЙ блок загрузки знакогенератора ===
        # Теперь охватывает и 8275/8276, и discrete_video
        if device is not None and dev_type in ("i8275", "i8276", "discrete_video"):
            if "char_width" in dev_config:
                device.char_width = dev_config["char_width"]
            if "chargen_file" in dev_config:
                chargen_path = dev_config["chargen_file"]
                char_width = dev_config.get("char_width", 8)
                num_chars = dev_config.get("num_chars", 256)
                invert = dev_config.get("invert", False)
                bit_reverse = dev_config.get("bit_reverse", False)
                device.load_font_from_file(chargen_path,
                                          char_width=char_width,
                                          num_chars=num_chars,
                                          invert=invert,
                                          bit_reverse=bit_reverse)
                                          
        if device is None:
            return None

        # Регистрация на шине
        if memory_bus is not None and hasattr(device, 'register_to_bus'):
            device.register_to_bus(memory_bus)

        return device

    @classmethod
    def _create_instance(cls, dev_type, base_port, name):
        """Создать экземпляр устройства"""
        # Ленивые импорты
        try:
            if dev_type == "i8237":
                from modules.io.i8257 import I8237
                return I8237(base_port=base_port, name=name)
            elif dev_type == "i8251":
                from modules.io.i8251 import I8251
                return I8251(base_port=base_port, name=name)
            elif dev_type == "i8253":
                from modules.io.i8253 import I8253
                return I8253(base_port=base_port, name=name)
            elif dev_type == "i8255":
                from modules.io.i8255 import I8255
                return I8255(base_port=base_port, name=name)
            elif dev_type == "i8257":
                from modules.io.i8257 import I8257
                return I8257(base_port=base_port, name=name)
            elif dev_type == "i8259":
                from modules.io.i8259 import I8259
                return I8259(base_port=base_port, name=name)
            elif dev_type == "i8259a":
                from modules.io.i8259 import I8259A
                return I8259A(base_port=base_port, name=name) 
            elif dev_type == "i8272":
                from modules.io.i8272 import I8272
                return I8272(base_port=base_port, name=name)
            elif dev_type == "i8275":
                from modules.io.i8275 import I8275
                return I8275(base_port=base_port, name=name)
            elif dev_type == "i8276":
                from modules.io.i8276 import I8276
                return I8276(base_port=base_port, name=name)
            elif dev_type == "i8279":
                from modules.io.i8279 import I8279
                return I8279(base_port=base_port, name=name)
            elif dev_type == "i16550":
                from modules.io.i16550 import I16550
                return I16550(base_port=base_port, name=name)
            elif dev_type == "i512vi1":
                from modules.io.i512vi1 import I512VI1
                return I512VI1(base_port=base_port, name=name)
            elif dev_type == "cf_ide":
                from modules.io.cf_ide import CFIDE
                return CFIDE(base_port=base_port, name=name)
            elif dev_type == "ch376s":
                from modules.io.ch376s import CH376S
                return CH376S(base_port=base_port, name=name)
            elif dev_type == "am9511":
                from modules.io.am9511 import AM9511
                return AM9511(base_port=base_port, name=name)
            elif dev_type == "lcd1602":
                from modules.io.lcd1602 import LCD1602
                return LCD1602(base_port=base_port, name=name)
            elif dev_type == "lcd2004":
                from modules.io.lcd2004 import LCD2004
                return LCD2004(base_port=base_port, name=name)
            elif dev_type == "tft8080":
                from modules.io.tft8080 import TFT8080
                return TFT8080(base_port=base_port, name=name)
            elif dev_type == "keyboard8x8":
                from modules.io.keyboard8x8 import Keyboard8x8
                return Keyboard8x8(name=name)
            elif dev_type == "keyboard8279":
                from modules.io.keyboard8279_adapter import Keyboard8279Adapter
                return Keyboard8279Adapter(name=name)
            elif dev_type == "cube3d":
                from modules.io.cube3d import Cube3D
                return Cube3D(name=name)
            elif dev_type == "discrete_video":
                from modules.io.discrete_video import DiscreteVideo
                return DiscreteVideo(name=name)
            elif dev_type == "bitmap_video":
                from modules.io.bitmap_video import BitmapVideo
                return BitmapVideo(name=name)
            else:
                return None
        except ImportError:
            return None

    @staticmethod
    def _apply_optional_params(device, config, keys):
        """Применить опциональные параметры из конфига к устройству."""
        for key in keys:
            if key in config:
                setattr(device, key, config[key])

    @classmethod
    def create_memory_region(cls, mem_config: dict):
        """Создать регион памяти из конфигурации"""
        mem_type = mem_config.get("type", "ram")
        start = mem_config.get("start", 0)
        end = mem_config.get("end", 0xFFFF)
        name = mem_config.get("name", "RAM")
        file_path = mem_config.get("file", None)

        if mem_type == "ram":
            from modules.memory.memory_bus import RAMRegion
            return RAMRegion(start, end, name=name)
        elif mem_type == "rom":
            from modules.memory.memory_bus import ROMRegion
            data = {}
            if file_path:
                data = cls._load_rom_file(file_path, start)
            return ROMRegion(start, end, data=data, name=name)
        elif mem_type == "shadow":
            from modules.memory.shadow import ShadowROMRegion
            data = {}
            file_path = mem_config.get("file", None)
            if file_path:
                data = cls._load_rom_file(file_path, 0)
            low_addr = mem_config.get("low_addr", 0x0000)
            high_addr = mem_config.get("high_addr", 0xF800)
            mode = mem_config.get("mode", "m1")
            action = mem_config.get("action", "move")
            trigger_addr = mem_config.get("trigger_addr", None)
            trigger_port = mem_config.get("trigger_port", None)
            m1_count = mem_config.get("m1_count", 3)
            return ShadowROMRegion(data, low_addr, high_addr, mode, action, trigger_addr, trigger_port, m1_count, name=name)
        elif mem_type == "banked":
            from modules.memory.banked import BankedRegion
            num_banks = mem_config.get("num_banks", 2)
            switch_port = mem_config.get("switch_port", None)
            switch_addr = mem_config.get("switch_addr", None)
            return BankedRegion(start, end, num_banks, switch_port, switch_addr, name=name)
        elif mem_type == "bankedrom":
            from modules.memory.banked import BankedROMRegion
            num_banks = mem_config.get("num_banks", 2)
            switch_port = mem_config.get("switch_port", None)
            switch_addr = mem_config.get("switch_addr", None)
            banks = []
            for i in range(num_banks):
                bank_file = mem_config.get(f"bank_{i}_file", None)
                bank_data = {}
                if bank_file:
                    bank_data = cls._load_rom_file(bank_file, 0)
                banks.append(bank_data)
            return BankedROMRegion(start, end, banks, switch_port, switch_addr, name=name)
        elif mem_type == "paged":
            from modules.memory.paged import PagedRegion
            page_size = mem_config.get("page_size", 16384)
            num_physical_pages = mem_config.get("num_physical_pages", 16)
            switch_ports = mem_config.get("switch_ports", [])
            switch_addrs = mem_config.get("switch_addrs", [])
            return PagedRegion(start, end, page_size, num_physical_pages, switch_ports, switch_addrs, name=name)
        elif mem_type == "segmented":
            from modules.memory.segmented import SegmentedRegion
            num_segments = mem_config.get("num_segments", 16)
            switch_port = mem_config.get("switch_port", None)
            switch_addr = mem_config.get("switch_addr", None)
            return SegmentedRegion(start, end, num_segments, switch_port, switch_addr, name=name)
        elif mem_type == "segmentedpaged":
            from modules.memory.segmentedpaged import SegmentedPagedRegion
            segment_size = mem_config.get("segment_size", 16384)
            num_physical_pages = mem_config.get("num_physical_pages", 16)
            base_port = mem_config.get("base_port", 0x00)
            return SegmentedPagedRegion(start, end, segment_size, num_physical_pages, base_port, name=name)
        # === НОВАЯ ВЕТКА: MMIO ===
        elif mem_type == "mmio":
            from modules.memory.mmio import MMIORegion
            region = MMIORegion(device=None, name=name)
            region.set_device_name(mem_config.get("device", ""))

            # Одиночные маппинги
            for m in mem_config.get("mappings", []):
                addr = m.get("addr")
                port = m.get("port")
                if addr is not None and port is not None:
                    region.add_mapping(addr, port)

            # Диапазоны
            for r in mem_config.get("ranges", []):
                start_addr = r.get("start_addr")
                start_port = r.get("start_port")
                count = r.get("count", 1)
                if start_addr is not None and start_port is not None:
                    region.add_range(start_addr, start_port, count)

            return region

        else:
            return None

    @staticmethod
    def _load_rom_file(path: str, start_addr: int) -> dict:
        """Загрузить ROM-файл"""
        data = {}
        try:
            with open(path, 'rb') as f:
                rom_data = f.read()
            for i, byte in enumerate(rom_data):
                data[start_addr + i] = byte
        except OSError:
            pass
        return data
