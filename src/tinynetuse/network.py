"""Adapter discovery and network sampling in bytes per second."""

import ctypes  # for Windows DLL API calls
import ipaddress  # for IP address validation
import socket  # for network address families and conversions
import sys
import time

import psutil  # for network interface and I/O statistics


AUTO_ADAPTER = "auto"
AUTO_ADAPTER_LABEL = "Auto (Recommended)"
AUTO_ROUTE_DESTINATION = "1.1.1.1"  # IP address used to determine the default network route on Windows


class _SockaddrIn(ctypes.Structure):
    # field order and padding must match Windows' SOCKADDR_IN layout
    _fields_ = (
        ("family", ctypes.c_ushort),
        ("port", ctypes.c_ushort),
        ("address", ctypes.c_ubyte * 4),
        ("padding", ctypes.c_ubyte * 8),
    )


# Ask Windows which interface owns the best IPv4 route. No packet is sent.
def windows_default_adapter():
    # if not on Windows, bail early
    if sys.platform != "win32":
        return None

    # missing DLL entry points should just leave auto mode to its fallback
    try:
        ip_helper = ctypes.WinDLL("iphlpapi")  # load the Windows IP helper library
        get_best_interface = ip_helper.GetBestInterfaceEx  # get the best interface for a given destination
        index_to_luid = ip_helper.ConvertInterfaceIndexToLuid  # convert interface index to LUID
        luid_to_alias = ip_helper.ConvertInterfaceLuidToAlias  # convert interface LUID to alias
    except (AttributeError, OSError):
        return None

    # ctypes cannot infer these native Windows signatures, so we have to specify them manually
    get_best_interface.argtypes = (
        ctypes.POINTER(_SockaddrIn),
        ctypes.POINTER(ctypes.c_ulong),
    )
    get_best_interface.restype = ctypes.c_ulong
    index_to_luid.argtypes = (
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_uint64),
    )
    index_to_luid.restype = ctypes.c_ulong
    luid_to_alias.argtypes = (
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.c_wchar_p,
        ctypes.c_size_t,
    )
    luid_to_alias.restype = ctypes.c_ulong

    # ask Windows which interface would reach the probe address
    destination = _SockaddrIn()
    destination.family = socket.AF_INET
    destination.address[:] = socket.inet_aton(AUTO_ROUTE_DESTINATION)
    interface_index = ctypes.c_ulong()

    # if it returns a non-zero value, something went wrong, so bail
    if get_best_interface(destination, ctypes.byref(interface_index)) != 0:
        return None

    # the index is needed as a LUID before Windows can return the adapter name
    interface_luid = ctypes.c_uint64()
    if index_to_luid(interface_index.value, ctypes.byref(interface_luid)) != 0:
        return None

    # give the API room for the interface alias, then return the filled-in text
    alias = ctypes.create_unicode_buffer(257)
    if luid_to_alias(ctypes.byref(interface_luid), alias, len(alias)) != 0:
        return None
    return alias.value or None


# Keep adapters that are up and have a usable IP address.
def discover_adapters(counters, stats, addresses):
    result = []
    for name in counters:
        adapter_stats = stats.get(name)
        if not adapter_stats or not adapter_stats.isup:
            continue
        # skip adapters that are local or have no usable IP
        if not _has_usable_ip(addresses.get(name, ())):
            continue
        result.append(name)
    return sorted(result, key=str.casefold)

# check if any of the given addresses is a usable IP (not loopback or unspecified or anything weird)


def _has_usable_ip(addresses):
    for address in addresses:
        # ignore non-IP addresses
        if address.family not in (socket.AF_INET, socket.AF_INET6):
            continue

        # clean up the address by removing any zone index (after '%')
        value = address.address.split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(value)
        except ValueError:
            continue
        if not ip.is_loopback and not ip.is_unspecified:
            return True
    return False


class NetworkSampler:
    def __init__(
        self,
        selected_adapter=AUTO_ADAPTER,
        counter_reader=None,
        stats_reader=None,
        address_reader=None,
        route_resolver=None,
        clock=None,
    ):
        # readers stay injectable so sampling can be tested without live interfaces
        self._counter_reader = counter_reader or (lambda: psutil.net_io_counters(pernic=True))  # get the network I/O counters for each network interface
        self._stats_reader = stats_reader or psutil.net_if_stats  # get the status (up/down) for each network interface
        self._address_reader = address_reader or psutil.net_if_addrs  # get the IP addresses for each network interface
        self._route_resolver = route_resolver or windows_default_adapter  # check which adapter is the default on Windows
        self._clock = clock or time.monotonic  # use a monotonic clock for measuring intervals

        self.selected_adapter = AUTO_ADAPTER
        self.active_adapters = ()
        self.upload_rate = 0.0
        self.download_rate = 0.0
        self.source_revision = 0  # increases when the monitored adapter changes
        self._previous = {}  # previous byte-counter readings
        self._last_time = 0.0  # when those readings were taken
        self._initialized = False  # records whether the first baseline exists

        # establish the first counter baseline before any rate is reported
        self.set_adapter(selected_adapter)

    # Return adapter names suitable for the Settings combo box.
    def available_adapters(self):
        # use one snapshot of each source so the list describes the same moment
        return discover_adapters(
            self._counter_reader(),
            self._stats_reader(),
            self._address_reader(),
        )

    # Change source and reset counters so adapters are never compared.
    def set_adapter(self, adapter):
        # resolve the requested name against adapters that are usable right now
        counters = self._counter_reader()
        available = discover_adapters(
            counters,
            self._stats_reader(),
            self._address_reader(),
        )
        selected = self._normalize_selection(adapter, available)
        sources = self._resolve_sources(selected, available)
        changed = (
            selected != self.selected_adapter
            or sources != self.active_adapters
            or not self._initialized
        )
        if changed:
            # never compare counters collected from different adapter sources
            self.selected_adapter = selected
            self._reset_baseline(counters, sources, self._clock())
            self._initialized = True
            self.source_revision += 1
        return changed

    # Return upload and download rates since the previous sample.
    def sample(self) -> tuple[float, float]:
        # refresh the source list because interfaces can appear or disappear
        now = self._clock()
        counters = self._counter_reader()
        available = discover_adapters(
            counters,
            self._stats_reader(),
            self._address_reader(),
        )
        selected = self._normalize_selection(self.selected_adapter, available)
        sources = self._resolve_sources(selected, available)

        if selected != self.selected_adapter or sources != self.active_adapters:
            # topology changed, so the next interval starts from a clean baseline
            self.selected_adapter = selected
            self._reset_baseline(counters, sources, now)
            self.source_revision += 1
            return 0.0, 0.0

        elapsed = now - self._last_time
        sent_delta = 0
        recv_delta = 0
        # add deltas from every source selected by auto mode or the user
        for name in sources:
            current = counters.get(name)
            previous = self._previous.get(name)
            if not current or not previous:
                continue
            sent_delta += max(0, current.bytes_sent - previous[0])
            recv_delta += max(0, current.bytes_recv - previous[1])

        self._remember(counters, sources)
        self._last_time = now
        # rates are byte deltas divided by the elapsed sampling interval
        if elapsed <= 0:
            self.upload_rate = 0.0
            self.download_rate = 0.0
        else:
            self.upload_rate = sent_delta / elapsed
            self.download_rate = recv_delta / elapsed
        return self.upload_rate, self.download_rate

    def _normalize_selection(self, adapter, available):
        # preserve the canonical available spelling for case-insensitive matches
        if not isinstance(adapter, str) or adapter == AUTO_ADAPTER:
            return AUTO_ADAPTER
        for name in available:
            if name.casefold() == adapter.casefold():
                return name
        return AUTO_ADAPTER

    def _resolve_sources(self, selected, available):
        # an explicit adapter always wins over route detection
        if selected != AUTO_ADAPTER:
            return (selected,)

        route_adapter = self._route_resolver()
        if route_adapter:
            for name in available:
                if name.casefold() == route_adapter.casefold():
                    return (name,)

        # If Windows routing cannot be matched, total every active adapter.
        return tuple(available)

    def _reset_baseline(self, counters, sources, now):
        # reset both counters and displayed rates when the source changes
        self.active_adapters = tuple(sources)
        self._remember(counters, sources)
        self._last_time = now
        self.upload_rate = 0.0
        self.download_rate = 0.0

    def _remember(self, counters, sources):
        # retain only counters for the sources used by the next interval
        self._previous = {
            name: (counters[name].bytes_sent, counters[name].bytes_recv)
            for name in sources
            if name in counters
        }
