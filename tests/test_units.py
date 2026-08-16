import pytest

from tinynetuse.units import (
    SUPPORTED_UNITS,
    convert_rate,
    format_auto_rate,
    format_rate,
    select_auto_unit,
    threshold_bytes_per_sec,
    threshold_from_display,
    threshold_to_display,
)


MIB = 1024 * 1024

CONVERSION_CASES = [
    (0, {unit: 0 for unit in SUPPORTED_UNITS if unit != "auto"}),
    (
        1024,
        {
            "B/s": 1024,
            "KB/s": 1,
            "MB/s": 1 / 1024,
            "b/s": 8192,
            "Kib/s": 8,
            "Mib/s": 1 / 128,
        },
    ),
    (
        MIB,
        {
            "B/s": MIB,
            "KB/s": 1024,
            "MB/s": 1,
            "b/s": 8 * MIB,
            "Kib/s": 8192,
            "Mib/s": 8,
        },
    ),
    (
        10 * MIB,
        {
            "B/s": 10 * MIB,
            "KB/s": 10 * 1024,
            "MB/s": 10,
            "b/s": 80 * MIB,
            "Kib/s": 80 * 1024,
            "Mib/s": 80,
        },
    ),
]


@pytest.mark.parametrize(("bytes_per_sec", "expected"), CONVERSION_CASES)
def test_conversion_for_every_fixed_unit(bytes_per_sec, expected):
    for unit, expected_value in expected.items():
        assert convert_rate(bytes_per_sec, unit) == pytest.approx(expected_value)


@pytest.mark.parametrize(
    ("bytes_per_sec", "expected_unit"),
    [
        (0, "B/s"),
        (0.001, "B/s"),
        (1023, "B/s"),
        (1024, "KB/s"),
        (MIB - 1, "KB/s"),
        (MIB, "MB/s"),
        (10**30, "MB/s"),
    ],
)
def test_auto_selects_an_actual_unit(bytes_per_sec, expected_unit):
    assert select_auto_unit(bytes_per_sec) == expected_unit
    assert " auto" not in format_auto_rate(bytes_per_sec, 2)


@pytest.mark.parametrize("precision", [0, 1, 2])
@pytest.mark.parametrize(
    ("unit", "expected_value"),
    [
        ("B/s", MIB),
        ("KB/s", 1024),
        ("MB/s", 1),
        ("b/s", 8 * MIB),
        ("Kib/s", 8192),
        ("Mib/s", 8),
    ],
)
def test_format_value_and_label_match(unit, expected_value, precision):
    assert format_rate(MIB, unit, precision) == (
        f"{expected_value:.{precision}f} {unit}"
    )


def test_graph_conversion_keeps_values_and_labels_in_the_same_unit():
    history = [MIB, 10 * MIB]

    assert [convert_rate(rate, "MB/s") for rate in history] == [1, 10]
    assert [convert_rate(rate, "Mib/s") for rate in history] == [8, 80]
    assert format_rate(history[-1], "Mib/s", 1) == "80.0 Mib/s"


def test_graph_auto_uses_one_unit_for_the_whole_history():
    history = [1, 1024, MIB]
    unit = select_auto_unit(max(history))
    values = [convert_rate(rate, unit) for rate in history]

    assert unit == "MB/s"
    assert values == pytest.approx([1 / MIB, 1 / 1024, 1])


@pytest.mark.parametrize("unit", SUPPORTED_UNITS)
def test_threshold_round_trip_for_every_unit(unit):
    stored = threshold_from_display(1.0, unit)

    assert threshold_to_display(stored, unit) == pytest.approx(1.0)


@pytest.mark.parametrize("value", [None, 0, -1])
def test_disabled_threshold_becomes_none(value):
    assert threshold_from_display(value, "MB/s") is None


@pytest.mark.parametrize("unit", SUPPORTED_UNITS)
def test_none_threshold_stays_disabled(unit):
    assert threshold_to_display(None, unit) is None


def test_switching_between_byte_and_bit_thresholds_preserves_the_rate():
    stored = threshold_from_display(1, "MB/s")

    assert stored == 1
    assert threshold_bytes_per_sec(stored) == MIB
    assert threshold_to_display(stored, "Mib/s") == pytest.approx(8)
    assert threshold_from_display(8, "Mib/s") == pytest.approx(stored)


def test_negative_counter_delta_displays_as_zero():
    assert convert_rate(-100, "B/s") == 0
    assert format_rate(-100, "Mib/s", 2) == "0.00 Mib/s"
