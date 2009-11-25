# A part of pdfrw (pdfrw.googlecode.com)
# Copyright (C) 2006-2009 Patrick Maupin, Austin, Texas
# MIT license -- See LICENSE.txt for details

'''
Converts pdfrw objects into reportlab objects.

Designed for and tested with rl 2.3.

Knows too much about reportlab internals.
What can you do?

The interface to this function is through the makerl() function.

Parameters:
        rldoc       - a reportlab "document"
        pdfobj      - a top-level pdfrw PDF object
        isxobj      - set True if pdfobj is an XObject

Returns:
        A corresponding reportlab object, or the object
        name if the object is an Xobject.  (Reportlab
        seems weird about Xobjects.)

Notes:
    1) Original objects are annotated with a
        _rl_obj attribute which points to the
        reportlab object.  This is great for
        not putting too many objects into the
        new PDF, but not so good if you are modifying
        objects for different pages.  Then you
        need to do your own deep copying (of circular
        structures).  You're on your own.

makerl(rldoc, pdfobj, isxobj=False):

'''

from reportlab.pdfbase import pdfdoc as rldocmodule
from pdfobjects import PdfDict, PdfArray

RLStream = rldocmodule.PDFStream
RLDict = rldocmodule.PDFDictionary
RLArray = rldocmodule.PDFArray


def _makedict(rldoc, pdfobj, isxobj):
    assert isinstance(pdfobj, PdfDict)
    assert pdfobj.stream is None
    assert pdfobj._rl_obj is None
    assert not isxobj

    rlobj = rldict = RLDict()
    if pdfobj.indirect:
        rlobj.__RefOnly__ = 1
        rlobj = rldoc.Reference(rlobj)
    pdfobj._rl_obj = rlobj

    for key, value in pdfobj.iteritems():
        rldict[key[1:]] = makerl(rldoc, value)

    return rlobj

def _makestream(rldoc, pdfobj, isxobj):
    assert isinstance(pdfobj, PdfDict)
    assert pdfobj.stream is not None
    assert pdfobj._rl_obj is None

    if isxobj:
        name = 'pdfrw_%s' % (rldoc.objectcounter+1)
        xobjname = rldoc.getXObjectName(name)
    else:
        name = xobjname = None
    rldict = RLDict()
    rlobj = RLStream(rldict, pdfobj.stream)
    rlobj = rldoc.Reference(rlobj, xobjname)
    pdfobj._rl_obj = rlobj

    for key, value in pdfobj.iteritems():
        rldict[key[1:]] = makerl(rldoc, value)

    return name or rlobj

def _makearray(rldoc, pdfobj, isxobj):
    assert isinstance(pdfobj, PdfArray)
    assert pdfobj._rl_obj is None
    assert not isxobj

    mylist = []
    rlobj = rlarray = RLArray(mylist)
    if pdfobj.indirect:
        rlobj.__RefOnly__ = 1
        rlobj = rldoc.Reference(rlobj)
    pdfobj._rl_obj = rlobj

    for value in pdfobj:
        mylist.append(makerl(rldoc, value))

    return rlobj

def _makestr(rldoc, pdfobj, isxobj):
    assert not isxobj
    assert isinstance(pdfobj, (float, int, str)), repr(pdfobj)
    return pdfobj

def makerl(rldoc, pdfobj, isxobj=False):
    value = getattr(pdfobj, '_rl_obj', None)
    if value is not None:
        return value
    if isinstance(pdfobj, PdfDict):
        if pdfobj.stream is not None:
            func = _makestream
        else:
            func = _makedict
    elif isinstance(pdfobj, PdfArray):
        func = _makearray
    else:
        func = _makestr
    return func(rldoc, pdfobj, isxobj)
