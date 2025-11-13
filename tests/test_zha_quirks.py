"""Tests for Ubisys ZHA quirk helpers using lightweight zigpy stubs."""

from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace

import pytest


@pytest.fixture
def ubisys_quirk_modules():
    """Install minimal zigpy/zhaquirks stubs and import quirk modules."""

    stub_names = [
        "zigpy",
        "zigpy.quirks",
        "zigpy.quirks.v2",
        "zigpy.types",
        "zigpy.zcl",
        "zigpy.zcl.foundation",
        "zigpy.zcl.clusters",
        "zigpy.zcl.clusters.general",
        "zigpy.zcl.clusters.homeautomation",
        "zigpy.zcl.clusters.lighting",
        "zigpy.zcl.clusters.smartenergy",
        "zhaquirks",
        "zhaquirks.const",
    ]
    saved = {name: sys.modules.get(name) for name in stub_names}
    for name in stub_names:
        sys.modules.pop(name, None)

    def register(name: str, module: types.ModuleType) -> types.ModuleType:
        sys.modules[name] = module
        return module

    zigpy = register("zigpy", types.ModuleType("zigpy"))

    class CustomCluster:
        def __init__(self, *args, **kwargs):
            self.read_history: list[int | None] = []
            self.write_history: list[tuple[dict, int | None]] = []

        async def read_attributes(
            self, attributes, allow_cache=False, only_cache=False, manufacturer=None
        ):
            self.read_history.append(manufacturer)
            return {"attrs": attributes}

        async def write_attributes(self, attributes, manufacturer=None):
            self.write_history.append((attributes, manufacturer))
            return ["ok"]

    zigpy_quirks = register("zigpy.quirks", types.ModuleType("zigpy.quirks"))
    zigpy_quirks.CustomCluster = CustomCluster
    zigpy_quirks.CustomDevice = type("CustomDevice", (), {})
    zigpy.quirks = zigpy_quirks

    zigpy_quirks_v2 = register("zigpy.quirks.v2", types.ModuleType("zigpy.quirks.v2"))

    class QuirkBuilder:
        def __init__(self, *args, **kwargs):
            pass

        def replaces(self, *args, **kwargs):
            return self

        def adds(self, *args, **kwargs):
            return self

        def add_to_registry(self):
            return None

    zigpy_quirks_v2.QuirkBuilder = QuirkBuilder

    zigpy.types = register("zigpy.types", types.ModuleType("zigpy.types"))
    zigpy.types.CharacterString = bytes

    zigpy_zcl = register("zigpy.zcl", types.ModuleType("zigpy.zcl"))

    foundation = register(
        "zigpy.zcl.foundation", types.ModuleType("zigpy.zcl.foundation")
    )

    class ZCLAttributeDef:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    foundation.ZCLAttributeDef = ZCLAttributeDef
    foundation.WriteAttributesResponse = type("WriteAttributesResponse", (), {})
    foundation.DATA_TYPES = SimpleNamespace(bitmap8="bitmap8")
    zigpy_zcl.foundation = foundation

    register("zigpy.zcl.clusters", types.ModuleType("zigpy.zcl.clusters"))

    def simple_cluster(name: str):
        return type(name, (), {"cluster_id": 0x0001})

    general = register(
        "zigpy.zcl.clusters.general", types.ModuleType("zigpy.zcl.clusters.general")
    )
    for cls_name in ["Basic", "Identify", "Groups", "Scenes", "OnOff", "LevelControl"]:
        setattr(general, cls_name, simple_cluster(cls_name))

    homeauto = register(
        "zigpy.zcl.clusters.homeautomation",
        types.ModuleType("zigpy.zcl.clusters.homeautomation"),
    )
    homeauto.ElectricalMeasurement = simple_cluster("ElectricalMeasurement")

    lighting = register(
        "zigpy.zcl.clusters.lighting", types.ModuleType("zigpy.zcl.clusters.lighting")
    )
    lighting.Ballast = simple_cluster("Ballast")

    smartenergy = register(
        "zigpy.zcl.clusters.smartenergy",
        types.ModuleType("zigpy.zcl.clusters.smartenergy"),
    )
    smartenergy.Metering = simple_cluster("Metering")

    zhaquirks = register("zhaquirks", types.ModuleType("zhaquirks"))
    zhaquirks_consts = register("zhaquirks.const", types.ModuleType("zhaquirks.const"))
    for const in [
        "DEVICE_TYPE",
        "ENDPOINTS",
        "INPUT_CLUSTERS",
        "MODELS_INFO",
        "OUTPUT_CLUSTERS",
        "PROFILE_ID",
    ]:
        setattr(zhaquirks_consts, const, const.lower())
    zhaquirks.const = zhaquirks_consts

    # Reload quirk modules so they see the stubbed zigpy tree.
    sys.modules.pop("custom_zha_quirks.ubisys_common", None)
    sys.modules.pop("custom_zha_quirks.ubisys_d1", None)
    common = importlib.import_module("custom_zha_quirks.ubisys_common")
    d1 = importlib.import_module("custom_zha_quirks.ubisys_d1")

    yield SimpleNamespace(common=common, d1=d1, CustomCluster=CustomCluster)

    # Clean up and restore original modules
    sys.modules.pop("custom_zha_quirks.ubisys_common", None)
    sys.modules.pop("custom_zha_quirks.ubisys_d1", None)
    for name in stub_names:
        sys.modules.pop(name, None)
        if saved[name] is not None:
            sys.modules[name] = saved[name]


@pytest.mark.asyncio
async def test_device_setup_cluster_injects_manufacturer(ubisys_quirk_modules):
    common = ubisys_quirk_modules.common
    cluster = common.UbisysDeviceSetup()

    result = await cluster.read_attributes([0x0000], manufacturer=None)
    assert result["attrs"] == [0x0000]
    assert cluster.read_history == [common.UBISYS_MANUFACTURER_CODE]

    await cluster.write_attributes({0x0001: b"\x00"})
    assert cluster.write_history == [
        ({0x0001: b"\x00"}, common.UBISYS_MANUFACTURER_CODE)
    ]


@pytest.mark.asyncio
async def test_d1_ballast_configuration_respects_manufacturer_arg(ubisys_quirk_modules):
    d1 = ubisys_quirk_modules.d1
    cluster = d1.UbisysBallastConfiguration()

    await cluster.read_attributes(["ballast_min_level"])
    # No manufacturer code should be forced for standard ballast attributes.
    assert cluster.read_history == [None]

    await cluster.write_attributes({"ballast_min_level": 5}, manufacturer=0x9999)
    assert cluster.write_history[-1] == ({"ballast_min_level": 5}, 0x9999)
