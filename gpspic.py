# encoding: utf8

"""
gpspic.py - class for handling geocoded photos

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

try:
	import pyexiv2
except ImportError:
	raise ImportError("Could not find the python bindings for the exiv2-library.")

try:
	import gmpy
except ImportError:
	raise ImportError("Could not find the python bindings for the gmp-library (GNU Multiple Precision Arithmetic Library).")
#import os.path

# Converter Functions ###################################################
# http://www.greier-greiner.at/hc/umrechnungen.htm

KEY_LAT='Exif.GPSInfo.GPSLatitude'
KEY_LON='Exif.GPSInfo.GPSLongitude'
KEY_LAT_REF='Exif.GPSInfo.GPSLatitudeRef'
KEY_LON_REF='Exif.GPSInfo.GPSLongitudeRef'
KEY_MAP_DATUM='Exif.GPSInfo.GPSMapDatum'
KEY_DATETIME='Exif.Image.DateTime'
KEY_ALTITUDE='Exif.GPSInfo.GPSAltitude'
KEY_DATETIME_ORIG='Exif.Photo.DateTimeOriginal'

# according to the exif 2.2 specification only these two spatial referencesystems
# are valid. see http://www.exif.org/Exif2-2.PDF
EPSG_TOKYO=4301
EPSG_WGS84=4326


class GPSPic:
	def __init__(self,filename=""):
		if filename!="":
			self.open(filename)
		else:
			self.__reset_values__()
		
	def __reset_values__(self):
		self.image=None
		self.filename=None
	
	def open(self,filename):
		self.__reset_values__()
		self.filename=filename
		self.image=pyexiv2.Image(self.filename)
		self.image.readMetadata()
		
	def hasFullGeoInfo(self):
		for key in (KEY_LAT,KEY_LAT_REF,KEY_LON,KEY_LON_REF):
			if key not in self.image.exifKeys():
				return False
		return True
	
	def getAltitude(self):
		if (KEY_ALTITUDE in self.image.exifKeys()):
			return self.image[KEY_ALTITUDE]
		else:
			return None

	def getRecordingDate(self):
		if (KEY_DATETIME_ORIG in self.image.exifKeys()):
			return self.image[KEY_DATETIME_ORIG]
		elif (KEY_DATETIME in self.image.exifKeys()):
			return self.image[KEY_DATETIME]
		else:
			return None

	def getLongitudeFloat(self):
		if (KEY_LON in self.image.exifKeys()) and (KEY_LON_REF in self.image.exifKeys()):
			longitude=convertDeegreesToFloat(*self.image[KEY_LON])
			if self.image[KEY_LON_REF]=='W':
				 return longitude*(-1.0)
			else:
				return longitude
		else:
			return None
	
	def getLatitudeFloat(self):
		if (KEY_LAT in self.image.exifKeys()) and (KEY_LAT_REF in self.image.exifKeys()):
			latitude=convertDeegreesToFloat(*self.image[KEY_LAT])
			if self.image[KEY_LAT_REF]=='S':
				return latitude*(-1.0)
			else:
				return latitude
		else:
			return None
	
	def setLongitudeFloat(self,lon):
		if self.image:
			if lon<0:
				ref='W'
			else:
				ref='E'
			self.image[KEY_LON]=convertFloatToDeegrees(lon)
			self.image[KEY_LON_REF]=ref
	
	def setLatitudeFloat(self,lat):
		if self.image:
			if lat<0:
				ref='S'
			else:
				ref='N'
			self.image[KEY_LAT]=convertFloatToDeegrees(lat)
			self.image[KEY_LAT_REF]=ref
			
	def getEPSG(self):
		if (KEY_MAP_DATUM in self.image.exifKeys()):
			datum=self.image[KEY_MAP_DATUM]
			if datum=="TOKYO":
				return EPSG_TOKYO
		return EPSG_WGS84 # per default assume wgs84
	
	def write(self):
		if self.image:
			self.image.writeMetadata()
		
	def asWKT(self):
		return "POINT(%.8f %.8f)" % (self.getLongitudeFloat(),self.getLatitudeFloat())
	
	def show(self):
		if self.image!=None:
			for key in self.image.exifKeys():
				print "%s : %s\n" % (key,str(self.image[key]))

	
	
##########################################################################
#                                                                        #
#    Converter-functions                                                 #
#                                                                        #
#    see http://www.greier-greiner.at/hc/umrechnungen.htm                #
#                                                                        #
##########################################################################

def convertRationalToMPQ(r):
	"""
	Convert type pyexiv2.Rational to gmpy.mpq
	Lowlevel-function for convertDeegreesToFloat()
	"""
	if isinstance(r,pyexiv2.Rational):
		return gmpy.mpq(r.numerator,r.denominator)
	else:
		raise TypeError, 'type pyexiv2.Rational expected.'


def convertMPQToRational(m):
	"""
	Convert type gmpy.mpq to pyexiv2.Rational
	Lowlevel-function for convertFloatToDeegrees()
	"""
	#if isinstance(m,gmpy.mpq):
	print gmpy.numer(m)
	print gmpy.denom(m)
	return pyexiv2.Rational(long(gmpy.numer(m)),long(gmpy.denom(m)))
	#else:
	#	raise TypeError, 'type gmpy.mpq expected.'	

def convertFloatToDeegrees(f):
	"""
	Convert float vatiable to deegree,deegree-minutes and deegree-seconds of type
	pyexiv2.Rational for pyexiv2
	"""
	d=int(f) # maybe there exists a better way to do this...
	mins=(f%1)*60 # everything after the "." * 60
	dmins=int(mins)
	dsecs=gmpy.mpq((mins%1)*60)
	return (pyexiv2.Rational(d,1), pyexiv2.Rational(mins,1), convertMPQToRational(dsecs))
	

def convertDeegreesToFloat(d,dmin,dsec):
	"""
	Convert the coordinates from pyexiv2 to a float value
	"""
	d_mpq=convertRationalToMPQ(d)
	dmin_mpq=convertRationalToMPQ(dmin)
	dsec_mpq=convertRationalToMPQ(dsec)
	return float(d_mpq+(dmin_mpq/60)+(dsec_mpq/(60*60)))

