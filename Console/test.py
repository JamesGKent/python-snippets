from Console import Console
import sys, time

if (__name__ == '__main__'):
	p = Console(False)
	for i in range(0, 100):
#		print('test %i\n' % i)
		p.write('test %i\n' % i)
		time.sleep(1)