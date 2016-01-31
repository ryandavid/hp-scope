#!/usr/bin/python

from hpScope import hpScope

scope = hpScope()

scope.connect()
print scope.getIdentification()
scope.disconnect()