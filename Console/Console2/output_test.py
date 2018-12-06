from Console import Console
import sys, threading

if (__name__ == '__main__'):
	p = Console(False)
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