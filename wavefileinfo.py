"""
WAVEFILEINFO.PY - a simple, user-friendly include for getting pertinent info from wave files
jon@jonkubis.com

REFERENCES:
http://www-mmsp.ece.mcgill.ca/Documents/AudioFormats/WAVE/WAVE.html
http://www.piclist.com/techref/io/serial/midi/wave.html
https://sites.google.com/site/musicgapi/technical-documents/wav-file-format
and others!
"""
import struct
import os

from pprint import pprint
from inspect import getmembers
from types import FunctionType

def attributes(obj):
	disallowed_names = {
		name for name, value in getmembers(type(obj)) 
			if isinstance(value, FunctionType)}
	return {
		name: getattr(obj, name) for name in dir(obj) 
			if name[0] != '_' and name not in disallowed_names and hasattr(obj, name)}

def print_attributes(obj):
	pprint(attributes(obj))

class wavefileinfo:

	# sGroupID = 'RIFF'
	# dwFileLength = //File length in bytes, measured from offset 8
	

	def __init__(self, fn):
		self.__pathname = fn
		self.__readfile__()
	
	def __readfile__(self):
		self.__chunkIDs = []
		self.__chunkstarts = []
		self.__chunklengths = []
		self.__loops = []
		
		self.__smpl_numberofloops     = None
		self.__smpl_midiunitynote     = None
		self.__smpl_midipitchfraction = None
		self.__inst_unshiftednote     = None
		self.__inst_finetune          = None
		
		with open(self.__pathname,mode='rb') as fi:
			#get the true file length on disk and don't trust dwFileLength
			fi.seek(0,2)            # go to the file end.
			self.__eof = fi.tell()   # get the end of file location
			fi.seek(0,0)             # # go back to file beginning
			
			self.__sGroupID = fi.read(4) # 'RIFF'
			if (self.__sGroupID != b'RIFF'): raise ("Input file not a WAVE file: 'RIFF' chunk ID not found")
			self.__dwFileLength = struct.unpack('I', fi.read(4))[0] # File length - 8
			self.__sRiffType = fi.read(4) # 'WAVE'
			if (self.__sRiffType != b'WAVE'): raise ("Input file not a WAVE file: 'WAVE' RIFF type not found")
			
			while(fi.tell() != self.__eof):
				thischunkstart = fi.tell()
				thischunkID = fi.read(4)
				thischunklength = struct.unpack('I', fi.read(4))[0]
				
				self.__chunkstarts.append(thischunkstart)
				self.__chunkIDs.append(thischunkID)
				self.__chunklengths.append(thischunklength)
				
				#print (thischunkID)
				
				if (thischunkID == b'fmt '):
					self.__fmtChunkSize = thischunklength
					self.__wFormatTag       = struct.unpack('H', fi.read(2))[0] #1 = WAVE_FORMAT_PCM, 3 = WAVE_FORMAT_IEEE_FLOAT
					self.__wChannels        = struct.unpack('H', fi.read(2))[0] #mono = 1, stereo = 2, ...
					self.__wSamplesPerSec   = struct.unpack('I', fi.read(4))[0] #sample rate (e.g. 44100, 48000)
					self.__dwAvgBytesPerSec = struct.unpack('I', fi.read(4))[0] # = wSamplesPerSec * (wBitsPerSample/8) * wChannels
					self.__wBlockAlign      = struct.unpack('H', fi.read(2))[0] # = (dwBitsPerSample/8) * wChannels
					self.__dwBitsPerSample  = struct.unpack('H', fi.read(2))[0] #bit depth (16, 24, 32)
					if (thischunklength >= 18): #32 bit float files are almost always 18 
						self.__fmtChunkExtSize = struct.unpack('H', fi.read(2))[0] #Size of the fmt chunk extension: almost always zero
					else:
						self.__fmtChunkExtSize = 0
				if (thischunkID == b'data'):
					self.__dataChunkStart = thischunkstart #data chunk start position (since we're not going to read the wave data into RAM
														   #we store the starting position of the data chunk so we can quickly access wave data later
					self.__dataChunkSize = thischunklength #data chunk size in bytes
					self.__dataChunkFrames = thischunklength / ((self.__dwBitsPerSample / 8) * self.__wChannels)
				if (thischunkID == b'smpl'):
					self.__smpl_manufacturer      = struct.unpack('I', fi.read(4))[0]
					self.__smpl_product           = struct.unpack('I', fi.read(4))[0]
					self.__smpl_sampleperiod      = struct.unpack('I', fi.read(4))[0]
					self.__smpl_midiunitynote     = struct.unpack('I', fi.read(4))[0]
					self.__smpl_midipitchfraction = struct.unpack('I', fi.read(4))[0]
					self.__smpl_smpteformat       = struct.unpack('I', fi.read(4))[0]
					self.__smpl_smpteoffset       = struct.unpack('I', fi.read(4))[0]
					self.__smpl_numberofloops     = struct.unpack('I', fi.read(4))[0]
					self.__smpl_samplerdatasize   = struct.unpack('I', fi.read(4))[0]
					
					if (self.__smpl_numberofloops > 0):
						for x in range(self.__smpl_numberofloops):
							thisloop = self.__sampleloopinfo()
							thisloop.cuepointID = struct.unpack('I', fi.read(4))[0]
							thisloop.type       = struct.unpack('I', fi.read(4))[0]
							thisloop.start      = struct.unpack('I', fi.read(4))[0]
							thisloop.end        = struct.unpack('I', fi.read(4))[0]
							thisloop.fraction   = struct.unpack('I', fi.read(4))[0]
							thisloop.playcount  = struct.unpack('I', fi.read(4))[0]
							self.__loops.append(thisloop)
							
				if (thischunkID == b'inst'):
					self.__inst_unshiftednote   = struct.unpack('B', fi.read(1))[0] # 0-127      : should be the same as self.__smpl_midiunitynote
					self.__inst_finetune        = struct.unpack('b', fi.read(1))[0] # -50 to +50 : fine tune in cents
					self.__inst_gain			= struct.unpack('b', fi.read(1))[0] # -64 to +64 : gain in dB
					self.__inst_lownote			= struct.unpack('B', fi.read(1))[0] # 0-127      : key range low starting note
					self.__inst_highnote		= struct.unpack('B', fi.read(1))[0] # 0-127      : key range high ending note
					self.__inst_lowvelocity		= struct.unpack('B', fi.read(1))[0] # 0-127      : key range low velocity
					self.__inst_highvelocity	= struct.unpack('B', fi.read(1))[0] # 0-127      : key range high velocity
				
				fi.seek(thischunkstart+8) #return back to the start of this chunk
				
				fi.seek(thischunklength,1)
			
			
		
	@property
	def pathname(self):
		""" Returns full path name of the requested file """
		return self.__pathname
		
	@property
	def filename(self):
		""" Returns only the file name of the requested file """
		return os.path.basename(self.__pathname)
		
	@property
	def RIFFchunkID(self):
		""" Should always return 'RIFF' """
		return self.__RIFFchunkID
	
	@property
	def dwFileLength(self):
		""" Total file length minus 8, which is taken up by RIFF and length (first 8 bytes of file) """
		return self.__dwFileLength
	
	@property
	def filesize(self):
		""" Total file length on disk - SHOULD be dwFileLength + 8 """
		return self.__eof
	
	@property
	def sRiffType(self):
		""" Should always return 'WAVE' """
		return self.__sRiffType
		
	@property
	def fourCCbackwards(self):
		""" the 4 letter format identifier backwards (for Logic Pro EXS24) """
		if self.__sRiffType == b'WAVE':
			return b'EVAW'
	
	@property
	def fmtChunkSize(self):
		""" #Size of the 'fmt ' chunk - almost always 16, sometimes 18, rarely 40 """
		return self.__fmtChunkSize
	
	@property
	def wFormatTag(self):
		""" Returns 1 if PCM, 3 if IEEE Float (1 = WAVE_FORMAT_PCM, 3 = WAVE_FORMAT_IEEE_FLOAT)"""
		return self.__wFormatTag
	
	@property
	def wChannels(self):
		""" Returns # of channels: 1 = mono, 2 = stereo, ..."""
		return self.__wChannels
		
	@property
	def channels(self):
		""" Returns # of channels: 1 = mono, 2 = stereo, ..."""
		return self.__wChannels
	
	@property
	def wSamplesPerSec(self):
		""" Returns sample rate (e.g. 44100, 48000)"""
		return self.__wSamplesPerSec
		
	@property
	def samplerate(self):
		""" Returns sample rate (e.g. 44100, 48000)"""
		return self.__wSamplesPerSec
	
	@property
	def dwAvgBytesPerSec(self):
		""" = wSamplesPerSec * (wBitsPerSample/8) * wChannels """
		return self.__dwAvgBytesPerSec	
		
	@property
	def wBlockAlign(self):
		""" Number of bytes per 'frame' (a single sample that includes all channels):  
		= (wBitsPerSample/8) * wChannels """
		return self.__wBlockAlign
	
	@property
	def dwBitsPerSample(self):
		""" Returns the bit depth (8, 16, 24, 32) """
		return self.__dwBitsPerSample	
	
	@property
	def bitdepth(self):
		""" Returns the bit depth (8, 16, 24, 32) """
		return self.__dwBitsPerSample
		
	@property
	def fmtChunkExtSize(self):
		""" Size of the fmt chunk extension: almost always zero """
		return self.__fmtChunkExtSize
		
	@property
	def dataChunkStart(self):
		""" Starting position of data chunk inside wave file """
		return self.__dataChunkStart	
	
	@property	
	def dataStart(self):
		""" Starting byte position of wave data in file - seek here for data! """
		return (self.__dataChunkStart + 8)
		
	@property
	def dataChunkSize(self):
		""" Size of the data chunk (total byte count of sample data) """
		return self.__dataChunkSize
	
	@property
	def dataChunkFrames(self):
		""" Number of frames in data chunk  """
		return int(self.__dataChunkFrames)
	
	@property
	def dataAsRawBytes(self):
		""" Returns the entire data chunk as raw bytes """
		self.__readfile__() #re-read file in case it changed!
		
		with open(self.__pathname,mode='rb') as fi:
			fi.seek(self.__dataChunkStart+8)
			data = fi.read(self.__dataChunkSize)
			
		return data
	
	@property
	def loopCount(self):
		""" Number of loops in 'smpl' chunk if present - returns None if no sample chunk, 0 if sample chunk is present but no loops """
		return self.__smpl_numberofloops
	
	@property
	def loops(self):
		""" Return the loops associated with this sample """
		return self.__loops
		
	@property
	def loopstart(self):
		""" Returns first loop sample start if applicable, None if not """
		if (self.__smpl_numberofloops is not None):
			if (self.__smpl_numberofloops > 0):
				return self.__loops[0].start
		return None
	
	@property
	def loopend(self):
		""" Returns first loop sample end if applicable, None if not """
		if (self.__smpl_numberofloops is not None):
			if (self.__smpl_numberofloops > 0):
				return self.__loops[0].end
		return None	
	
	@property
	def looplength(self):
		""" Returns length of first loop in samples if applicable, None if not """
		if (self.__smpl_numberofloops is not None):
			if (self.__smpl_numberofloops > 0):
				return self.__loops[0].end - self.__loops[0].start
		return None
	
	@property
	def smpl_midiunitynote(self):
		""" Returns the MIDI Unity Note Number from the smpl chunk if applicable, None if not """
		return self.__smpl_midiunitynote
	
	@property
	def inst_unshiftednote(self):
		""" Returns the MIDI Unity Note Number from the inst chunk if applicable, None if not """
		return self.__inst_unshiftednote
		
	@property
	def rootnote(self):
		""" Examines the smpl and inst chunks and returns a MIDI root note if applicable, None if not """
		if (self.__smpl_midiunitynote is not None):
			if (self.__inst_unshiftednote is not None):
				if (self.__smpl_midiunitynote == self.__inst_unshiftednote): #found both and they agree!
					return self.__smpl_midiunitynote
				else: #found both and they disagree, return the higher number :(
					if (self.__inst_unshiftednote > self.__smpl_midiunitynote):
						return self.__inst_unshiftednote
					else:
						return self.__smpl_midiunitynote
			else: #self.__inst_unshiftednote is None
				return self.__smpl_midiunitynote
		else: #self.__smpl_midiunitynote is None
			#return the root note from the inst chunk if present, otherwise return None
			return self.__inst_unshiftednote
	
	@property
	def finetune(self):
		""" Examines the smpl and inst chunks and returns a fine-tuning value if applicable, None if not """
		if self.__smpl_midipitchfraction is not None:
			mpf_in_cents = int(self.__smpl_midipitchfraction / ((int(0x8000000)/50)))
			
		#prefer inst fine tune chunk if found:			
		if self.__inst_finetune is not None:
			if self.__smpl_midipitchfraction is not None:
				
				if (self.__inst_finetune == self.__inst_finetune): #smpl & inst chunks agree:
					return self.__inst_finetune
				elif ((mpf_in_cents == 0) and (self.__inst_finetune != 0)): #inst chunk is nonzero, trust that
					return self.__inst_finetune
				elif ((mpf_in_cents != 0) and (self.__inst_finetune == 0)): #inst chunk is zero, smpl isn't...
					return mpf_in_cents
				else:
					return self.__inst_finetune
			else: #self.__smpl_midipitchfraction is none
				return self.__inst_finetune
		else: #self.__inst_finetune is none, return smpl chunk
			return mpf_in_cents
				
	
	"""
		
		
		
		
		if (fmtChunkSize == 18): #32 bit float files are always 18 
			cbSize = struct.unpack('H', fi.read(2))[0] #Size of the fmt chunk extension: 0

		pos += fmtChunkSize

		tag = fi.read(4)
		if (tag == b'fact'): #32 bit
			factTagSize    = struct.unpack('I', fi.read(4))[0]
			dwSampleLength = struct.unpack('I', fi.read(4))[0]
			tag = fi.read(4)
			
		if (tag == b'data'):
			ckSize = struct.unpack('I', fi.read(4))[0] #size of wave data in bytes
			raw_wavedatabytes = fi.read(ckSize) #read wave data into buffer
			
			if (wFormatTag == 1): #ints (PCM)
				if (dwBitsPerSample == 8):
					ints = array.array('b', raw_wavedatabytes)
				elif (dwBitsPerSample == 16):
					ints = array.array('h', raw_wavedatabytes)
				elif (dwBitsPerSample == 24): #hurray for 24-bit
					frames = ckSize//3
					triads = struct.Struct('3s' * frames)
					int4byte = struct.Struct('<i')
					ints = [int4byte.unpack(b'\0' + i)[0] >> 8 for i in triads.unpack(raw_wavedatabytes)]
			elif (wFormatTag == 3): #floats
				floats = array.array('f', raw_wavedatabytes) #parse buffer into floats
				
				if (outputbitdepth == 16):
					#16 bit ints from the floats:
					ints = []
					for thissample in floats:
						ints.append(int(thissample * 0x7FFF))
							
				elif (outputbitdepth == 24):
					#if we want 24 bit ints from the floats:
					ints = []
					for thissample in floats:
						ints.append(int(thissample * 0x7FFFFF))
						
		"""

	class __sampleloopinfo:
		def __init__(self):
			self.__cuepointID = None
			self.__type       = None
			self.__start      = None
			self.__end        = None
			self.__fraction   = None
			self.__playcount  = None
			
		@property
		def cuepointID(self):
			return self.__cuepointID

		@cuepointID.setter
		def cuepointID(self, x):
			self.__cuepointID = x
				
		@property
		def type(self):
			return self.__type

		@type.setter
		def type(self, x):
			self.__type = x
			
		@property
		def start(self):
			return self.__start

		@start.setter
		def start(self, x):
			self.__start = x		

		@property
		def end(self):
			return self.__end

		@end.setter
		def end(self, x):
			self.__end = x
			
		@property
		def fraction(self):
			return self.__fraction

		@fraction.setter
		def fraction(self, x):
			self.__fraction = x	
			
		@property
		def playcount(self):
			return self.__playcount

		@playcount.setter
		def playcount(self, x):
			self.__playcount = x		
	


#wfi = wavefileinfo('/Users/jonkubis/Music/Audio Music Apps/Sampler Instruments/01 Synths/SNES/SNES Final Fantasy 4/FF4 80s Air Synth/(2020330 20051)-A3-HI7D.wav')

#for attr in dir(wfi):
#	print("obj.%s = %r" % (attr, getattr(wfi, attr)))
	
#print_attributes(wfi)

