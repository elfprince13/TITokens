#!python
# Komodo TI-Basic language service.

"""Language package for TI-Basic"""

import os
import re
import logging

import process
import koprocessutils

from koLanguageServiceBase import *
from koUDLLanguageBase import KoUDLLanguage
from xpcom import components, ServerException
import xpcom.server

sci_constants = components.interfaces.ISciMoz


log = logging.getLogger("koTIBasicLanguage")
log.setLevel(logging.DEBUG)


def registerLanguage(registry):
    log.debug("Registering language TI-Basic")
    registry.registerLanguage(KoTIBasicLanguage())


class KoTIBasicLanguage(KoUDLLanguage):#, KoLanguageBaseDedentMixin):
    name = "TIBasic"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_clsid_ = "2f26219b-d6e2-4f27-a00b-9bdc5374b902"
    _reg_categories_ = [("komodo-language", name)]
    _com_interfaces_ = [components.interfaces.koILanguage,
                        components.interfaces.nsIObserver]

    lexresLangName = "TIBasic"
    lang_from_udl_family = { 'SSL' : 'TIBasic'}
     
    defaultExtension = ".tib"
    downloadURL = 'http://www.cemetech.net'
    commentDelimiterInfo = {
        "line": [ "//" ]
    }

    sample = """Disp "Hello World"
5->A
3->B
A+B->C
Pause C
ClrHome"""

    #def __init__(self):
    #    KoUDLLanguage.__init__(self)
    #    KoLanguageBaseDedentMixin.__init__(self)
    #    
    #    self.matchingSoftChars = {"(": (")", None),
    #                              "{": ("}", None),
    #                              "[": ("]", None),
    #                              '"': ('"', self.softchar_accept_matching_double_quote)
    #                              }            
    #    
    #    self._setupIndentCheckSoftChar()


