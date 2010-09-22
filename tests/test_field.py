#
# Copyright CERN, 2010.
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements. See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the
# specific language governing permissions and limitations
# under the License.
#

import unittest
import cStringIO

from fudge import registry
REGISTRY = registry.DEFAULT_REGISTRY

from fudge import message
from fudge.field import *
from fudge.taxonomy.map import Taxonomy

INDICATOR_FIELD = REGISTRY.type_by_id(types.INDICATOR_TYPE_ID)
BYTE_FIELD = REGISTRY.type_by_id(types.BYTE_TYPE_ID)
INT_FIELD = REGISTRY.type_by_id(types.INT_TYPE_ID)
STRING_FIELD = REGISTRY.type_by_id(types.STRING_TYPE_ID)
INTARRAY_FIELD = REGISTRY.type_by_id(types.INTARRAY_TYPE_ID)
FUDGEMSG_FIELD = REGISTRY.type_by_id(types.FUDGEMSG_TYPE_ID)

class testField(unittest.TestCase):
    def setUp(self):
        pass

    def encodeEquals(self, expected, f, taxonomy=None):
        output = cStringIO.StringIO()
        f.encode(output, taxonomy)
        # Allow us to compare easily using \xDF etc..
        result = output.getvalue().encode('hex')
        self.assertEquals(expected, result)

    def test_bytes_for_value_length(self):
        """Check we use the correct variable width for a variety
        of value lengths"""

        self.assertEquals(0, bytes_for_value_length(0))

        self.assertEquals(1, bytes_for_value_length(1 ))
        self.assertEquals(1, bytes_for_value_length(utils.MAX_BYTE))

        self.assertEquals(2, bytes_for_value_length(utils.MAX_BYTE+1))
        self.assertEquals(2, bytes_for_value_length(utils.MAX_SHORT))

        self.assertEquals(4, bytes_for_value_length(utils.MAX_SHORT+1))
        self.assertEquals(4, bytes_for_value_length(utils.MAX_INT))

        self.assertRaises(AssertionError, bytes_for_value_length, utils.MAX_INT+1)
        self.assertRaises(AssertionError, bytes_for_value_length, -1)

    def test_size_no_opts_fixed(self):
        """Test the simplest case"""
        f = Field(BYTE_FIELD, None, None, 0x01)
        self.assertEquals(3, f.size())
        self.encodeEquals('800201', f)

        f = Field(INT_FIELD, None, None, 0x80000000)
        self.assertEquals(6, f.size())
        self.encodeEquals('800480000000', f)

    def test_size_no_opts_variable(self):
        f= Field(STRING_FIELD, None, None, u'foo')
        self.assertEquals(6, f.size())
        self.encodeEquals('200e03'+u'foo'.encode('hex'), f)

    def test_size_ordinal(self):
        f = Field(BYTE_FIELD, 0x01, None, 0x01)
        self.assertEquals(5, f.size())
        self.encodeEquals('9002000101', f)

        f = Field(INT_FIELD, 0x02, None, 0x80000001)
        self.encodeEquals('9004000280000001', f)

        self.assertEquals(8, f.size())

    def test_size_name(self):
        f = Field(BYTE_FIELD, None, u'foo', 0x01)
        self.assertEquals(7, f.size())
        self.encodeEquals('880203'+u'foo'.encode('hex')+'01', f)

        f = Field(BYTE_FIELD, None, u'foobarbaz', 0x02)
        self.assertEquals(13, f.size())
        self.encodeEquals('880209'+u'foobarbaz'.encode('hex')+'02', f)

    def test_both(self):
        f = Field(BYTE_FIELD, 0x01, u'foo', 0x01)
        self.assertEquals(9, f.size())
        self.encodeEquals('9802000103'+u'foo'.encode('hex')+'01', f)

        f = Field(BYTE_FIELD, 0x02, u'foobarbaz', 0x02)
        self.assertEquals(15, f.size())
        self.encodeEquals('9802000209'+u'foobarbaz'.encode('hex')+'02', f)

    def test_indicator(self):
        f = Field(INDICATOR_FIELD, None, None, None)
        self.assertEquals(2, f.size())
        self.encodeEquals('8000', f)
        result, bytes = Field.decode('\x80\x00')
        self.assertEqual(2, bytes)
        self.assertEquals(types.INDICATOR, result.value)

    def test_size_with_taxonomy(self):
        f = Field(BYTE_FIELD, None, u'foo', 0xff)
        t = Taxonomy({1 : u'foo', 2 : u'bar'})

        self.assertEquals(7, f.size())
        self.encodeEquals('880203'+u'foo'.encode('hex')+'ff', f)

        self.assertEquals(5, f.size(t))
        self.encodeEquals('90020001ff', f, t)

    def test_bad_encoded(self):
        # incomplete headers
        self.assertRaises(AssertionError, Field.decode, '')
        self.assertRaises(AssertionError, Field.decode, '\x88')

        # TODO(jamesc) better decode error handling
        #Field.decode('\x88\x02\x01')

    def test_empty_variable(self):
        "Test that empty variable length fields are encoded correctly."
        f = Field(STRING_FIELD, None, None, u'')
        self.assertEquals(2, f.size())
        self.encodeEquals('000e', f)

        f2, bytes = Field.decode('\x00\x0e')
        self.assertEquals(2, bytes)
        self.assertEquals(u'', f2.value)

    def test_empty_intarray(self):
        "Test that empty variable length fields are encoded correctly."
        f = Field(INTARRAY_FIELD, None, None, [])
        self.assertEquals(2, f.size())
        self.encodeEquals('0008', f)

        f2, bytes = Field.decode('\x00\x08')
        self.assertEquals(2, bytes)
        self.assertEquals([], f2.value)

    def test_messagefield(self):
        "Test a Fudge Msg field is encoded/decoded ok"
        m = message.Message()
        m.add(u'')
        m.add(types.INDICATOR)
        f = Field(FUDGEMSG_FIELD, None, None, m)
        self.assertEquals(7, f.size())
        self.encodeEquals('200f04000e8000', f)

        res, bytes = Field.decode('\x20\x0f\x04\x00\x0e\x80\x00')
        self.assertEquals(7, bytes)
        m = res.value
        self.assertEquals(2, len(m.fields))

    def test_deepermsg(self):
        "Test a deep message is ok"
        m = message.Message()
        m.add(u'foo')
        m.add(u'bar')
        m.add(types.INDICATOR)

        m2 = message.Message()
        m2.add(0xf1, classname='int')
        m.add(m2)

        f = Field(FUDGEMSG_FIELD, None, None, m)
        self.assertEquals(23, f.size())
        self.encodeEquals('200f14200e03' + u'foo'.encode('hex') + \
                '200e03' + u'bar'.encode('hex') +  \
                '8000' + # INDICATOR \
                '200f038002f1' , f)

