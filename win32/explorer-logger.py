#!python3
'''
simple script to get details of the files and selection in a windows explorer window
uses calls to the win32 api
'''
import win32gui, time
from win32con import PAGE_READWRITE, MEM_COMMIT, MEM_RESERVE, MEM_RELEASE, PROCESS_ALL_ACCESS, WM_GETTEXTLENGTH, WM_GETTEXT
from commctrl import LVM_GETITEMTEXT, LVM_GETITEMCOUNT, LVM_GETNEXTITEM, LVNI_SELECTED
import os
import struct
import ctypes
import win32api

GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
VirtualAllocEx = ctypes.windll.kernel32.VirtualAllocEx
VirtualFreeEx = ctypes.windll.kernel32.VirtualFreeEx
OpenProcess = ctypes.windll.kernel32.OpenProcess
WriteProcessMemory = ctypes.windll.kernel32.WriteProcessMemory
ReadProcessMemory = ctypes.windll.kernel32.ReadProcessMemory
memcpy = ctypes.cdll.msvcrt.memcpy

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

def getSelectedListViewItem(hwnd):
	return win32gui.SendMessage(hwnd, LVM_GETNEXTITEM, -1, LVNI_SELECTED)
	
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

def searchChildWindows(currentHwnd,
			   wantedText=None,
			   wantedClass=None,
			   selectionFunction=None):
	results = []
	childWindows = []
	try:
		win32gui.EnumChildWindows(currentHwnd,
					  _windowEnumerationHandler,
					  childWindows)
	except win32gui.error:
		# This seems to mean that the control *cannot* have child windows,
		# i.e. not a container.
		return
	for childHwnd, windowText, windowClass in childWindows:
		descendentMatchingHwnds = searchChildWindows(childHwnd)
		if descendentMatchingHwnds:
			results += descendentMatchingHwnds

		if wantedText and \
			not _normaliseText(wantedText) in _normaliseText(windowText):
				continue
		if wantedClass and \
			not windowClass == wantedClass:
				continue
		if selectionFunction and \
			not selectionFunction(childHwnd):
				continue
		results.append(childHwnd)
	return results

w=win32gui

while True:
	time.sleep(5)
	window = w.GetForegroundWindow()
	print("window: %s" % window)
	if (window != 0):
		if (w.GetClassName(window) == 'CabinetWClass'): # the main explorer window
			print("class: %s" % w.GetClassName(window))
			print("text: %s " %w.GetWindowText(window))
			children = list(set(searchChildWindows(window)))
			addr_edit = None
			file_view = None
			for child in children:
				if (w.GetClassName(child) == 'ComboBoxEx32'): # the address bar
					addr_children = list(set(searchChildWindows(child)))
					for addr_child in addr_children:
						if (w.GetClassName(addr_child) == 'Edit'):
							addr_edit = addr_child
					pass
				elif (w.GetClassName(child) == 'SysListView32'): # the list control within the window that shows the files
					file_view = child
			if addr_edit:
				path = getEditText(addr_edit)
			else:
				print('something went wrong - no address bar found')
				path = ''

			if file_view:
				files = [item.decode('utf8') for item in readListViewItems(file_view)]
				indexes = getSelectedListViewItems(file_view)
				print('path: %s' % path)
				print('files: %s' % files)
				print('selected files:')
				for index in indexes:
					print("\t%s - %s" % (files[index], os.path.join(path, files[index])))
			else:
				print('something went wrong - no file view found')
