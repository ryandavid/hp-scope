#!/usr/bin/python

import serial
import time
import struct
import json
import matplotlib.pyplot as plt

# Assumes the following settings for the 54652B RS-232 Interface
# Baud-rate = 19200
# Hardware Flow Control = DTR

class hpScope:

	DEFAULT_NUM_CHANNELS = 2

	DEFAULT_READ_SIZE = 200
	DEFAULT_SLEEP_TIME = 0.050

	CHANNEL_NUM = '<N>'

	# List of commands
	COMMAND_IDN 					= '*IDN?'
	COMMAND_DIGITIZE_CHANNEL		= ':DIG CHAN' + CHANNEL_NUM
	COMMAND_DIGITIZE_CH1			= ':DIG CHAN1'
	COMMAND_DIGITIZE_CH2			= ':DIG CHAN2'
	COMMAND_DIGITIZE_BOTH 			= ':DIG CHAN1,CHAN2'
	COMMAND_SET_FORMAT				= ':WAVEFORM:FORMAT BYTE'
	COMMAND_SET_WAVEFORM_POINTS 	= ':WAV:POIN 5000'
	COMMAND_READ_WAVEFORM			= ':WAVEFORM:DATA?'
	COMMAND_SET_BYTE_ORDER 			= ':WAV:BYT MSBF'
	COMMAND_SET_WAVEFORM_SOURCE		= ':WAV:SOUR ' + CHANNEL_NUM

	COMMAND_GET_WAVEFORM_PREAMBLE 	= ':WAV:PRE?'

	COMMAND_GET_ACQUIRE_COMPLETE 	= ':ACQ:COMP?'

	COMMAND_RUN 					= ':RUN'
	COMMAND_STOP 					= ':STOP'

	COMMAND_GET_TIMEBASE_DELAY 		= ':TIM:DEL?'
	COMMAND_GET_TIMEBASE_RANGE 		= ':TIM:RANG?'

	COMMAND_GET_TRIGGER_LEVEL 		= ':TRIG:LEV?'
	COMMAND_GET_TRIGGER_SOURCE 		= ':TRIG:SOUR?'
	COMMAND_GET_TRIGGER_SLOPE 		= ':TRIG:SLOP?'
	COMMAND_GET_TRIGGER_COUPLING 	= ':TRIG:COUP?'

	COMMAND_SYS_DISPLAY_TEXT 		= ':SYST:DSP'
	COMMAND_SET_ROW 				= ':DISP:ROW'
	COMMAND_WRITE_TEXT 				= ':DISP:LINE'
	COMMAND_CLEAR_TEXT 				= ':DISP:TEXT BLAN'

	COMMAND_GET_CHANNEL_BWLIMIT 	= ':CHAN' + CHANNEL_NUM +':BWL?'
	COMMAND_GET_CHANNEL_COUPLING 	= ':CHAN' + CHANNEL_NUM +':COUP?'
	COMMAND_GET_CHANNEL_INPUT 		= ':CHAN' + CHANNEL_NUM +':INP?'
	COMMAND_GET_CHANNEL_OFFSET 		= ':CHAN' + CHANNEL_NUM +':OFFS?'
	COMMAND_GET_CHANNEL_PROBE_MODE	= ':CHAN' + CHANNEL_NUM +':PMOD?'
	COMMAND_GET_CHANNEL_PROBE_ATT 	= ':CHAN' + CHANNEL_NUM +':PROB?'
	COMMAND_GET_CHANNEL_PROTECT 	= ':CHAN' + CHANNEL_NUM +':PROT?'
	COMMAND_GET_CHANNEL_RANGE	 	= ':CHAN' + CHANNEL_NUM +':RANG?'
	COMMAND_GET_CHANNEL_SKEW	 	= ':CHAN' + CHANNEL_NUM +':SKEW?'
	COMMAND_GET_CHANNEL_VERNIER	 	= ':CHAN' + CHANNEL_NUM +':VERN?'
	COMMAND_GET_CHANNEL_ENABLED	 	= ':STAT? CHAN' + CHANNEL_NUM

	plotChannelColors = [
		'k',	# Channel 0 - Black, USED AS PADDING TO KEEP INDEX STARTING AT 1
		'b',	# Channel 1 - Blue
		'r'		# Channel 2 - Red
	]

	def __init__( self, portName='/dev/ttyUSB0', baudrate=19200 ):
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

			success = True

		return success

	def readResult( self, length=None ):
		if( length == None ):
			length = self.DEFAULT_READ_SIZE

		return self.port.read( length )

	def getIdentification( self ):
		self.writeCommand( self.COMMAND_IDN )

		identification = self.readResult()

		return identification.strip()

	def getWaveform( self, channelList ):
		waveform = dict()
		waveformStr = ''

		self.writeCommand( self.COMMAND_SET_FORMAT )
		self.writeCommand( self.COMMAND_SET_BYTE_ORDER )

		if( channelList == [1,2] ):
			self.writeCommand( self.COMMAND_DIGITIZE_BOTH )
		else:
			newCommand = self.COMMAND_DIGITIZE_CHANNEL.replace( self.CHANNEL_NUM, str(channelList[0]) )
			self.writeCommand( newCommand )


		# Now actually try and get the waveform
		for channel in channelList:
			#HACKY
			time.sleep(0.400)

			# Set the source to read the waveform
			newCommand = self.COMMAND_SET_WAVEFORM_SOURCE.replace( self.CHANNEL_NUM, str(channel) )
			self.writeCommand( newCommand )

			self.writeCommand( self.COMMAND_READ_WAVEFORM )

			# HACKY
			time.sleep(0.600)

			rawWaveform = []
			scaledWaveform = []
			header = self.readResult( 2 )

			if( len(header) == 2 ):
				if( header[0] == '#' ):
					digitsToFollow = int( header[1] )

					asciiLength = self.readResult( digitsToFollow )
					numBytes = int( asciiLength )
					#print "Expecting {} bytes".format( numBytes )

					while( len(waveformStr) < numBytes ):
						waveformStr += self.readResult( numBytes - len(waveformStr) )
						#print "At {} bytes".format( len(waveformStr) )

					# We need to read out the trailing linefeed as well
					self.readResult(1)

					for i in range(0, numBytes):
						point = struct.unpack( 'B', waveformStr[i] )[0]
						rawWaveform.append( point )

			preamble = self.getWaveformPreamble()

			vDiv 	= 32 * preamble['yIncrement']
			yOffset = (128 - preamble['yReference']) * preamble['yIncrement'] - preamble['yOrigin']
			tDiv 	= (preamble['numPoints'] * preamble['xIncrement']) / 10
			tDelay  = (((preamble['numPoints'] / 2) - preamble['xReference']) * preamble['xIncrement']) + preamble['xOrigin']

			# Lets also put the waveform into real units
			for i in range(0, len(rawWaveform) ):
				scaledPoint = ((rawWaveform[i] - preamble['yReference']) * preamble['yIncrement']) + preamble['yOrigin']
				scaledWaveform.append( scaledPoint )

			waveform[ channel ] = {
				'format'		: preamble['format'],
				'type'			: preamble['type'],
				'numPoints'		: preamble['numPoints'],
				'count'			: preamble['count'],
				'xIncrement'	: preamble['xIncrement'],
				'xOrigin'		: preamble['xOrigin'],
				'xReference'	: preamble['xReference'],
				'yIncrement'	: preamble['yIncrement'],
				'yOrigin'		: preamble['yOrigin'],
				'yReference'	: preamble['yReference'],
				'vDiv'			: vDiv,
				'yOffset'		: yOffset,
				'points'		: rawWaveform,
				'scaledPoints'	: scaledWaveform
			}

		# Finally lets put together the timebase
		timePoints = []
		for x in range( preamble['numPoints'] ):
			timePoints.append( preamble['xOrigin'] + (preamble['xIncrement'] * x) )

		waveform['timebase'] = {
			'points'	: timePoints,
			'tDiv'		: tDiv,
			'tDelay'	: tDelay
		}

		return waveform

	def makePlot( self ):
		# Grab channel settings
		channelInfo = self.getChannelInfo()

		# Snag the actual waveform
		enabledChannels = []
		for channel in channelInfo :
			if( channelInfo[channel]['enabled'] == True ):
				enabledChannels.append( channel )

		waveforms = self.getWaveform( enabledChannels )

		# Draw the timebase delay
		plt.plot( -1 * waveforms['timebase']['tDelay'], (waveforms[1]['vDiv'] * -4) , 'g^' )
		plt.axvline( x=-1 * waveforms['timebase']['tDelay'], color='b', linestyle='dotted' )

		# Turn on the grid and set the axis ranges
		plt.grid( True )
		plt.xlim( waveforms[1]['xOrigin'], waveforms[1]['xOrigin'] + (waveforms[1]['xIncrement'] * waveforms[1]['numPoints']))
		#plt.ylim( waveforms[1]['vDiv'] * -4, waveforms[1]['vDiv'] * 4 )

		# TODO: Draw trigger level
		#plt.plot( waveforms[1]['xOrigin'] + (waveforms[1]['xIncrement'] * waveforms[1]['numPoints']), waveforms[1]['yOffset'], 'b<' )
		#plt.axhline( y=waveforms[1]['yOffset'], color='b', linestyle='dotted' )

		# Darken the grid lines for X and Y axis
		plt.axvline( color='k' )
		plt.axhline( color='k' )


		# Finally plot the waveform
		for channel in waveforms:
			plt.plot( waveforms['timebase']['points'], waveforms[1]['scaledPoints'], color=self.plotChannelColors[ 1 ] )
		
		
		plt.show()


	def run( self ):
		return self.writeCommand( self.COMMAND_RUN )

	def stop( self ):
		return self.writeCommand( self.COMMAND_STOP )

	def getAcquireProgress( self ):
		self.writeCommand( self.COMMAND_GET_ACQUIRE_COMPLETE )

		progressASCII = self.readResult()
		print progressASCII
		progress = float( progressASCII.split()[0] )

		return progress / 100.0

	def getTimebaseRange( self ):
		self.writeCommand( self.COMMAND_GET_TIMEBASE_RANGE )

		rangeASCII = self.readResult()

		# Need to divide by 10, units are in 100ms
		timeRange = float( rangeASCII.split()[0] ) / 10

		return timeRange

	def getTimebaseDelay( self ):
		self.writeCommand( self.COMMAND_GET_TIMEBASE_DELAY )

		delayASCII = self.readResult()
		delay = float( delayASCII.split()[0] )

		return delay

	def getTriggerLevel( self ):
		self.writeCommand( self.COMMAND_GET_TRIGGER_LEVEL )

		levelASCII = self.readResult()
		level = float( levelASCII.split()[0] )

		return level

	def getTriggerSource( self ):
		self.writeCommand( self.COMMAND_GET_TRIGGER_SOURCE )

		sourceASCII = self.readResult()
		source = sourceASCII.split()[0]

		return source

	def getTriggerSlope( self ):
		self.writeCommand( self.COMMAND_GET_TRIGGER_SLOPE )

		slopeASCII = self.readResult()
		slope = slopeASCII.split()[0]

		return slope 

	def getTriggerCoupling( self ):
		self.writeCommand( self.COMMAND_GET_TRIGGER_COUPLING )

		couplingASCII = self.readResult()
		coupling = couplingASCII.split()[0]

		return coupling 

	def writeSystemText( self, text ):
		return self.writeCommand( self.COMMAND_SYS_DISPLAY_TEXT + ' "' + text + '"' )

	def writeTextString( self, row, text ):
		success = False

		if( row in range(1, 21) ):
			self.writeCommand( self.COMMAND_SET_ROW + ' ' + str(row) )
			self.writeCommand( self.COMMAND_WRITE_TEXT + ' "' + text + '"')

			success = True

		return success

	def clearText( self ):
		self.writeCommand( self.COMMAND_CLEAR_TEXT )

	def getChannelBWLimit( self, channel ):
		newCommand = self.COMMAND_GET_CHANNEL_BWLIMIT.replace( self.CHANNEL_NUM, str(channel) )
		self.writeCommand( newCommand )

		bwLimitASCII = self.readResult()
		bwLimit = bwLimitASCII.split()[0]

		return bwLimit

	def getChannelCoupling( self, channel ):
		newCommand = self.COMMAND_GET_CHANNEL_COUPLING.replace( self.CHANNEL_NUM, str(channel) )
		self.writeCommand( newCommand )

		couplingASCII = self.readResult()
		coupling = couplingASCII.split()[0]

		return coupling

	def getChannelInputImpedance( self, channel ):
		newCommand = self.COMMAND_GET_CHANNEL_INPUT.replace( self.CHANNEL_NUM, str(channel) )
		self.writeCommand( newCommand )

		inputASCII = self.readResult()
		inputImp = inputASCII.split()[0]

		return inputImp

	def getChannelOffset( self, channel ):
		newCommand = self.COMMAND_GET_CHANNEL_OFFSET.replace( self.CHANNEL_NUM, str(channel) )
		self.writeCommand( newCommand )

		offsetASCII = self.readResult()
		offset = float(offsetASCII.split()[0])

		# Multiply by -1 to get axis on plot
		return -1 * offset

	def getChannelProbeMode( self, channel ):
		newCommand = self.COMMAND_GET_CHANNEL_PROBE_MODE.replace( self.CHANNEL_NUM, str(channel) )
		self.writeCommand( newCommand )

		modeASCII = self.readResult()
		mode = modeASCII.split()[0]

		return mode

	def getChannelProbeAttenuation( self, channel ):
		newCommand = self.COMMAND_GET_CHANNEL_PROBE_ATT.replace( self.CHANNEL_NUM, str(channel) )
		self.writeCommand( newCommand )

		attASCII = self.readResult()
		attenuation = attASCII.split()[0]

		return attenuation

	def getChannelProtect( self, channel ):
		newCommand = self.COMMAND_GET_CHANNEL_PROTECT.replace( self.CHANNEL_NUM, str(channel) )
		self.writeCommand( newCommand )

		protASCII = self.readResult()
		protect = protASCII.split()[0]

		return protect

	def getChannelRange( self, channel ):
		newCommand = self.COMMAND_GET_CHANNEL_RANGE.replace( self.CHANNEL_NUM, str(channel) )
		self.writeCommand( newCommand )

		rangeASCII = self.readResult()
		chRange = float(rangeASCII.split()[0])

		return chRange

	def getChannelSkew( self, channel ):
		newCommand = self.COMMAND_GET_CHANNEL_SKEW.replace( self.CHANNEL_NUM, str(channel) )
		self.writeCommand( newCommand )

		skewASCII = self.readResult()
		skew = float(skewASCII.split()[0])

		return skew

	def getChannelVernier( self, channel ):
		newCommand = self.COMMAND_GET_CHANNEL_VERNIER.replace( self.CHANNEL_NUM, str(channel) )
		self.writeCommand( newCommand )

		vernASCII = self.readResult()
		vern = vernASCII.split()[0]

		return vern	

	def getChannelEnabled( self, channel ):
		enabled = False

		newCommand = self.COMMAND_GET_CHANNEL_ENABLED.replace( self.CHANNEL_NUM, str(channel) )
		self.writeCommand( newCommand )

		enabledASCII = self.readResult()
		if( enabledASCII.split()[0] == 'ON' ):
			enabled = True

		return enabled	

	def getChannelInfo( self ):
		channels = range( 1, self.DEFAULT_NUM_CHANNELS + 1 )

		channelInfo = dict()

		for channel in channels:
			channelInfo[channel] = {
				'enabled'		: self.getChannelEnabled( channel ),
				'bwLimit' 		: self.getChannelBWLimit( channel ),
				'coupling'		: self.getChannelCoupling( channel ),
				'impedance' 	: self.getChannelInputImpedance( channel ),
				'offset' 		: self.getChannelOffset( channel ),
				'probeMode' 	: self.getChannelProbeMode( channel ),
				'attenuation'	: self.getChannelProbeAttenuation( channel ),
				'protect' 		: self.getChannelProtect( channel ),
				'range'			: self.getChannelRange( channel ),
				'skew'			: self.getChannelSkew( channel ),
				'vernier'		: self.getChannelVernier( channel )
			}

		return channelInfo

	def getWaveformPreamble( self ):
		self.writeCommand( self.COMMAND_GET_WAVEFORM_PREAMBLE )

		preambleASCII = self.readResult()
		preambleSplit = preambleASCII.split(',')

		if( len(preambleSplit) == 10 ):
			preamble = {
				'format'		: int( preambleSplit[0] ),
				'type'			: int( preambleSplit[1] ),
				'numPoints'		: int( preambleSplit[2] ),
				'count'			: int( preambleSplit[3] ),
				'xIncrement'	: float( preambleSplit[4] ),
				'xOrigin'		: float( preambleSplit[5] ),
				'xReference'	: int( preambleSplit[6] ),
				'yIncrement'	: float( preambleSplit[7] ),
				'yOrigin'		: float( preambleSplit[8] ),
				'yReference'	: int( preambleSplit[9] )
			}
		else:
			preamble = None

		return preamble