import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, win32api, win32con, ctypes

d = RPDriver()
pid = d.get_rp_pid()
h = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)

buf = ctypes.create_string_buffer(4)
bytesRead = ctypes.c_size_t()
ctypes.windll.kernel32.ReadProcessMemory(h.handle, 0x7ce260, buf, 4, ctypes.byref(bytesRead))
inst = int.from_bytes(buf.raw[:4], 'little')

PAGE_EXECUTE_READWRITE = 0x40
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000

remote_mem = ctypes.windll.kernel32.VirtualAllocEx(h.handle, 0, 1024, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)

# Layout in remote_mem:
# offset 0..63: shellcode
# offset 64..79: BSTR string data (Unicode "BEGINTURN\0")
# offset 80..83: BSTR pointer pointing to offset 64
# offset 84..87: ByRef pointer pointing to offset 80

bstr_data = "BEGINTURN\0".encode('utf-16le')
bstr_len = (len(bstr_data) - 2).to_bytes(4, 'little') # BSTR length prefix
full_bstr = bstr_len + bstr_data

ctypes.windll.kernel32.WriteProcessMemory(h.handle, remote_mem + 60, full_bstr, len(full_bstr), ctypes.byref(bytesRead))

p_bstr = remote_mem + 64 # points to first char after 4-byte length prefix
ctypes.windll.kernel32.WriteProcessMemory(h.handle, remote_mem + 80, p_bstr.to_bytes(4, 'little'), 4, ctypes.byref(bytesRead))

p_byref = remote_mem + 80 # pointer to BSTR pointer
ctypes.windll.kernel32.WriteProcessMemory(h.handle, remote_mem + 84, p_byref.to_bytes(4, 'little'), 4, ctypes.byref(bytesRead))

# Shellcode:
# push p_byref (offset 84)
# push inst
# mov ecx, [0x7ce260]
# mov eax, [ecx]
# call [eax + 0x718]
# ret

shellcode = bytearray()
shellcode += b'\x68' + p_byref.to_bytes(4, 'little') # push p_byref
shellcode += b'\x68' + inst.to_bytes(4, 'little') # push inst
shellcode += b'\x8b\x0d' + (0x7ce260).to_bytes(4, 'little') # mov ecx, [0x7ce260]
shellcode += b'\x8b\x01' # mov eax, [ecx]
shellcode += b'\xff\x90\x18\x07\x00\x00' # call [eax + 0x718]
shellcode += b'\xc3' # ret

ctypes.windll.kernel32.WriteProcessMemory(h.handle, remote_mem, (ctypes.c_char * len(shellcode))(*shellcode), len(shellcode), ctypes.byref(bytesRead))

h_thread = ctypes.windll.kernel32.CreateRemoteThread(h.handle, 0, 0, remote_mem, 0, 0, 0)
ctypes.windll.kernel32.WaitForSingleObject(h_thread, 5000)

exit_code = ctypes.c_ulong()
ctypes.windll.kernel32.GetExitCodeThread(h_thread, ctypes.byref(exit_code))
print(f"Remote thread exit code: {exit_code.value:#010x} ({exit_code.value})")

ctypes.windll.kernel32.CloseHandle(h_thread)
ctypes.windll.kernel32.VirtualFreeEx(h.handle, remote_mem, 0, 0x8000)
win32api.CloseHandle(h)
