import sys, os, shutil, platform
from cx_Freeze import setup, Executable

setup(
	name = 'Console-test',
	executables = [
		Executable(
			'Console.py',
			base=None,
			),
		Executable(
			'output_test.py',
			base=None,
			),
		Executable(
			'bidirectional_test.py',
			base=None,
			)
		]
)
