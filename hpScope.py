#!/usr/bin/python

import serial
import time
import struct

# Assumes the following settings for the 54652B RS-232 Interface
# Baud-rate = 19200
# Hardware Flow Control = DTR

class hpScope:

	DEFAULT_READ_SIZE = 100
	DEFAULT_SLEEP_TIME = 0.050

	# List of commands
	COMMAND_IDN 					= '*IDN?'
	COMMAND_DIGITIZE_CH1			= ':DIGITIZE CHANNEL1'
	COMMAND_DIGITIZE_CH2			= ':DIGITIZE CHANNEL2'
	COMMAND_SET_FORMAT				= ':WAVEFORM:FORMAT WORD'
	COMMAND_READ_WAVEFORM			= ':WAVEFORM:DATA?'	

	def __init__( self, portName='/dev/ttyUSB1', baudrate=19200 ):
		self.portName = portName
		self.baudrate = baudrate

		self.port = serial.Serial() # self.portName, baudrate, timeout=0, dsrdtr=True)
		self.port.baudrate = self.baudrate
		self.port.dsrdtr=True;
		self.port.port = self.portName
		self.port.timeout = 0.050
		self.port.rts = True

		self.connect()

	def connect( self ):
		success = False

		if( self.port.isOpen() == False ):
			self.port.open()

		success = self.port.isOpen()

		return success

	def disconnect( self ):
		success = False

		if( self.port.isOpen() == True ):
			self.port.close()
			success = True

		return success


	def writeCommand( self, command ):
		success = False

		if( self.port.isOpen() ):
			# Automatically wait some time before bombing the scope
			time.sleep( self.DEFAULT_SLEEP_TIME )
			self.port.write( command )
			self.port.write( '\r\n' )

	def readResult( self, length=None ):
		if( length == None ):
			length = self.DEFAULT_READ_SIZE

		return self.port.read( length )


	def getIdentification( self ):
		self.writeCommand( self.COMMAND_IDN )

		identification = self.readResult()

		return identification.strip()


	def getWaveform( self ):
		waveform = []
		waveformStr = ''

		self.writeCommand( self.COMMAND_SET_FORMAT )
		self.writeCommand( self.COMMAND_DIGITIZE_CH1 )
		self.writeCommand( self.COMMAND_READ_WAVEFORM )

		# We have to wait a bit for the waveform to be ready
		time.sleep(0.400)

		preamble = self.readResult( 2 )

		if( len(preamble) == 2 ):
			if( preamble[0] == '#' ):
				digitsToFollow = int( preamble[1] )

				asciiLength = self.readResult( digitsToFollow )
				numBytes = int( asciiLength )
				print "Expecting {} bytes".format( numBytes )

				while( len(waveformStr) < numBytes ):
					waveformStr += self.readResult( numBytes - len(waveformStr) )
					print "At {} bytes".format( len(waveformStr) )

				for i in range(0, numBytes, 2):
					point = struct.unpack( '<h', waveformStr[i:i+2] )
					waveform.append( point[0] )

		return waveform