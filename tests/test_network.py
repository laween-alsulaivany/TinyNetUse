import ctypes
import socket
from types import SimpleNamespace

import pytest

import tinynetuse.network as sampling_module
from tinynetuse.network import (
    AUTO_ADAPTER,
    AUTO_ROUTE_DESTINATION,
    NetworkSampler,
    discover_adapters,
    windows_default_adapter,
)


def counters(sent, received):
    return SimpleNamespace(bytes_sent=sent, bytes_recv=received)


def adapter_stats(is_up=True):
    return SimpleNamespace(isup=is_up)


def address(value):
    family = socket.AF_INET6 if ":" in value else socket.AF_INET
    return SimpleNamespace(family=family, address=value)


def sequence(values):
    values = iter(values)
    return lambda: next(values)


def network_state(wifi_up=False):
    stats = {
        "Ethernet": adapter_stats(),
        "Wi-Fi": adapter_stats(wifi_up),
        "VPN": adapter_stats(),
        "Loopback": adapter_stats(),
    }
    addresses = {
        "Ethernet": [address("192.168.1.10")],
        "Wi-Fi": [address("192.168.1.20")],
        "VPN": [address("10.8.0.2")],
        "Loopback": [address("127.0.0.1"), address("::1")],
    }
    return stats, addresses


def make_sampler(
    snapshots,
    times,
    selected="Ethernet",
    route_resolver=lambda: "Ethernet",
    stats=None,
    addresses=None,
):
    default_stats, default_addresses = network_state()
    return NetworkSampler(
        selected_adapter=selected,
        counter_reader=sequence(snapshots),
        stats_reader=lambda: stats or default_stats,
        address_reader=lambda: addresses or default_addresses,
        route_resolver=route_resolver,
        clock=sequence(times),
    )


class FakeFunction:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


def test_windows_route_lookup_returns_the_interface_alias(monkeypatch):
    def get_best_interface(destination, index_pointer):
        assert bytes(destination.address) == socket.inet_aton(
            AUTO_ROUTE_DESTINATION
        )
        ctypes.cast(index_pointer, ctypes.POINTER(ctypes.c_ulong)).contents.value = 7
        return 0

    def index_to_luid(interface_index, luid_pointer):
        assert interface_index == 7
        ctypes.cast(luid_pointer, ctypes.POINTER(ctypes.c_uint64)).contents.value = 99
        return 0

    def luid_to_alias(luid_pointer, alias, length):
        assert ctypes.cast(
            luid_pointer, ctypes.POINTER(ctypes.c_uint64)
        ).contents.value == 99
        assert length >= len("Ethernet") + 1
        alias.value = "Ethernet"
        return 0

    fake_ip_helper = SimpleNamespace(
        GetBestInterfaceEx=FakeFunction(get_best_interface),
        ConvertInterfaceIndexToLuid=FakeFunction(index_to_luid),
        ConvertInterfaceLuidToAlias=FakeFunction(luid_to_alias),
    )
    monkeypatch.setattr(sampling_module.sys, "platform", "win32")
    monkeypatch.setattr(
        sampling_module.ctypes,
        "WinDLL",
        lambda name: fake_ip_helper,
        raising=False,
    )

    assert windows_default_adapter() == "Ethernet"


@pytest.mark.parametrize(
    "failure_stage",
    ["best_interface", "index_to_luid", "luid_to_alias"],
)
def test_windows_route_lookup_returns_none_when_a_native_call_fails(
    monkeypatch, failure_stage
):
    def get_best_interface(destination, index_pointer):
        if failure_stage == "best_interface":
            return 1
        ctypes.cast(index_pointer, ctypes.POINTER(ctypes.c_ulong)).contents.value = 7
        return 0

    def index_to_luid(interface_index, luid_pointer):
        if failure_stage == "index_to_luid":
            return 1
        ctypes.cast(luid_pointer, ctypes.POINTER(ctypes.c_uint64)).contents.value = 99
        return 0

    def luid_to_alias(luid_pointer, alias, length):
        if failure_stage == "luid_to_alias":
            return 1
        alias.value = "Ethernet"
        return 0

    fake_ip_helper = SimpleNamespace(
        GetBestInterfaceEx=FakeFunction(get_best_interface),
        ConvertInterfaceIndexToLuid=FakeFunction(index_to_luid),
        ConvertInterfaceLuidToAlias=FakeFunction(luid_to_alias),
    )
    monkeypatch.setattr(sampling_module.sys, "platform", "win32")
    monkeypatch.setattr(
        sampling_module.ctypes,
        "WinDLL",
        lambda name: fake_ip_helper,
        raising=False,
    )

    assert windows_default_adapter() is None


def test_windows_route_lookup_returns_none_when_ip_helper_is_unavailable(
    monkeypatch,
):
    def unavailable_ip_helper(name):
        raise OSError("iphlpapi unavailable")

    monkeypatch.setattr(sampling_module.sys, "platform", "win32")
    monkeypatch.setattr(
        sampling_module.ctypes,
        "WinDLL",
        unavailable_ip_helper,
        raising=False,
    )

    assert windows_default_adapter() is None


def test_discovery_keeps_active_physical_and_virtual_adapters():
    stats, addresses = network_state()
    per_adapter = {
        "Ethernet": counters(0, 0),
        "Wi-Fi": counters(0, 0),
        "VPN": counters(0, 0),
        "Loopback": counters(0, 0),
    }

    assert discover_adapters(per_adapter, stats, addresses) == [
        "Ethernet",
        "VPN",
    ]


def test_sampler_calculates_selected_adapter_rates():
    sampler = make_sampler(
        [
            {"Ethernet": counters(1000, 2000), "VPN": counters(500, 500)},
            {"Ethernet": counters(1200, 2600), "VPN": counters(1500, 1500)},
        ],
        [10.0, 12.0],
    )

    assert sampler.resolved_adapter is None
    assert sampler.sample() == pytest.approx((100, 300))


def test_sampler_uses_actual_elapsed_time():
    sampler = make_sampler(
        [
            {"Ethernet": counters(0, 0)},
            {"Ethernet": counters(300, 900)},
        ],
        [1.0, 1.5],
    )

    assert sampler.sample() == pytest.approx((600, 1800))


def test_counter_reset_returns_zero_and_updates_baseline():
    sampler = make_sampler(
        [
            {"Ethernet": counters(1000, 2000)},
            {"Ethernet": counters(100, 200)},
            {"Ethernet": counters(150, 300)},
        ],
        [1.0, 2.0, 3.0],
    )

    assert sampler.sample() == (0, 0)
    assert sampler.sample() == pytest.approx((50, 100))


def test_non_positive_elapsed_time_returns_zero():
    sampler = make_sampler(
        [
            {"Ethernet": counters(10, 20)},
            {"Ethernet": counters(30, 40)},
        ],
        [5.0, 5.0],
    )

    assert sampler.sample() == (0, 0)


def test_auto_uses_adapter_selected_by_windows_route():
    sampler = make_sampler(
        [
            {"Ethernet": counters(100, 200), "VPN": counters(1000, 2000)},
            {"Ethernet": counters(300, 600), "VPN": counters(3000, 6000)},
        ],
        [1.0, 3.0],
        selected=AUTO_ADAPTER,
        route_resolver=lambda: "Ethernet",
    )

    assert sampler.active_adapters == ("Ethernet",)
    assert sampler.resolved_adapter == "Ethernet"
    assert sampler.sample() == pytest.approx((100, 200))


def test_auto_matches_the_windows_route_alias_case_insensitively():
    sampler = make_sampler(
        [
            {"Ethernet": counters(100, 200), "VPN": counters(1000, 2000)},
            {"Ethernet": counters(300, 600), "VPN": counters(3000, 6000)},
        ],
        [1.0, 3.0],
        selected=AUTO_ADAPTER,
        route_resolver=lambda: "ethernet",
    )

    assert sampler.active_adapters == ("Ethernet",)
    assert sampler.sample() == pytest.approx((100, 200))


def test_auto_fallback_aggregates_active_adapters():
    sampler = make_sampler(
        [
            {"Ethernet": counters(100, 200), "VPN": counters(1000, 2000)},
            {"Ethernet": counters(300, 600), "VPN": counters(1400, 2600)},
        ],
        [1.0, 3.0],
        selected=AUTO_ADAPTER,
        route_resolver=lambda: None,
    )

    assert sampler.active_adapters == ("Ethernet", "VPN")
    assert sampler.resolved_adapter is None
    assert sampler.sample() == pytest.approx((300, 500))


def test_auto_mode_with_no_usable_adapters_reports_zero_rates():
    sampler = NetworkSampler(
        selected_adapter=AUTO_ADAPTER,
        counter_reader=sequence(
            [
                {"Loopback": counters(100, 200)},
                {"Loopback": counters(300, 600)},
            ]
        ),
        stats_reader=lambda: {"Loopback": adapter_stats()},
        address_reader=lambda: {"Loopback": [address("127.0.0.1")]},
        route_resolver=lambda: None,
        clock=sequence([1.0, 3.0]),
    )

    assert sampler.active_adapters == ()
    assert sampler.sample() == (0, 0)


def test_selected_adapter_disappears_and_falls_back_to_auto():
    sampler = make_sampler(
        [
            {"Ethernet": counters(100, 200), "VPN": counters(1000, 2000)},
            {"Ethernet": counters(300, 500)},
            {"Ethernet": counters(500, 900)},
        ],
        [1.0, 2.0, 4.0],
        selected="VPN",
        route_resolver=lambda: "Ethernet",
    )

    assert sampler.sample() == (0, 0)
    assert sampler.selected_adapter == AUTO_ADAPTER
    assert sampler.active_adapters == ("Ethernet",)
    assert sampler.sample() == pytest.approx((100, 200))


def test_missing_adapter_at_startup_uses_auto():
    sampler = make_sampler(
        [{"Ethernet": counters(100, 200), "VPN": counters(1000, 2000)}],
        [1.0],
        selected="Wi-Fi",
        route_resolver=lambda: "Ethernet",
    )

    assert sampler.selected_adapter == AUTO_ADAPTER
    assert sampler.active_adapters == ("Ethernet",)


def test_changing_adapter_resets_baseline_without_a_spike():
    sampler = make_sampler(
        [
            {"Ethernet": counters(100, 200), "VPN": counters(10_000, 20_000)},
            {"Ethernet": counters(200, 400), "VPN": counters(20_000, 40_000)},
            {"Ethernet": counters(300, 600), "VPN": counters(30_000, 60_000)},
            {"Ethernet": counters(400, 800), "VPN": counters(30_200, 60_600)},
        ],
        [1.0, 2.0, 3.0, 5.0],
    )

    assert sampler.sample() == pytest.approx((100, 200))
    revision = sampler.source_revision
    assert sampler.set_adapter("VPN") is True
    assert sampler.source_revision == revision + 1
    assert sampler.sample() == pytest.approx((100, 300))


def test_auto_route_change_resets_baseline():
    routes = sequence(["Ethernet", "VPN", "VPN"])
    sampler = make_sampler(
        [
            {"Ethernet": counters(100, 200), "VPN": counters(1000, 2000)},
            {"Ethernet": counters(300, 600), "VPN": counters(3000, 6000)},
            {"Ethernet": counters(500, 900), "VPN": counters(3200, 6600)},
        ],
        [1.0, 2.0, 4.0],
        selected=AUTO_ADAPTER,
        route_resolver=routes,
    )

    assert sampler.sample() == (0, 0)
    assert sampler.active_adapters == ("VPN",)
    assert sampler.sample() == pytest.approx((100, 300))


def test_aggregate_fallback_handles_one_adapter_reset():
    sampler = make_sampler(
        [
            {"Ethernet": counters(1000, 2000), "VPN": counters(100, 200)},
            {"Ethernet": counters(10, 20), "VPN": counters(300, 600)},
        ],
        [1.0, 3.0],
        selected=AUTO_ADAPTER,
        route_resolver=lambda: None,
    )

    assert sampler.sample() == pytest.approx((100, 200))
