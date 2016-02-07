#!/usr/bin/python

from hpScope import hpScope
import json
import time

# Connect to the scope
scope = hpScope()

sFile = "waveform_20160206-182946.json"
hFile = open(sFile, 'r')
print "Opening '{0}'".format( sFile )

jsonWaveforms = hFile.read()
waveforms = json.loads( jsonWaveforms )

scope.makePlot( waveforms=waveforms )


hFile.close()