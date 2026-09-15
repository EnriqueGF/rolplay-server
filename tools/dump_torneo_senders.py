from rpexe import Exe
import re

exe = Exe()

targets = [
    ("SETPLAYERREADY", 0x7257c1),
    ("SETPLAYERUNREADY", 0x725846),
    ("SURRENDERME", 0x725ef4),
    ("UNJOINGAME", 0x7260b3),
    ("SENDACTUALPASS", 0x726599),
    ("SHOWCARDUNVEERO", 0x726f6c),
    ("SHOWKILLCARD", 0x7271d3),
    ("SENDENDTURN", 0x727985),
    ("SHOWCARDOPPSIT", 0x727e29),
    ("GETUSERLEVEL", 0x728c70),
    ("GETDUELNUMCARDS", 0x728cb6),
    ("GETDUELBEGINGUS", 0x728d2d),
    ("MSGDUEL", 0x728da3),
    ("SETCATTACK", 0x72c027),
    ("SETCDEFEND", 0x72c62e),
    ("SENDATTACK", 0x72cea3),
    ("SETPINGGAME", 0x732cc4),
    ("GETCARDCOUNT", 0x73379b),
    ("GETCARDCOUNTOPP", 0x73381e),
    ("GETGAMEOPP", 0x733bc8),
    ("GETGAMEOPPLEVEL", 0x733c46),
    ("GETGAMEOPPPV", 0x733cb8),
    ("GETCARDHAND", 0x734891),
    ("GETCARDTYPE", 0x734914),
    ("GETCARDPOWER", 0x734997),
    ("GETCARDESP", 0x734a1a),
    ("GETCARDESPF", 0x734a9d),
    ("SHOWCARDVEER", 0x73ad0b),
    ("DEADME", 0x7440e2),
    ("SHOWCARDOPP", 0x745e31),
    ("SETAMUVAL", 0x748615),
    ("INVKGIRMONSOK", 0x74945f),
    ("KILLCARD", 0x74aa41),
    ("REMAMUVAL", 0x74bd22),
    ("GETGOLDBET", 0x75156a),
    ("GETDUELNUMCARDBET", 0x7515e8),
    ("GETGOLDBETOPP", 0x75165a),
    ("GETDUELNUMCARDBETOPP", 0x7516cc),
]

for name, va in targets:
    fs, fe = exe.func_of(va)
    # Find all string references in this function
    strs = []
    for ins, note in exe.disasm(fs, fe):
        m = re.search(r'; L"([^"]+)"', note)
        if m:
            strs.append(m.group(1))
    print(f"=== {name} (func {fs:#x}..{fe:#x}) ===")
    print("  Strings: " + " | ".join(repr(s) for s in strs))
