#!/usr/bin/env python

import glob
import os
import re

class FsScanner(object):

    def __init__(self, pathTemplate):
        fmt = re.compile(r'%\((\w+)\).*?([diouxXeEfFgGcrs])')
        self.globString = fmt.sub('*', pathTemplate)
        last = 0
        self.fields = {}
        self.reString = ""
        n = 0
        pos = 0
        for m in fmt.finditer(pathTemplate):
            fieldName = m.group(1)
            if self.fields.has_key(fieldName):
                fieldName += "_%d" % (n,)
                n += 1
            isInt = False
            if m.group(2) not in 'crs':
                isInt = True

            self.fields[fieldName] = dict(pos=pos, isInt=isInt)
            pos += 1

            prefix = pathTemplate[last:m.start(0)]
            last = m.end(0)
            self.reString += prefix
        
            if m.group(2) in 'crs':
                self.reString += r'(?P<' + fieldName + '>.+?)'
            elif m.group(2) in 'xX':
                self.reString += r'(?P<' + fieldName + '>[\dA-Fa-f]+?)'
            else:
                self.reString += r'(?P<' + fieldName + '>[\d.eE+-]+?)'
        
        self.reString += pathTemplate[last:] 

    def getFields(self):
        fieldList = ["" for i in xrange(len(self.fields))]
        for f in self.fields.keys():
            fieldList[self.fields[f]['pos']] = f
        return fieldList

    def isIntField(self, name):
        return self.fields[name]['isInt']

    def processDir(self, location, callback):
        curdir = os.getcwd()
        os.chdir(location)
        pathList = glob.glob(self.globString)
        for path in pathList:
            dataId = re.search(self.reString, path).groupdict()
            callback(path, dataId)
        os.chdir(curdir)
