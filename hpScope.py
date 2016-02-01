#!/usr/bin/python

import serial
import time
import struct
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
	COMMAND_DIGITIZE_CH1			= ':DIGITIZE CHANNEL1'
	COMMAND_DIGITIZE_CH2			= ':DIGITIZE CHANNEL2'
	COMMAND_DIGITIZE_BOTH 			= ':DIG CHAN1,CHAN2'
	COMMAND_SET_FORMAT				= ':WAVEFORM:FORMAT BYTE'
	COMMAND_SET_WAVEFORM_POINTS 	= ':WAV:POIN 5000'
	COMMAND_READ_WAVEFORM			= ':WAVEFORM:DATA?'
	COMMAND_SET_BYTE_ORDER 			= ':WAV:BYT MSBF'

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

	def getWaveform( self ):
		waveform = []
		waveformStr = ''

		self.writeCommand( self.COMMAND_SET_FORMAT )
		self.writeCommand( self.COMMAND_SET_BYTE_ORDER )
		self.writeCommand( self.COMMAND_DIGITIZE_CH1 )
		#HACKY
		time.sleep(0.400)

		# We have to wait a bit for the waveform to be ready
		#progress = 0
		#while( progress < 1.0 ):
		#	print "Progress = " + str( progress ) + '%'
		#	progress = self.getAcquireProgress()	little-endian	standard	none
	

		# Now actually try and get the waveform
		self.writeCommand( self.COMMAND_READ_WAVEFORM )
		# HACKY
		time.sleep(0.600)

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
					waveform.append( point )

		return waveform

	def makePlot( self ):
		# Snag the actual waveform
		points = self.getWaveform()

		# Grab display information
		preamble = self.getWaveformPreamble()
		vDiv 	= 32 * preamble['yIncrement']
		yOffset = (128 - preamble['yReference']) * preamble['yIncrement'] - preamble['yOrigin']
		tDiv 	= (preamble['points'] * preamble['xIncrement']) / 10
		tDelay  = (((preamble['points'] / 2) - preamble['xReference']) * preamble['xIncrement']) + preamble['xOrigin']

		# Grab channel settings
		#channelInfo = self.getChannelInfo()

		# Scale the points, and interleave them with the timebase
		# TODO: Double check the waveform contains as many points as we expect
		waveform = []
		timebase = []

		for x in range( preamble['points'] ):
			scaledPoint = ((points[x] - preamble['yReference']) * preamble['yIncrement']) + preamble['yOrigin']
			waveform.append( scaledPoint + yOffset )
			timebase.append( preamble['xOrigin'] + (preamble['xIncrement'] * x) )

		# Draw the timebase delay
		plt.plot( -1 * tDelay, (vDiv * -4) , 'g^' )

		# Turn on the grid and set the axis ranges
		plt.grid( True )
		plt.xlim( preamble['xOrigin'], preamble['xOrigin'] + (preamble['xIncrement'] * preamble['points']))
		plt.ylim( vDiv * -4, vDiv * 4 )

		# Draw y-offset marker and grid line
		plt.plot( preamble['xOrigin'] + (preamble['xIncrement'] * preamble['points']), yOffset, 'b<' )
		plt.axhline( y=yOffset, color='b', linestyle='dotted' )

		# Darken the grid lines for X and Y axis
		plt.axvline( color='k' )
		plt.axhline( color='k' )

		plt.xticks([
			timebase[ int(preamble['points'] * 0.1) ],
			timebase[ int(preamble['points'] * 0.2) ],
			timebase[ int(preamble['points'] * 0.3) ],
			timebase[ int(preamble['points'] * 0.4) ],
			timebase[ int(preamble['points'] * 0.5) ],
			timebase[ int(preamble['points'] * 0.6) ],
			timebase[ int(preamble['points'] * 0.7) ],
			timebase[ int(preamble['points'] * 0.8) ],
			timebase[ int(preamble['points'] * 0.9) ]
		])

		plt.yticks([
			vDiv * -3,
			vDiv * -2,
			vDiv * -1,
			vDiv *  0,
			vDiv *  1,
			vDiv *  2,
			vDiv *  3
		])

		# Finally plot the waveform
		plt.plot( timebase, waveform, color='b' )
		
		
		

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

		channelInfo = []

		for channel in channels:
			channelInfo.append({
				'channel'		: channel,
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
			})

		return channelInfo

	def getWaveformPreamble( self ):
		self.writeCommand( self.COMMAND_GET_WAVEFORM_PREAMBLE )

		preambleASCII = self.readResult()
		preambleSplit = preambleASCII.split(',')

		preamble = {
			'format'		: int( preambleSplit[0] ),
			'type'			: int( preambleSplit[1] ),
			'points'		: int( preambleSplit[2] ),
			'count'			: int( preambleSplit[3] ),
			'xIncrement'	: float( preambleSplit[4] ),
			'xOrigin'		: float( preambleSplit[5] ),
			'xReference'	: int( preambleSplit[6] ),
			'yIncrement'	: float( preambleSplit[7] ),
			'yOrigin'		: float( preambleSplit[8] ),
			'yReference'	: int( preambleSplit[9] )
		}

		return preamble