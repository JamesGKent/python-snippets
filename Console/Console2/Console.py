#!python3

import ctypes, sys, subprocess

Kernel32 = ctypes.windll.Kernel32

class Console():
	def __init__(self, ischild=True):
		if ischild:
			# try allocate new console
			result = Kernel32.AllocConsole()
			if result > 0:
				# if we succeed open handle to the console output
				sys.stdout = open('CONOUT$', mode='w')
		else:
			# if frozen we assume its names Console.exe
			# note that when frozen 'Win32GUI' must be used as a base
			if hasattr(sys, 'frozen'):
				args = ['Console.exe']
			else:
				# otherwise we use the console free version of python
				args = ['pythonw.exe', __file__]
			self.p = subprocess.Popen(
				args,
				stdin=subprocess.PIPE
				)
			return
		while True:
			data = sys.stdin.read(1)
			if not data:
				break
			sys.stdout.write(data)
			
	def write(self, data):
		self.p.stdin.write(data.encode('utf8'))
		self.p.stdin.flush()
		
if (__name__ == '__main__'):
	p = Console()