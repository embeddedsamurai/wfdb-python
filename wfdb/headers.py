import numpy as np
import re
import os
import sys
import requests
from collections import OrderedDict, OrderedSet

        
# The base WFDB class to extend. Contains shared helper functions and fields.             
class WFDBbaserecord():
    # Constructor
    
    def __init__(self, recordname=None, nsig=None, 
                 fs=None, counterfreq=None, basecounter = None, 
                 siglen = None, basetime = None,basedate = None, 
                 comments = None)

    # Get the list of required fields needed to write the wfdb record. Method for both single and multi-segment records. 
    # Returns the default required fields, the user defined fields, and their dependencies.
    def getreqfields(self, fieldspeclist):

        # Record specification fields
        reqfields=getreqsubset(self, reversed(list(fieldspeclist[1].items())))

        # Single-segment record
        if fieldspeclist[0] == signalspecs:

            checkfield(self, 'nsig')

            if self.nsig>0:
                # signals is not always required because this method is called via wrheader. 
                # Enforce the presence of signals at the start of rdsamp to ensure it gets added here. 
                if self.signals!=None:
                    reqfields.append('signals')

                reqfields=reqfields+getreqsubset(self, reversed(list(fieldspeclist[2].items())))

        # Multi-segment record
        else:
            # Segment specification fields and segments
            reqfields=reqfields+['segments', 'seglen', 'segname']

        # Comments
        if self.comments !=None:
            reqfields.append('comments')
        return reqfields


    # Helper function to getreqfields
    def getreqsubset(self, fieldspecs):
        reqfields=[]
        for f in fieldspecs:
            if f in reqfields:
                continue
            # If the field is default required or has been defined by the user...
            if f[1].write_req or self.f!=None:
                rf=f
                # Add the field and its recurrent dependencies
                while rf!=None:
                    reqfields.append(rf)
                    rf=fieldspeclist[1][rf].dependency

        return reqfields
            
   
       
            
            
# Class representing a single segment WFDB record.
class WFDBrecord(WFDBbaserecord):
    
    # Constructor
    def __init__(self, p_signals=None, d_signals=None, recordname=None, 
                 nsig=None, 
                 fs=None, counterfreq=None, basecounter=None, 
                 siglen=None, basetime=None, basedate=None, 
                 filename=None, fmt=None, sampsperframe=None, 
                 skew=None, byteoffset=None, adcgain=None, 
                 baseline=None, units=None, adcres=None, 
                 adczero=None, initvalue=None, checksum=None, 
                 blocksize=None, signame=None, comments=None):
        
        # Note the lack of 'nseg' field. Single segment records cannot have this field. Even nseg = 1 makes 
        # the header a multi-segment header. 
        
        super(self, recordname=recordname, nsig=nsig, 
              fs=fs, counterfreq=counterfreq, basecounter =basecounter,
              siglen = siglen, basetime = basetime, basedate = basedate, 
              comments = comments)
        
        self.p_signals = p_signals
        self.d_signals = d_signals
        
        self.filename=filename
        self.fmt=fmt
        self.sampsperframe=sampsperframe
        self.skew=skew
        self.byteoffset=byteoffset
        self.adcgain=adcgain
        self.baseline=baseline
        self.units=units
        self.adcres=adcres
        self.adczero=adczero
        self.initvalue=initvalue
        self.checksum=checksum
        self.blocksize=blocksize
        self.signame=signame
                                 
        
    # Set missing fields that a default, or can be inferred.
    # This method does NOT overwrite values. 
    # If a field requires another field which is invalid or not set, just return. 
    def setfields(self, fieldstoset = getreqfields(self, singlefieldspeclist.copy())):
                                 
        # Set the missing required fields if possible. 
        for f in fieldstoset:
            # Do not overwrite fields set by the user
            if f == None:
                setfield(self, f)
    
    
    # Check the specified fields of the WFDBrecord object for validity. 
    def checkfields(self ,fieldstocheck = getreqfields(self), objecttype='WFDBrecord'):
        
        fielderrors=[]
        
        # Check for foreign fields
        _checkforeignfields(self, allowedfields = self.getallowedfields())
        
        # Check whether the fields' values are valid. 
        _checkfieldvalues(self, fieldstocheck)
        
                
    # Return a list of all the fields this class is allowed to have    
    def getallowedfields():
        return list(mergeODlist(singlefieldspeclist).keys())
    
    


# Multi segment WFDB record. Stores a list of individual WFDBrecord objects in the 'segment' field.
class WFDBmultirecord():
     def __init__(self, segments=None, recordname=None, nseg=None, nsig=None, 
                  fs=None, counterfreq=None, basecounter=None,
                  siglen=None, basetime=None, basedate=None,
                  seglen=None, segname=None, segment=None, 
                  comments=None):
        
        # Perhaps this should go in the checking functions below...
        if nseg==None or nseg<1:
            sys.exit("The WFDBmultirecord class is for multi-segment "
                     "records. The 'nseg' field must be specified."
                     "\nUse the 'WFDBrecord' class for creating "
                     "single segment records.")
    
        super(self, recordname=recordname, nsig=nsig, 
              fs=fs, counterfreq=counterfreq, basecounter =basecounter,
              siglen = siglen, basetime = basetime, basedate = basedate, 
              comments = comments)
    
        self.segments=sements  
        self.nseg=nseg
        
        self.seglen=seglen
        self.segname=segname
    
    # Return a list of all the fields this class is allowed to have    
    def getallowedfields():
        return list(mergeODlist(multifieldspeclist).keys())
        


# The specifications of a WFDB field
class WFDBfieldspecs():
    
    def __init__(self, speclist):
    
        # Data types the field can take
        self.allowedtypes = speclist[0]
        
        # The text delimiter that preceeds the field if it is a field that gets written to header files.
        self.delimiter = speclist[1]
        
        # The required/dependent field which must also be present
        self.dependency = speclist[2]
        
        # Whether the field is mandatory for writing a header (WFDB requirements + extra rules enforced by this library).
        # Being required for writing is not the same as the user having to specify via wrsamp/wrhea.
        self.write_req = speclist[3]
        
        
# The signal field and its physical indicator
signalspecs = OrderedDict([('signal', WFDBfield([[np.ndarray], None, None, False])),
                          ('physical', WFDBfield([[bool], None, None, False]))])

# The segment field. A list of WFDBrecord objects
segmentspecs = OrderedDict([('segment', WFDBfield([[list], None, None, True]))])

# Record specification fields            
recfieldspecs = OrderedDict([('recordname', WFDBfield([[str], '', None, True])),
                         ('nseg', WFDBfield([[int], '/', 'recordname', True])), # Essential for multi but not present in single.
                         ('nsig', WFDBfield([[int], ' ', 'recordname', True])),
                         ('fs', WFDBfield([[int, float], ' ', 'nsig', True])),
                         ('counterfreq', WFDBfield([[int, float], '/', 'fs', False])),
                         ('basecounter', WFDBfield([[int, float], '(', 'counterfreq', False])),
                         ('siglen', WFDBfield([[int], ' ', 'fs', True])),
                         ('basetime', WFDBfield([[str], ' ', 'siglen', False])),
                         ('basedate', WFDBfield([[str], ' ', 'basetime', False]))])
# Signal specification fields. Type will be list. Maybe numpy nd array?
sigfieldspecs = OrderedDict([('filename', WFDBfield([[str], '', None, True])),
                         ('fmt', WFDBfield([[int, str], ' ', 'filename', True])),
                         ('sampsperframe', WFDBfield([[int], 'x', 'fmt', False])),
                         ('skew', WFDBfield([[int], ':', 'fmt', False])),
                         ('byteoffset', WFDBfield([[int], '+', 'fmt', False])),
                         ('adcgain', WFDBfield([[int, float], ' ', 'fmt', True])),
                         ('baseline', WFDBfield([[int], '(', 'adcgain', True])),
                         ('units', WFDBfield([[str], '/', 'adcgain', True])),
                         ('adcres', WFDBfield([[int], ' ', 'adcgain', False])),
                         ('adczero', WFDBfield([[int], ' ', 'adcres', False])),
                         ('initvalue', WFDBfield([[int], ' ', 'adczero', False])),
                         ('checksum', WFDBfield([[int], ' ', 'initvalue', False])),
                         ('blocksize', WFDBfield([[int], ' ', 'checksum', False])),
                         ('signame', WFDBfield([[str], ' ', 'blocksize', False]))])
    
# Segment specification fields. Type will be list. 
segfieldspecs = OrderedDict([('segname', WFDBfield([[str], '', None, True, 0])),
                         ('seglen', WFDBfield([[int], ' ', 'segname', True, 0]))])
# Comment field
comfieldspecs = OrderedDict([('comments', WFDBfield([[int], '', None, False, False]))])

# I don't think I need these ... I need something else
singlefieldspeclist = [signalspecs.copy(), recfieldspecs.copy(), sigfieldspecs.copy(), comfieldspecs.copy()]
del(singlefieldspeclist[1]['nseg']
multifieldspeclist = [segmentspecs.copy(), recfieldspecs.copy(), segfieldspecs.copy(), comfieldspecs.copy()]

allfieldspecs = mergeODlist([signalspecs, segmentspecs, recfieldspecs, sigfieldspecs, segfieldspecs, comfieldspecs])


# The useful summary information contained in a wfdb record.
# Note: NOT a direct subset of WFDBrecord's fields. 
infofields = [['recordname',
               'nseg',
               'nsig',
               'fs',
               'siglen',
               'basetime',
               'basedate'],
              
              ['filename',
               'maxresolution',
               'sampsperframe',
               'units',
               'signame'],
              
              ['segname',
               'seglen'],
              
              ['comments']]

# Write a single segment wfdb header file.
# record is a WFDBrecord object
def wrheader(record, targetdir=os.cwd()):
    
    # The fields required to write this header
    requiredfields = record.getreqfields()
    
    # Fill in any missing info possible 
    # for the set of required fields
    record.setfields(requiredfields)
    
    # Check every field to be used
    record.checkfields(requiredfields)  
    
    # Write the output header file
    writeheaderfile(record)
    
    # The reason why this is more complicated than the ML toolbox's rdsamp:
    # That one only accepts a few fields, and sets defaults for the rest. 
    # This one accepts any combination of fields and tries to set what it can. Also does checking. 
        
        
        
# Write a multi-segment wfdb header file. 
def wrmultiheader(recinfo, targetdir=os.cwd(), setinfo=0):
    
    # Make sure user is not trying to write single segment headers. 
    if getattr(recinfo, 'nseg')!=None:
        if type(getattr(recinfo, 'nseg'))!= int:
            
            sys.exit("The 'nseg' field must be an integer.")
            
        if getattr(recinfo, 'nseg')==0:
            
            sys.exit("The 'nseg' field is 0. You cannot write a multi-segment header with zero segments.")
            
        elif getattr(recinfo, 'nseg')==1:
            
            print("Warning: The 'nseg' field is 1. You are attempting to write a multi-segment header which encompasses only one segment.\nContinuing ...")
            
    else:
        sys.exit("Missing input field 'nseg' for writing multi-segment header.\nFor writing regular WFDB headers, use the 'wrheader' function.")
                  
    
    WFDBfieldlist = [recfields.copy(), segfields.copy(), comfields.copy()]
                  
    
    keycheckedfields = _checkheaderkeys(inputfields, WFDBfieldlist, setsigreqs, 1)
    
    # Check the header values
    valuecheckedfields = checkheadervalues(keycheckedfields, WFDBfields, setsigreqs, 0)
    
    # check that each signal component has the same fs and the correct number of signals. 
    
    # Write the header file
    

    
# Merge the ordered dictionaries in a list into one ordered dictionary. 
# Belongs to the module
def _mergeODlist(ODlist):
    mergedOD=ODlist[0].copy()
    for od in ODlist[1:]:
        mergedOD.update(od)
    return mergedOD
                  

              
    
    
    
    
    
    
    
def _writeheaderfile(fields):
    
    f=open(fields['recordname']+'.hea','w')
    
    
    
    f.close()
    
    
    
    
    

    


    
    
# For reading WFDB header files
def rdheader(recordname): 

    # To do: Allow exponential input format for some fields

    # Output dictionary
    fields=WFDBfields
    
    # filename stores file names for both multi and single segment headers.
    # nsampseg is only for multi-segment


    # RECORD LINE fields (o means optional, delimiter is space or tab unless specified):
    # record name, nsegments (o, delim=/), nsignals, fs (o), counter freq (o, delim=/, needs fs),
    # base counter (o, delim=(), needs counter freq), siglen (o, needs fs), base time (o),
    # base date (o needs base time).

    # Regexp object for record line
    rxRECORD = re.compile(
        ''.join(
            [
                "(?P<name>[\w]+)/?(?P<nseg>\d*)[ \t]+",
                "(?P<nsig>\d+)[ \t]*",
                "(?P<fs>\d*\.?\d*)/*(?P<counterfs>\d*\.?\d*)\(?(?P<basecounter>\d*\.?\d*)\)?[ \t]*",
                "(?P<siglen>\d*)[ \t]*",
                "(?P<basetime>\d*:?\d{,2}:?\d{,2}\.?\d*)[ \t]*",
                "(?P<basedate>\d{,2}/?\d{,2}/?\d{,4})"]))
    # Watch out for potential floats: fs (and also exponent notation...),
    # counterfs, basecounter

    # SIGNAL LINE fields (o means optional, delimiter is space or tab unless specified):
    # file name, format, samplesperframe(o, delim=x), skew(o, delim=:), byteoffset(o,delim=+),
    # ADCgain(o), baseline(o, delim=(), requires ADCgain), units(o, delim=/, requires baseline),
    # ADCres(o, requires ADCgain), ADCzero(o, requires ADCres), initialvalue(o, requires ADCzero),
    # checksum(o, requires initialvalue), blocksize(o, requires checksum),
    # signame(o, requires block)

    # Regexp object for signal lines. Consider flexible filenames, and also ~
    rxSIGNAL = re.compile(
        ''.join(
            [
                "(?P<filename>[\w]*\.?[\w]*~?)[ \t]+(?P<format>\d+)x?"
                "(?P<sampsperframe>\d*):?(?P<skew>\d*)\+?(?P<byteoffset>\d*)[ \t]*",
                "(?P<ADCgain>-?\d*\.?\d*e?[\+-]?\d*)\(?(?P<baseline>-?\d*)\)?/?(?P<units>[\w\^/-]*)[ \t]*",
                "(?P<ADCres>\d*)[ \t]*(?P<ADCzero>-?\d*)[ \t]*(?P<initialvalue>-?\d*)[ \t]*",
                "(?P<checksum>-?\d*)[ \t]*(?P<blocksize>\d*)[ \t]*(?P<signame>[\S]*)"]))

    # Units characters: letters, numbers, /, ^, -,
    # Watch out for potentially negative fields: baseline, ADCzero, initialvalue, checksum,
    # Watch out for potential float: ADCgain.

    # Read the header file and get the comment and non-comment lines
    headerlines, commentlines = _getheaderlines(recordname)

    # Get record line parameters
    (_, nseg, nsig, fs, counterfs, basecounter, siglen,
    basetime, basedate) = rxRECORD.findall(headerlines[0])[0]

    # These fields are either mandatory or set to defaults.
    if not nseg:
        nseg = '1'
    if not fs:
        fs = '250'

    fields['nseg'] = int(nseg)
    fields['fs'] = float(fs)
    fields['nsig'] = int(nsig)
    fields['recordname'] = name

    # These fields might by empty
    if siglen:
        fields['siglen'] = int(siglen)
    fields['basetime'] = basetime
    fields['basedate'] = basedate


    # Signal or Segment line paramters
    # Multi segment header - Process segment spec lines in current master
    # header.
    if int(nseg) > 1:
        for i in range(0, int(nseg)):
            (filename, nsampseg) = re.findall(
                '(?P<filename>\w*~?)[ \t]+(?P<nsampseg>\d+)', headerlines[i + 1])[0]
            fields["filename"].append(filename)
            fields["nsampseg"].append(int(nsampseg))
    # Single segment header - Process signal spec lines in regular header.
    else:
        for i in range(0, int(nsig)):  # will not run if nsignals=0
            # get signal line parameters
            (filename,
            fmt,
            sampsperframe,
            skew,
            byteoffset,
            adcgain,
            baseline,
            units,
            adcres,
            adczero,
            initvalue,
            checksum,
            blocksize,
            signame) = rxSIGNAL.findall(headerlines[i + 1])[0]
            
            # Setting defaults
            if not sampsperframe:
                # Setting strings here so we can always convert strings case
                # below.
                sampsperframe = '1'
            if not skew:
                skew = '0'
            if not byteoffset:
                byteoffset = '0'
            if not adcgain:
                adcgain = '200'
            if not baseline:
                if not adczero:
                    baseline = '0'
                else:
                    baseline = adczero  # missing baseline actually takes adczero value if present
            if not units:
                units = 'mV'
            if not initvalue:
                initvalue = '0'
            if not signame:
                signame = "ch" + str(i + 1)
            if not initvalue:
                initvalue = '0'

            fields["filename"].append(filename)
            fields["fmt"].append(fmt)
            fields["sampsperframe"].append(int(sampsperframe))
            fields["skew"].append(int(skew))
            fields['byteoffset'].append(int(byteoffset))
            fields["gain"].append(float(adcgain))
            fields["baseline"].append(int(baseline))
            fields["units"].append(units)
            fields["initvalue"].append(int(initvalue))
            fields["signame"].append(signame)

    for comment in commentlines:
        fields["comments"].append(comment.strip('\s#'))

    return fields


# Read header file to get comment and non-comment lines
def _getheaderlines(recordname):
    with open(recordname + ".hea", 'r') as fp:
        headerlines = []  # Store record line followed by the signal lines if any
        commentlines = []  # Comments
        for line in fp:
            line = line.strip()
            if line.startswith('#'):  # comment line
                commentlines.append(line)
            elif line:  # Non-empty non-comment line = header line.
                ci = line.find('#')
                if ci > 0:
                    headerlines.append(line[:ci])  # header line
                    # comment on same line as header line
                    commentlines.append(line[ci:])
                else:
                    headerlines.append(line)
    return headerlines, commentlines


# Create a multi-segment header file
def wrmultisegheader():
    