import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()

handlers = [
    ("GETGAMEOPPRPS", 0x733d70),
    ("GETGAMEOPPLEVELRPS", 0x733ff0),
    ("GETGAMEOPPPVRPS", 0x734220),
    ("GETDUELNUMCARDSRPS", 0x751770),
    ("GETDUELBEGINGUSRPS", 0x751a80),
    ("SETGAMEREADY", 0x733650),
    ("BEGINTURN", 0x734890),
    ("ENDTURN", 0x7363c0),
    ("SENDACTUALPASS", 0x735c40),
    ("GETCARDHANDRPS", 0x7365e0),
    ("GETCARDTYPERPS", 0x739440),
    ("GETCARDPOWERRPS", 0x7398a0),
    ("GETCARDESPRPS", 0x739da0),
    ("GETCARDESPFRPS", 0x746470),
    ("SENDATTACKWARN", 0x73c760),
    ("DEDUCTPV", 0x73d4b0),
    ("DEDUCTPVOPP", 0x742250),
    ("KILLCARD", 0x73dcb0),
    ("KILLCARDOPP", 0x7427b0),
    ("SHOWCARDOPPACT", 0x73e960),
    ("SHOWCARDVEERACT", 0x741000),
    ("SHOWCARDUNVEERACT", 0x742070),
    ("SETCATTACKRPS", 0x750160),
    ("SETCDEFENDRPS", 0x7501e0),
]

for name, va in handlers:
    fs, fe = exe.func_of(va)
    strs = []
    for ins, note in exe.disasm(fs, fe):
        if note and 'L"' in note:
            strs.append(note.strip())
    print(f"{name:22} @ {va:#x} (len {fe-fs:4}): {strs[:6]}")
