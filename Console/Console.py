#!python3

import sys, subprocess

class Console():
	def __init__(self, ischild=True):
		if not ischild:
			if hasattr(sys, 'frozen'):
				args = ['Console.exe']
			else:
				args = [sys.executable, __file__]
			self.p = subprocess.Popen(
				args,
				stdin=subprocess.PIPE,
				creationflags=subprocess.CREATE_NEW_CONSOLE
				)
		else:
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
#	if '-r' not in sys.argv:
#		for i in range(0, 100):
#			print('test %i\n' % i)
#			p.write('test %i\n' % i)
#			time.sleep(1)