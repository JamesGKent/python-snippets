#!python3
import memtkinter as tk
from memtkinter import ttk

from commctrl import LVM_GETITEMTEXT, LVM_GETITEMCOUNT, LVM_GETNEXTITEM, LVNI_SELECTED
import ctypes
import ctypes.wintypes
import os
import struct
import sys
from threading import Thread
import time
import win32api
from win32con import PAGE_READWRITE, MEM_COMMIT, MEM_RESERVE, MEM_RELEASE, PROCESS_ALL_ACCESS, WM_GETTEXTLENGTH, WM_GETTEXT
import win32gui

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
ole32 = ctypes.windll.ole32

WinEventProcType = ctypes.WINFUNCTYPE(
    None, 
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.HWND,
    ctypes.wintypes.LONG,
    ctypes.wintypes.LONG,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD
)

GetWindowThreadProcessId = user32.GetWindowThreadProcessId
VirtualAllocEx = kernel32.VirtualAllocEx
VirtualFreeEx = kernel32.VirtualFreeEx
OpenProcess = kernel32.OpenProcess
WriteProcessMemory = kernel32.WriteProcessMemory
ReadProcessMemory = kernel32.ReadProcessMemory
memcpy = ctypes.cdll.msvcrt.memcpy

WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002

EVENT_SYSTEM_FOREGROUND = 0x0003
EVENT_OBJECT_SELECTION = 0x8006
EVENT_OBJECT_SELECTIONWITHIN = 0x8009

def readListViewItems(hwnd, column_index=0):
	# Allocate virtual memory inside target process
	pid = ctypes.create_string_buffer(4)
	p_pid = ctypes.addressof(pid)
	GetWindowThreadProcessId(hwnd, p_pid) # process owning the given hwnd
	hProcHnd = OpenProcess(PROCESS_ALL_ACCESS, False, struct.unpack("i",pid)[0])
	pLVI = VirtualAllocEx(hProcHnd, 0, 4096, MEM_RESERVE|MEM_COMMIT, PAGE_READWRITE)
	pBuffer = VirtualAllocEx(hProcHnd, 0, 4096, MEM_RESERVE|MEM_COMMIT, PAGE_READWRITE)

	# Prepare an LVITEM record and write it to target process memory
	lvitem_str = struct.pack('iiiiiiiii', *[0,0,column_index,0,0,pBuffer,4096,0,0])
	lvitem_buffer = ctypes.create_string_buffer(lvitem_str)
	copied = ctypes.create_string_buffer(4)
	p_copied = ctypes.addressof(copied)
	WriteProcessMemory(hProcHnd, pLVI, ctypes.addressof(lvitem_buffer), ctypes.sizeof(lvitem_buffer), p_copied)

	# iterate items in the SysListView32 control
	num_items = win32gui.SendMessage(hwnd, LVM_GETITEMCOUNT)
	item_texts = []
	for item_index in range(num_items):
		win32gui.SendMessage(hwnd, LVM_GETITEMTEXT, item_index, pLVI)
		target_buff = ctypes.create_string_buffer(4096)
		ReadProcessMemory(hProcHnd, pBuffer, ctypes.addressof(target_buff), 4096, p_copied)
		item_texts.append(target_buff.value)

	VirtualFreeEx(hProcHnd, pBuffer, 0, MEM_RELEASE)
	VirtualFreeEx(hProcHnd, pLVI, 0, MEM_RELEASE)
	win32api.CloseHandle(hProcHnd)
	return item_texts

def getSelectedListViewItems(hwnd):
	items = []
	item = -1
	while True:
		item = win32gui.SendMessage(hwnd, LVM_GETNEXTITEM, item, LVNI_SELECTED)
		if item == -1:
			break
		items.append(item)
	return items

def getEditText(hwnd):
	# api returns 16 bit characters so buffer needs 1 more char for null and twice the num of chars
	buf_size = (win32gui.SendMessage(hwnd, WM_GETTEXTLENGTH, 0, 0) +1 ) * 2
	target_buff = ctypes.create_string_buffer(buf_size)
	win32gui.SendMessage(hwnd, WM_GETTEXT, buf_size, ctypes.addressof(target_buff))
	return target_buff.raw.decode('utf16')[:-1]# remove the null char on the end

def _normaliseText(controlText):
	'''Remove '&' characters, and lower case.
	Useful for matching control text.'''
	return controlText.lower().replace('&', '')

def _windowEnumerationHandler(hwnd, resultList):
	'''Pass to win32gui.EnumWindows() to generate list of window handle,
	window text, window class tuples.'''
	resultList.append((hwnd, win32gui.GetWindowText(hwnd), win32gui.GetClassName(hwnd)))

def searchChildWindows(currentHwnd, wantedText=None, wantedClass=None, selectionFunction=None):
	results = []
	childWindows = []
	try:
		win32gui.EnumChildWindows(currentHwnd, _windowEnumerationHandler, childWindows)
	except win32gui.error:
		# This seems to mean that the control *cannot* have child windows,
		# i.e. not a container.
		return
	for childHwnd, windowText, windowClass in childWindows:
		descendentMatchingHwnds = searchChildWindows(childHwnd)
		if descendentMatchingHwnds:
			results += descendentMatchingHwnds

		if wantedText and not _normaliseText(wantedText) in _normaliseText(windowText):
			continue
		if wantedClass and not windowClass == wantedClass:
			continue
		if selectionFunction and not selectionFunction(childHwnd):
			continue
		results.append(childHwnd)
	return results
	
def callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
    length = user32.GetWindowTextLengthA(hwnd)
    buff = ctypes.create_string_buffer(length + 1)
    user32.GetWindowTextA(hwnd, buff, length + 1)
    print(buff.value)

class App(tk.Tk):
	def __init__(self):
		tk.SoftwarePrefix = True
		tk.VendorPrefix = 'James Kent'
		tk.Tk.__init__(self, tk.HKCU, None, 'explorer-selection-logger')
		self.title('Explorer Selection and path logger')
		self.protocol("WM_DELETE_WINDOW", self.exit_handler)
		
		self.grid_columnconfigure(1, weight=1)
		self.grid_columnconfigure(3, weight=1)
		self.grid_columnconfigure(5, weight=3)
		self.grid_rowconfigure(3, weight=1)
		
		tk.Label(self, text='Path:').grid(column=1, row=1, sticky='nesw')
		self.path = tk.Entry(self)
		self.path.grid(column=2, row=1, columnspan=5, sticky='nesw')
		
		tk.Label(self, text='Files:').grid(column=1, row=2, sticky='nesw')
		self.files = tk.Listbox(self, selectmode=tk.MULTIPLE)
		self.files.grid(column=1, row=3, sticky='nesw')
		vsb = ttk.Scrollbar(self, command=self.files.yview)
		vsb.grid(column=2, row=3, sticky='nesw')
		self.files.configure(yscrollcommand=vsb.set)
		self.fmenu = tk.Menu(self, tearoff=False)
		self.fmenu.add_command(label='Copy', command=self.copy_files)
		self.files.bind('<Button-3>', self.popup)
		
		tk.Label(self, text='Selected:').grid(column=3, row=2, sticky='nesw')
		self.selected = tk.Listbox(self, selectmode=tk.MULTIPLE)
		self.selected.grid(column=3, row=3, sticky='nesw')
		vsb = ttk.Scrollbar(self, command=self.selected.yview)
		vsb.grid(column=4, row=3, sticky='nesw')
		self.selected.configure(yscrollcommand=vsb.set)
		self.smenu = tk.Menu(self, tearoff=False)
		self.smenu.add_command(label='Copy', command=self.copy_selected)
		self.selected.bind('<Button-3>', self.popup)
		
		tk.Label(self, text='Selected with path:').grid(column=5, row=2, sticky='nesw')
		self.selectedpaths = tk.Listbox(self, selectmode=tk.MULTIPLE)
		self.selectedpaths.grid(column=5, row=3, sticky='nesw')
		vsb = ttk.Scrollbar(self, command=self.selectedpaths.yview)
		vsb.grid(column=6, row=3, sticky='nesw')
		self.selectedpaths.configure(yscrollcommand=vsb.set)
		self.spmenu = tk.Menu(self, tearoff=False)
		self.spmenu.add_command(label='Copy', command=self.copy_selectedpaths)
		self.selectedpaths.bind('<Button-3>', self.popup)
		
		ttk.Button(self, text='Copy All', command=self.copy_all).grid(column=1, row=4, columnspan=6, sticky='nesw')
		
		t = Thread(target=self.msgloop)
		t.daemon=True
		t.start()
		
	def popup(self, event):
		if event.widget == self.files:
			self.fmenu.post(event.x_root, event.y_root)
		elif event.widget == self.selected:
			self.smenu.post(event.x_root, event.y_root)
		elif event.widget == self.selectedpaths:
			self.spmenu.post(event.x_root, event.y_root)

	def msgloop(self):
		ole32.CoInitialize(0)
		
		self.foregroundEventProc = WinEventProcType(self.foreground_callback)
		
		user32.SetWinEventHook.restype = ctypes.wintypes.HANDLE
		# hook for foreground window change
		self.hook1 = user32.SetWinEventHook(
			EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
			0, self.foregroundEventProc,
			0, 0,
			WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS
		)
		if self.hook1 == 0:
			self.path.delete(0, tk.END)
			self.path.insert(tk.END, 'SetWinEventHook 1 failed')
			return
		
		self.selectionEventProc = WinEventProcType(self.selection_callback)
		# hook to catch changes in selection once have explorer window
		self.hook2 = user32.SetWinEventHook(
			EVENT_OBJECT_SELECTION, EVENT_OBJECT_SELECTIONWITHIN,
			0, self.selectionEventProc,
			0, 0,
			WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS
		)
		if self.hook2 == 0:
			self.path.delete(0, tk.END)
			self.path.insert(tk.END, 'SetWinEventHook 2 failed')
			return
		
		msg = ctypes.wintypes.MSG()
		# find way to kill this loop
		while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
			user32.TranslateMessageW(msg)
			user32.DispatchMessageW(msg)
		
	def foreground_callback(self, hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
		if (hwnd != 0):
			if (win32gui.GetClassName(hwnd) == 'CabinetWClass'): # the main explorer window
				self.hwnd = hwnd
				self.after_idle(self.background_task, hwnd)
			else:
				self.hwnd = 0
		
	def selection_callback(self, hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
		if self.hwnd != 0:
			self.after_idle(self.background_task, self.hwnd)
		
	def background_task(self, hwnd):
		if (hwnd != 0):
			if (win32gui.GetClassName(hwnd) == 'CabinetWClass'): # the main explorer window
				children = list(set(searchChildWindows(hwnd)))
				addr_edit = None
				file_view = None
				for child in children:
					if (win32gui.GetClassName(child) == 'ComboBoxEx32'): # the address bar
						addr_children = list(set(searchChildWindows(child)))
						for addr_child in addr_children:
							if (win32gui.GetClassName(addr_child) == 'Edit'):
								addr_edit = addr_child
								break
						pass
					elif (win32gui.GetClassName(child) == 'SysListView32'): # the list control within the window that shows the files
						file_view = child
				if addr_edit:
					path = getEditText(addr_edit)
				else:
					path = 'Error getting path'
				print('repr path: %s' % repr(path))
				self.path.delete(0, tk.END)
				self.path.insert(tk.END, path)

				self.files.delete(0, tk.END)
				self.selected.delete(0, tk.END)
				self.selectedpaths.delete(0, tk.END)
				if file_view:
					files = [item.decode('utf8') for item in readListViewItems(file_view)]
					for f in files:
						self.files.insert(tk.END, f)
					indexes = getSelectedListViewItems(file_view)
					for index in indexes:
						self.selected.insert(tk.END, files[index])
						self.selectedpaths.insert(tk.END, os.path.join(path, files[index]))

	def copy_all(self):
		data = 'path,%s\nfiles,selected,selected with path\n' % self.path.get()
		i = 0
		while True:
			f = self.files.get(i)
			s = self.selected.get(i)
			sp = self.selectedpaths.get(i)
			if f == '' and s == '' and sp == '':
				break
			data += '%s,%s,%s\n' % (f,s,sp)
			i += 1
		self.clipboard_clear()
		self.clipboard_append(data)
		
	def copy_files(self, event=None):
		data = 'path,%s\nfiles\n' % self.path.get()
		i = 0
		while True:
			f = self.files.get(i)
			if f == '':
				break
			data += '%s\n' % f
			i += 1
		self.clipboard_clear()
		self.clipboard_append(data)
		
	def copy_selected(self, event=None):
		data = 'path,%s\nselected\n' % self.path.get()
		i = 0
		while True:
			s = self.selected.get(i)
			if s == '':
				break
			data += '%s\n' % s
			i += 1
		self.clipboard_clear()
		self.clipboard_append(data)
		
	def copy_selectedpaths(self, event=None):
		data = 'path,%s\nselected with path\n' % self.path.get()
		i = 0
		while True:
			sp = self.selectedpaths.get(i)
			if sp == '':
				break
			data += '%s\n' % sp
			i += 1
		self.clipboard_clear()
		self.clipboard_append(data)
		
	def exit_handler(self):
		user32.UnhookWinEvent(self.hook1)
		user32.UnhookWinEvent(self.hook2)
		ole32.CoUninitialize()
		self.destroy()
		sys.exit(0)
			
if __name__ == '__main__':
	app = App()
	app.mainloop()
	