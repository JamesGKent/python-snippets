import ctypes, sys, subprocess, threading, traceback

Kernel32 = ctypes.windll.Kernel32

class Console():
	def __init__(self, ischild=True, outputonly=True):
		if ischild:
			# detach console if it is attached
			Kernel32.FreeConsole()
			# try allocate new console
			result = Kernel32.AllocConsole()
			if result > 0:
				# if we succeed open handle to the console output
				self.stdout = open('CONOUT$', mode='w')
				# check if sys.stdout is a pipe instead of a tty
				if not sys.stdout.isatty():
					# is pipe so open handle to console input
					self.stdin = open('CONIN$', mode='r')
					# start thread to read from console input
					self.cin_thread = threading.Thread(target=self._cin_loop)
					self.cin_thread.daemon = True
					self.cin_thread.start()
			self._cout_loop()
		else:
			# if frozen we assume its names Console.exe
			if hasattr(sys, 'frozen'):
				args = ['Console.exe']
			else: # otherwise use python
				args = [sys.executable, __file__]
			kwargs = {'stdin':subprocess.PIPE}
			if not outputonly:
				kwargs['stdout'] = subprocess.PIPE
			self.p = subprocess.Popen(args, **kwargs)
		
	def _cin_loop(self):
		'''reads from the visible console and writes
		it to the pipe back to parent process'''
		while True:
			data = self.stdin.read(1)
			if not data:
				break
			sys.stdout.write(data)
			sys.stdout.flush()
			
	def _cout_loop(self):
		'''reads from the pipe from parent process
		and writes it to the visible console'''
		while True:
			data = sys.stdin.read(1)
			if not data:
				break
			self.stdout.write(data)
			
	def write(self, data):
		self.p.stdin.write(data)
		self.p.stdin.flush()
		
	def read(self, size=None):
		return self.p.stdout.read(size)
		
	def readline(self):
		return self.p.stdout.readline()
		
	def readlines(self):
		return self.p.stdout.readlines()
		
if (__name__ == '__main__'):
	p = Console()