#!/usr/bin/env python

# A part of pdfrw (pdfrw.googlecode.com)
# Copyright (C) 2006-2009 Patrick Maupin, Austin, Texas
# MIT license -- See LICENSE.txt for details

'''
The PdfWriter class writes an entire PDF file out to disk.

The writing process is not at all optimized or organized.

An instance of the PdfWriter class has two methods:
    addpage(page)
and
    write(fname)

addpage() assumes that the pages are part of a valid
tree/forest of PDF objects.
'''

from pdfobjects import PdfName, PdfArray, PdfDict, IndirectPdfDict, PdfObject
from pdfcompress import compress

debug = False

class FormatObjects(object):
    ''' FormatObjects performs the actual formatting and disk write.
    '''

    def add(self, obj):
        ''' Add an object to our list, if it's an indirect
            object.  Just format it if not.
        '''
        # Can't hash dicts, so just hash the object ID
        objid = id(obj)

        # Automatically set stream objects to indirect
        if isinstance(obj, PdfDict):
            indirect = obj.indirect or (obj.stream is not None)
        else:
            indirect = getattr(obj, 'indirect', False)

        if not indirect:
            visited = self.visited
            assert objid not in visited, \
                'Circular reference encountered in non-indirect object %s' % repr(obj)
            visited.add(objid)
            result = self.format_obj(obj)
            visited.remove(objid)
            return result

        objnum = self.indirect_dict.get(objid)

        # If we haven't seen the object yet, we need to
        # add it to the indirect object list.
        if objnum is None:
            objlist = self.objlist
            objnum = len(objlist) + 1
            if debug:
                print '  Object', objnum, '\r',
            objlist.append(None)
            self.indirect_dict[objid] = objnum
            objlist[objnum-1] = self.format_obj(obj)
        return '%s 0 R' % objnum

    @staticmethod
    def format_array(myarray, formatter):
        # Format array data into semi-readable ASCII
        if sum(len(x) for x in myarray) <= 70:
            return formatter % ' '.join(myarray)
        bigarray = []
        count = 1000000
        for x in myarray:
            lenx = len(x)
            if lenx + count > 70:
                subarray = []
                bigarray.append(subarray)
                count = 0
            count += lenx + 1
            subarray.append(x)
        return formatter % '\n  '.join(' '.join(x) for x in bigarray)

    def format_obj(self, obj):
        ''' format PDF object data into semi-readable ASCII.
            May mutually recurse with add() -- add() will
            return references for indirect objects, and add
            the indirect object to the list.
        '''
        if isinstance(obj, PdfArray):
            myarray = [self.add(x) for x in obj]
            return self.format_array(myarray, '[%s]')
        elif isinstance(obj, PdfDict):
            if self.compress and obj.stream:
                compress([obj])
            myarray = []
            for key, value in sorted(obj.iteritems()):
                myarray.append(key)
                myarray.append(self.add(value))
            result = self.format_array(myarray, '<<%s>>')
            stream = obj.stream
            if stream is not None:
                result = '%s\nstream\n%s\nendstream' % (result, stream)
            return result
        else:
            return str(obj)

    @classmethod
    def dump(cls, f, trailer, version='1.3', compress=True):
        self = cls()
        self.compress = compress
        self.indirect_dict = {}
        self.objlist = []
        self.visited = set()

        # The first format of trailer gets all the information,
        # but we throw away the actual trailer formatting.
        self.format_obj(trailer)
        # Now we know the size, so we update the trailer dict
        # and get the formatted data.
        trailer.Size = PdfObject(len(self.objlist) + 1)
        trailer = self.format_obj(trailer)

        # Now we have all the pieces to write out to the file.
        # Keep careful track of the counts while we do it so
        # we can correctly build the cross-reference.

        header = '%%PDF-%s\n%%\xe2\xe3\xcf\xd3\n' % version
        f.write(header)
        offset = len(header)
        offsets = [(0, 65535, 'f')]

        for i, x in enumerate(self.objlist):
            objstr = '%s 0 obj\n%s\nendobj\n' % (i + 1, x)
            offsets.append((offset, 0, 'n'))
            offset += len(objstr)
            f.write(objstr)

        f.write('xref\n0 %s\n' % len(offsets))
        for x in offsets:
            f.write('%010d %05d %s\r\n' % x)
        f.write('trailer\n\n%s\nstartxref\n%s\n%%%%EOF\n' % (trailer, offset))


class PdfWriter(object):

    def __init__(self, version='1.3', compress=True):
        self.pagearray = pagearray = PdfArray()
        self.compress = compress
        self.version = version

    def addpage(self, page):
        assert page.Type == PdfName.Page
        self.pagearray.append(IndirectPdfDict(page))

    def write(self, fname):
        pagearray = self.pagearray
        pagedict = IndirectPdfDict(
            Type = PdfName.Pages,
            Count = PdfObject(len(pagearray)),
            Kids = pagearray
        )
        for page in pagearray:
            page.Parent = pagedict
        rootdict = IndirectPdfDict(
            Type = PdfName.Catalog,
            Pages = pagedict
        )

        trailer = PdfDict(Root=rootdict)
        f = open(fname, 'wb')
        FormatObjects.dump(f, trailer, self.version, self.compress)
        f.close()

if __name__ == '__main__':
    debug = True
    import pdfreader
    from pdftokens import PdfTokens
    x = pdfreader.PdfReader('source.pdf')
    y = PdfWriter()
    for i, page in enumerate(x.pages):
        print '  Adding page', i+1, '\r',
        y.addpage(page)
    print
    y.write('result.pdf')
    print
