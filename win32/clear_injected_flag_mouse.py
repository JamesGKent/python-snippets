import atexit
import ctypes
from ctypes import c_int, c_uint, c_uint32, c_long, Structure, CFUNCTYPE, POINTER
from ctypes.wintypes import DWORD, BOOL, HWND, HHOOK, MSG, WPARAM, LPARAM
import threading

LPMSG = POINTER(MSG)

user32 = ctypes.WinDLL('user32', use_last_error = True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error = True)

class MSLLHOOKSTRUCT(Structure):
	_fields_ = [("x", c_long), ("y", c_long),
				('data', c_uint32), ("flags", DWORD),
				("time", c_int), ('extrainfo', c_uint32), ]

LowLevelMouseProc = CFUNCTYPE(c_int, WPARAM, LPARAM, POINTER(MSLLHOOKSTRUCT))

SetWindowsHookEx = user32.SetWindowsHookExA
#SetWindowsHookEx.argtypes = [c_int, LowLevelMouseProc, c_int, c_int]
SetWindowsHookEx.restype = HHOOK

CallNextHookEx = user32.CallNextHookEx
#CallNextHookEx.argtypes = [c_int , c_int, c_int, POINTER(MSLLHOOKSTRUCT)]
CallNextHookEx.restype = c_int

UnhookWindowsHookEx = user32.UnhookWindowsHookEx
UnhookWindowsHookEx.argtypes = [HHOOK]
UnhookWindowsHookEx.restype = BOOL

GetMessage = user32.GetMessageW
GetMessage.argtypes = [LPMSG, c_int, c_int, c_int]
GetMessage.restype = BOOL

TranslateMessage = user32.TranslateMessage
TranslateMessage.argtypes = [LPMSG]
TranslateMessage.restype = BOOL

DispatchMessage = user32.DispatchMessageW
DispatchMessage.argtypes = [LPMSG]

PostThreadMessage = user32.PostThreadMessageW
WM_QUIT = 0x0012
GetCurrentThreadId = kernel32.GetCurrentThreadId

NULL = c_int(0)

class TranslateInjectedMouse(threading.Thread):
	daemon=True
	def run(self):
		self.t_id = GetCurrentThreadId()
		def low_level_mouse_handler(nCode, wParam, lParam):
			print("handler")
			lParam.contents.flags &= 0x11111100
			return CallNextHookEx(NULL, nCode, wParam, lParam)

		WH_MOUSE_LL = c_int(14)
		mouse_callback = LowLevelMouseProc(low_level_mouse_handler)
		self.mouse_hook = SetWindowsHookEx(WH_MOUSE_LL, mouse_callback, user32._handle, NULL)

		# Register to remove the hook when the interpreter exits. Unfortunately a
		# try/finally block doesn't seem to work here.
		atexit.register(UnhookWindowsHookEx, self.mouse_hook)

		msg = ctypes.wintypes.MSG()
		while GetMessage(ctypes.byref(msg), NULL, NULL, NULL) != 0:
			TranslateMessage(msg)
			DispatchMessage(msg)
			
	def stop(self):
		PostThreadMessage(self.t_id, WM_QUIT, 0, 0)
		UnhookWindowsHookEx(self.mouse_hook)

if __name__ == '__main__':
	# this is all you need to translate in background
	t = TranslateInjectedMouse()
	t.start()
	
	# below this is test code to create clicks
	import time
	mouse_event = user32.mouse_event
	MOUSEEVENTF_LEFTDOWN = 0x0002
	MOUSEEVENTF_LEFTUP = 0x0004

	while True:
		try:
			time.sleep(1)
			mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
			
			mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
		except KeyboardInterrupt:
			if t.is_alive():
				t.stop()
			else:
				break