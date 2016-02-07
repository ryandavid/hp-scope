#!/usr/bin/python

from hpScope import hpScope
import json
import time

# Connect to the scope
scope = hpScope()
scope.connect()

sFile = time.strftime("waveform_%Y%m%d-%H%M%S.json")
hFile = open(sFile, 'w')
print "Writing out to '{0}'".format( sFile )

# Lets snapshot everything on the scope
waveforms = scope.getWaveform()
jsonWaveforms = json.dumps( waveforms )

# Write it out to a file
hFile.write( jsonWaveforms )

# Tidy up
scope.disconnect()
hFile.close()