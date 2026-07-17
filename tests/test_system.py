from warden.core import system


def test_get_system_info_returns_expected_shape():
    info = system.get_system_info()
    assert info["os"]
    assert info["cpu_count"] >= 1
    assert info["memory_total_gb"] > 0
    assert isinstance(info["disks"], list)
    assert len(info["disks"]) >= 1
    disk = info["disks"][0]
    assert {"mountpoint", "total_gb", "used_gb", "free_gb"} <= set(disk.keys())
