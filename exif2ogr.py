#!/usr/bin/env python
# encoding: utf8

"""
exif2ogr.py - 	commandline tool to convert geoinformation stored in 
					the exif-tags of jpeg files to formats supported by the 
					ogr-library

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

import sys
import os.path
from walker import MimeWalker
from optparse import OptionParser

try:
	from osgeo import ogr,osr
except ImportError:
	try:
		import ogr
		import osr
	except ImportError:
		print "Could not find python bindings for the ogr-library. Bye."
		sys.exit(1)

try:
	from gpspic import GPSPic
except ImportError,e:
	print e
	sys.exit(1)

error_msgs = [	"OK",
					"Not enough data",
					"Not enough memory",
					"Unsupported geometry type",
					"Unsupported operation",
					"Corrupt data",
					"Unknown failure",
					"Unsupported SRS"]

class JPEGReader:
	def __init__(self,abspath=False,recursive=True,search=[]):
		self.searchdirs=search
		self.numfiles=0
		self.coords=[]
		self.abspath=abspath
		self.recursive=recursive
		self.last=0

	def findfiles(self):
		for sd in self.searchdirs:
			if os.path.exists(sd):
				# collect pictures from this directory
				mw=MimeWalker(sd,recursive=self.recursive)
				mw.registerCallback('image/jpeg',self.__addfile__)
				mw.start()
			else:
				print "\"%s\" does not exist. skipping." % (sd)
		return self.numfiles,len(self.coords)

	def __addfile__(self,file):
		if self.abspath:
			file=os.path.abspath(file)
		self.numfiles+=1
		gp=GPSPic(file)
		if gp.hasFullGeoInfo():
			self.coords.append(gp)
			
	def __iter__(self):
		return self
			
	def next(self):
		if self.last==len(self.coords):
			raise StopIteration
		else:
			self.last+=1
			return self.coords[self.last-1]
	

def stripquotes(mystring):
	if mystring!=None:
		return mystring.replace("'","").replace('"','')
	else:
		return None

def exif2ogr():
	options,args=readargs()
	
	drivername=options.format
	drivername=stripquotes(drivername)
	driver = ogr.GetDriverByName(drivername)
	if driver==None:
		print "No OGR dirver for %s found. Exiting." % (drivername)
		sys.exit(1)
	
	jr=JPEGReader(abspath=options.abspath,recursive=options.recursive,search=args)
	njpeg,ncoords=jr.findfiles()
	if njpeg==0:
		print "Found no jpeg files. Exiting."
		sys.exit(1)
	elif ncoords==0:
		print "Found %d jpeg files, but none had GPS information. Exiting." % (njpeg)
		sys.exit(1)
	
	print "Found %d jpeg files, %d with GPS information." % (njpeg,ncoords)

		
	if os.path.exists(options.output):
		driver.DeleteDataSource(options.output)
	ds = driver.CreateDataSource(options.output)
	
	# spatial reference 
	spref=osr.SpatialReference()
	err=spref.ImportFromEPSG(options.spatialref)
	if err:
		print error_msgs[err]
		print "Failed to set spatialreferencesystem with EPSG %d. Exiting." % (options.spatialref)
		sys.exit(1)
	
	
	
	plyr = ds.CreateLayer(stripquotes(options.layername), geom_type=ogr.wkbPoint, srs=spref)
	if plyr==None:
		print "Creating pointlayer failed. bye"
		sys.exit(1)
		
	#fields
	fields=[]
	fields.append(ogr.FieldDefn('file',ogr.OFTString))
	if options.datetime:
		if options.string:
			fields.append(ogr.FieldDefn('rdatetime',ogr.OFTString))
		else:
			fields.append(ogr.FieldDefn('rdatetime',ogr.OFTDateTime))
	else:
		fields.append(ogr.FieldDefn('rdate',ogr.OFTDate))
		if options.string:
			fields.append(ogr.FieldDefn('rtime',ogr.OFTString))
		else:
			fields.append(ogr.FieldDefn('rtime',ogr.OFTTime))
	fields.append(ogr.FieldDefn('altitude',ogr.OFTInteger))
	for f in fields:
		err=plyr.CreateField(f,approx_ok=1)
		if err:
			print error_msgs[err]
			print "Creating field %s failed. ignoring." % (f.GetName())
	
	
	
	for c in jr:
		feat=ogr.Feature(feature_def=plyr.GetLayerDefn())
		feat.SetField('file',c.filename)
		
		dt=c.getRecordingDate()
		if dt!=None:
			if options.datetime:
				if options.string:
					feat.SetField('rdatetime',dt.strftime('%Y-%M-%d %H:%m:%S'))
				else:
					feat.SetField('rdatetime',dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second,0)
			else:
				if options.string:
					feat.SetField('rtime',dt.strftime('%H:%m:%S'))
				else:
					feat.SetField('rtime',dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second,0)
				feat.SetField('rdate',dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second,0)
		alt=c.getAltitude()
		if alt!=None:
			feat.SetField('altitude',alt)
		
		geom=ogr.CreateGeometryFromWkt(c.asWKT())
		if options.spatialref!=c.getEPSG(): #transform to desired srs
			pic_spref=osr.SpatialReference()
			pic_spref.ImportFromEPSG(c.getEPSG())
			geom.AssignSpatialReference(pic_spref)
			geom.TransformTo(spref)
		else:
			geom.AssignSpatialReference(spref)
			
		feat.SetGeometryDirectly(geom)
		plyr.CreateFeature(feat)
		feat.Destroy()
		
	ds.Destroy()


def readargs():
	parser=OptionParser(usage="%prog [OPTIONS] pic1, pic2, pic_directory, ...")
	parser.add_option('-a','--abspath',dest='abspath',action="store_true",default=False,help="Use absolute paths in the generated file. Default are relative paths.")
	parser.add_option('-d','--datetime',dest='datetime',action="store_true",default=False,help="Use datetime fields instead of seperate date and time fields. datetime is not supported by all formats.")
	parser.add_option('-l','--layername',dest='layername',default="photos",help='Name of the layer. Default: "photos"')
	parser.add_option('-f','--format',dest='format',help='OGR format to generate. See `ogrinfo --formats` for a list of available drivers.')
	parser.add_option('-o','--output',dest='output',help='filename for the generated OGR file. Already existing files will be overwritten')
	parser.add_option('-r','--recursive',dest='recursive',action="store_true",default=False,help="Check also for files in subdirectories")
	parser.add_option('-s','--spatial_ref',dest='spatialref',type='int',default=4326,help='EPSG of the spatial referencesystem of the generated file. The geometries of the inputfiles will be transformed. Default 4326 (WGS84)')
	parser.add_option('-t','--string',dest='string',action="store_true",default=False,help="Use type String for Time and DateTime fields. Workaround for ESRIs Shapefiles which do not support the native fieldtypes Time and Datetime.")
		
	(options,args) = parser.parse_args()
	
	if len(args)==0:
		print "You must specify at least one file.\nUse --help for usage information."
		sys.exit(1)
	if options.format==None or options.output==None:
		print "No outputformat and/or outputfile specifed."
		sys.exit(1)
	
	return options,args

if __name__ == "__main__":
	exif2ogr()
