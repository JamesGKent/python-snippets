#!python3

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
			'test.py',
			base=None,
			)
		]
)
