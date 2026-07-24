import os
from datetime import datetime


INES_HEADER = 0x10

TILESET_REGIONS = {
    "Underground": (13, 0xA577, 0xBC2B),
    "2P VS": (14, 0xC4B6, 0xC571),
    "Plains": (15, 0xA4F9, 0xBDDB),
    "Hills": (16, 0xA577, 0xB9CE),
    "High Ice": (17, 0xA810, 0xBFA7),
    "Water": (18, 0xAB8D, 0xB9A8),
    "Sky": (19, 0xAA5F, 0xBFDC),
    "Desert": (20, 0xAF26, 0xBDB6),
    "Fortress": (21, 0xA7E7, 0xBFFF),
    "Airship": (23, 0xABF7, 0xBEFB),
}


def cpu_to_prg(bank, cpu_addr):
    return bank * 0x2000 + (cpu_addr & 0x1FFF)


def region_values(region_name, regions=None):
    info = (regions or TILESET_REGIONS)[region_name]
    if isinstance(info, dict):
        return info["bank"], info["start"], info["end"]
    return info


def get_region_bounds(region_name, regions=None, ines_header=INES_HEADER):
    bank, start, end = region_values(region_name, regions)
    return (
        cpu_to_prg(bank, start) + ines_header,
        cpu_to_prg(bank, end) + ines_header,
    )


def get_region_bytes(rom_path, region_name, regions=None, ines_header=INES_HEADER):
    rom_start, rom_end = get_region_bounds(region_name, regions, ines_header)
    with open(rom_path, "rb") as handle:
        rom = handle.read()
    return rom[rom_start:rom_end + 1]


def backup_root(rom_path, profile_name=None):
    root = os.path.join(os.path.dirname(rom_path), "Backups")
    if profile_name:
        safe_name = "".join(
            "_" if char in '<>:"/\\|?*' else char
            for char in profile_name
        ).strip(" .") or "Profile"
        root = os.path.join(root, safe_name)
    return root


def backup_roots(rom_path, profile_filename, legacy_profile_name=None):
    roots = [backup_root(rom_path, profile_filename)]
    if legacy_profile_name:
        legacy_root = backup_root(rom_path, legacy_profile_name)
        if os.path.normcase(legacy_root) != os.path.normcase(roots[0]):
            roots.append(legacy_root)
    return roots


def region_backups(rom_path, region_name, profile_filename, legacy_profile_name=None):
    files = []
    for root in backup_roots(rom_path, profile_filename, legacy_profile_name):
        region_dir = os.path.join(root, region_name)
        if not os.path.isdir(region_dir):
            continue
        files.extend(
            os.path.join(region_dir, filename)
            for filename in os.listdir(region_dir)
            if filename.lower().endswith(".lvls")
        )
    return sorted(set(files), key=os.path.getmtime, reverse=True)


def backup_tileset(
    rom_path,
    region_name,
    regions=None,
    ines_header=INES_HEADER,
    profile_name=None,
):
    data = get_region_bytes(rom_path, region_name, regions, ines_header)
    backup_dir = os.path.join(backup_root(rom_path, profile_name), region_name)
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = os.path.join(backup_dir, f"{region_name}_{timestamp}.lvls")
    with open(backup_file, "wb") as handle:
        handle.write(data)
    return backup_file


def restore_tileset(
    rom_path,
    region_name,
    backup_file,
    regions=None,
    ines_header=INES_HEADER,
):
    rom_start, rom_end = get_region_bounds(region_name, regions, ines_header)
    expected_size = rom_end - rom_start + 1
    with open(backup_file, "rb") as handle:
        data = handle.read()
    if len(data) != expected_size:
        raise ValueError(
            f"Backup size mismatch. Expected {expected_size}, got {len(data)}."
        )
    with open(rom_path, "r+b") as handle:
        handle.seek(rom_start)
        handle.write(data)


def backup_all_tilesets(
    rom_path,
    regions=None,
    ines_header=INES_HEADER,
    profile_name=None,
):
    return [
        backup_tileset(
            rom_path,
            region,
            regions,
            ines_header,
            profile_name,
        )
        for region in (regions or TILESET_REGIONS)
    ]


def restore_all_tilesets(
    rom_path,
    regions=None,
    ines_header=INES_HEADER,
    profile_name=None,
    legacy_profile_name=None,
):
    restored = []
    for region in (regions or TILESET_REGIONS):
        backups = region_backups(
            rom_path, region, profile_name, legacy_profile_name
        )
        if not backups:
            continue
        newest = backups[0]
        restore_tileset(rom_path, region, newest, regions, ines_header)
        restored.append(region)
    return restored
