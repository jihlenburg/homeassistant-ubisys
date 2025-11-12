import asyncio
import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.ubisys.helpers import async_write_and_verify_attrs


class FakeCluster:
    def __init__(self, read_map):
        self._read_map = read_map
        self._writes = []

    async def write_attributes(self, attrs, manufacturer=None):
        # record and pretend success
        self._writes.append((attrs, manufacturer))
        await asyncio.sleep(0)
        return [attrs]  # placeholder success structure

    async def read_attributes(self, attr_ids, manufacturer=None):
        await asyncio.sleep(0)
        return [{aid: self._read_map.get(aid) for aid in attr_ids}]


@pytest.mark.asyncio
async def test_write_verify_success():
    # On readback we get the same values
    cluster = FakeCluster({0x1234: 7})
    await async_write_and_verify_attrs(cluster, {0x1234: 7})


@pytest.mark.asyncio
async def test_write_verify_mismatch_raises():
    cluster = FakeCluster({0x1234: 1})
    with pytest.raises(HomeAssistantError):
        await async_write_and_verify_attrs(cluster, {0x1234: 2}, retries=0)

