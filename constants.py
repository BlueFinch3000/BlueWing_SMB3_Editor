# constants.py

import os

APP_NAME = "Blue Wing"
APP_VERSION = "1.6"
APP_TITLE = f"{APP_NAME} - SMB3 Editor (v{APP_VERSION})"


INES_HEADER = 0x10
FULLLEVELNAMES = 0x14008 + INES_HEADER
LEVELNAME_TILES = 0x14068 + INES_HEADER
POINTER_TO_ROM_OFFSET = 0x34000


LEVELNAME_PALETTE_OFFSET = 0x36C52 + INES_HEADER
TILE_PALETTE_OFFSET = (LEVELNAME_PALETTE_OFFSET - 0x80)

NES_RGB = {
    0x00:"#7C7C7C",0x01:"#0000FC",0x02:"#0000BC",0x03:"#4428BC",
    0x04:"#940084",0x05:"#A80020",0x06:"#A81000",0x07:"#881400",
    0x08:"#503000",0x09:"#007800",0x0A:"#006800",0x0B:"#005800",
    0x0C:"#004058",0x0D:"#000000",0x0E:"#000000",0x0F:"#000000",

    0x10:"#BCBCBC",0x11:"#0078F8",0x12:"#0058F8",0x13:"#6844FC",
    0x14:"#D800CC",0x15:"#E40058",0x16:"#F83800",0x17:"#E45C10",
    0x18:"#AC7C00",0x19:"#00B800",0x1A:"#00A800",0x1B:"#00A844",
    0x1C:"#008888",0x1D:"#000000",0x1E:"#000000",0x1F:"#000000",

    0x20:"#F8F8F8",0x21:"#3CBCFC",0x22:"#6888FC",0x23:"#9878F8",
    0x24:"#F878F8",0x25:"#F85898",0x26:"#F87858",0x27:"#FCA044",
    0x28:"#F8B800",0x29:"#B8F818",0x2A:"#58D854",0x2B:"#58F898",
    0x2C:"#00E8D8",0x2D:"#787878",0x2E:"#000000",0x2F:"#000000",

    0x30:"#FCFCFC",0x31:"#A4E4FC",0x32:"#B8B8F8",0x33:"#D8B8F8",
    0x34:"#F8B8F8",0x35:"#F8A4C0",0x36:"#F0D0B0",0x37:"#FCE0A8",
    0x38:"#F8D878",0x39:"#D8F878",0x3A:"#B8F8B8",0x3B:"#B8F8D8",
    0x3C:"#00FCFC",0x3D:"#F8D8F8",0x3E:"#000000",0x3F:"#000000"
}

PALETTE_WORLD_NAMES = (
    "World 1",
    "World 2",
    "World 3",
    "World 4"
)
WORLD_CHAR_MAP = {
    0x58:"S",
    0x59:"B",
    0x5A:"Y",
    0x5B:"H",
    0x5C:"K",
    0x5D:"F",
    0x5E:"J",
    0x5F:"Q",
    0x6A:"V",
    0x6B:"!",
    0xBA:"M",
    0xBC:"A",
    0xD8:"W",
    0xD9:"P",
    0xDA:"U",
    0xDB:"N",
    0xE8:"E",
    0xE9:"R",
    0xEA:"T",
    0xEB:"G",
    0xEC:"L",
    0xED:"C",
    0xEE:"D",
    0xF0:"O",
    0xFB:"X",
    0xFC:"I",
    0xFD:"Z",
    0xFE:"_",
    0xFF:" "
}

WORLD_TEXT_MAP = {
    v:k for k,v in WORLD_CHAR_MAP.items()
}

CHAR_MAP = {
    0x91:"A",0x93:"B",0x95:"C",0x97:"D",0x99:"E",0x9B:"F",0x9D:"G",
    0xE1:"H",0xE3:"I",0xE5:"J",0xE7:"K",0xE9:"L",0xEB:"M",0xED:"N",
    0xEF:"O",0xF1:"P",0xF3:"R",0xF5:"S",0xF7:"T",0xF9:"U",0xFB:"V",
    0xC9:"W",0xCB:"X",0xD9:"Y",0xDB:"Z",0x6B:"'",0x6D:"!",0x41:" ",
    0x4F:"1",0x23:"2",0x1B:"3",0x25:"4"
}
TEXT_MAP = {v:k for k,v in CHAR_MAP.items()}
VALID_CHARS = set(TEXT_MAP.keys())
WORLD_VALID_CHARS = set(WORLD_TEXT_MAP.keys())

TEXT_TABLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "text_tables")


def load_hex_text_table(name):
    path = os.path.join(TEXT_TABLE_DIR, f"{name}.tbl")
    byte_to_text = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith(("#", ";")):
                continue
            if "=" not in line:
                raise ValueError(f"Invalid text table line {line_number} in {path}")
            hex_value, text = line.split("=", 1)
            byte_to_text[int(hex_value.strip(), 16)] = text
    text_to_byte = {}
    for value, text in byte_to_text.items():
        text_to_byte.setdefault(text, value)
    return {
        "decode": byte_to_text,
        "encode": text_to_byte,
        "pad": text_to_byte.get(" ", text_to_byte.get("_", 0x00)),
    }


CUSTOM_TEXT_TABLES = {
    "MAIN": load_hex_text_table("MAIN"),
}

CUSTOM_GAME_TEXT_TABLES = tuple(CUSTOM_TEXT_TABLES.keys())
GAME_TEXT_TABLES = ("level", "world", "ascii") + CUSTOM_GAME_TEXT_TABLES

TILE_NAMES = {
0x03:"Level 1",0x04:"Level 2",0x05:"Level 3",0x06:"Level 4",
0x07:"Level 5",0x08:"Level 6",0x09:"Level 7",0x0A:"Level 8",
0x0B:"Level 9",0x0C:"Level 10",0x0D:"Bonus Level 1",0x0E:"Bonus Level 2",
0x0F:"Bonus Level 3",0x10:"Bonus Level 4",0x11:"Bonus Level 5",
0x12:"Bonus Level 6",0x13:"Bonus Level 7",0x14:"Bonus Level 8",
0x15:"Bonus Level 9",0x16:"Bonus Level 10",0x50:"Mushroom House A",
0x58:"Large Fort",0x59:"Small Fort",0x5F:"Medium Fort",0x63:"Tall Grass A (Active)",
0x64:"Tall Grass B (Inactive)",0x67:"Normal Fort",0x68:"Quicksand",
0x6A:"Chance Fort",0xBD:"Mushroom House B",0xDF:"Weird Fort A",
0xE0:"Mushroom House C",0xEB:"Weird Fort B"
}

WORLDS = {
"World 1":[f"Level {i}" for i in range(1,12)] + ["NULL"],
"World 2":[f"Level {i}" for i in range(1,9)] + ["Grass A","Grass B"] + ["NULL", "NULL"],
"World 3":[f"Level {i}" for i in range(1,13)],
"World 4":[f"Level {i}" for i in range(1,13)]
}

WORLD_BANNERS = {
    "World 1": {"addr": 0x154DD, "max": 15}, # paradise plains
    "World 2": {"addr": 0x154F0, "max": 11}, # dirty dunes
    "World 3": {"addr": 0x154FF, "max": 12}, # horrid hills
    "World 4": {"addr": 0x1550F, "max": 18}, # finchtastic fiasco
}

