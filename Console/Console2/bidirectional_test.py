from Console import Console
import sys, threading

def read_back():
	while True:
		data = p.read(1)
		if not data:
			break
		sys.stdout.write(data.decode('utf8'))

if (__name__ == '__main__'):
	p = Console(False, False)
	t = threading.Thread(target=read_back)
	t.daemon = True
	t.start()
	try:
		while True:
			data = input('Tx:')
			if data:
				data = '%s\n' % data
				p.write(data.encode('utf8'))
			else:
				break
	except KeyboardInterrupt:
		pass