# encoding: utf8

"""
walker.py - MimeWalker-class for crawling through an driectory-tree and
				defining actions for certain mimetypes

This file is part of exif2ogr.
Copyright (C) 2008 Nico Mandery <nicomandery@googlemail.com>.

Foobar is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Foobar is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Foobar.  If not, see <http://www.gnu.org/licenses/>.

"""

import mimetypes
import os

class MimeWalker:
	def __init__(self,basedir,followlinks=False,recursive=True):
		self.basedir=basedir
		self.callbacks={}
		self.followlinks=followlinks
		self.recursive=recursive
		
	def __add_callback__(self,mimetype,callback):
		if not self.callbacks.has_key(mimetype):
			self.callbacks[mimetype]=[]
		if not callback in self.callbacks[mimetype]:
			self.callbacks[mimetype].append(callback)

	def registerCallback(self,mimetypes,callback):
		if not isinstance(mimetypes,list):
			if isinstance(mimetypes,str):
				mimetypes=[mimetypes]
			else:
				raise TypeError, 'type list or str for mimetypes expected'
		
		for mimetype in mimetypes:
			self.__add_callback__(mimetype,callback)
		#print self.callbacks

	def __recursive__(self,directory=None):
		if directory==None:
			directory=self.basedir
		for root,dirs,files in os.walk(directory):
			for file in files:
				#self.__checkfile__(os.path.abspath(os.path.join(root,file)))
				self.__checkfile__(os.path.join(root,file))			
			if self.followlinks==True:
				for d in dirs:
					#dd=os.path.abspath(os.path.join(root,d))
					dd=os.path.join(root,d)
					if os.path.islink(dd):
						self.__recursive__(dd)
	
	def __notrecursive__(self,directory=None):
		if directory==None:
			directory=self.basedir
		for file in os.listdir(directory):
			f=os.path.join(directory,file)
			if os.path.isfile(f):
				self.__checkfile__(f)
	
	def __checkfile__(self,file):
		mtype=mimetypes.guess_type(file)[0]
		if self.callbacks.has_key(mtype):
			for callback in self.callbacks[mtype]:
				callback(file)
				
	def start(self):
		if os.path.isfile(self.basedir):
			self.__checkfile__(self.basedir)
		elif os.path.isdir(self.basedir) or (os.path.islink(self.basedir) and self.followlinks):
			if self.recursive:
				self.__recursive__()
			else:
				self.__notrecursive__()