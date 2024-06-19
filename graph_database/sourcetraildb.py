# This file was automatically generated by SWIG (http://www.swig.org).
# Version 2.0.11
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.





from sys import version_info
if version_info >= (2,6,0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('_sourcetraildb', [dirname(__file__)])
        except ImportError:
            import _sourcetraildb
            return _sourcetraildb
        if fp is not None:
            try:
                _mod = imp.load_module('_sourcetraildb', fp, pathname, description)
            finally:
                fp.close()
            return _mod
    _sourcetraildb = swig_import_helper()
    del swig_import_helper
else:
    import _sourcetraildb
del version_info
try:
    _swig_property = property
except NameError:
    pass # Python < 2.2 doesn't have 'property'.
def _swig_setattr_nondynamic(self,class_type,name,value,static=1):
    if (name == "thisown"): return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name,None)
    if method: return method(self,value)
    if (not static):
        self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)

def _swig_setattr(self,class_type,name,value):
    return _swig_setattr_nondynamic(self,class_type,name,value,0)

def _swig_getattr(self,class_type,name):
    if (name == "thisown"): return self.this.own()
    method = class_type.__swig_getmethods__.get(name,None)
    if method: return method(self)
    raise AttributeError(name)

def _swig_repr(self):
    try: strthis = "proxy of " + self.this.__repr__()
    except: strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except AttributeError:
    class _object : pass
    _newclass = 0


DEFINITION_IMPLICIT = _sourcetraildb.DEFINITION_IMPLICIT
DEFINITION_EXPLICIT = _sourcetraildb.DEFINITION_EXPLICIT
SYMBOL_TYPE = _sourcetraildb.SYMBOL_TYPE
SYMBOL_BUILTIN_TYPE = _sourcetraildb.SYMBOL_BUILTIN_TYPE
SYMBOL_MODULE = _sourcetraildb.SYMBOL_MODULE
SYMBOL_NAMESPACE = _sourcetraildb.SYMBOL_NAMESPACE
SYMBOL_PACKAGE = _sourcetraildb.SYMBOL_PACKAGE
SYMBOL_STRUCT = _sourcetraildb.SYMBOL_STRUCT
SYMBOL_CLASS = _sourcetraildb.SYMBOL_CLASS
SYMBOL_INTERFACE = _sourcetraildb.SYMBOL_INTERFACE
SYMBOL_ANNOTATION = _sourcetraildb.SYMBOL_ANNOTATION
SYMBOL_GLOBAL_VARIABLE = _sourcetraildb.SYMBOL_GLOBAL_VARIABLE
SYMBOL_FIELD = _sourcetraildb.SYMBOL_FIELD
SYMBOL_FUNCTION = _sourcetraildb.SYMBOL_FUNCTION
SYMBOL_METHOD = _sourcetraildb.SYMBOL_METHOD
SYMBOL_ENUM = _sourcetraildb.SYMBOL_ENUM
SYMBOL_ENUM_CONSTANT = _sourcetraildb.SYMBOL_ENUM_CONSTANT
SYMBOL_TYPEDEF = _sourcetraildb.SYMBOL_TYPEDEF
SYMBOL_TYPE_PARAMETER = _sourcetraildb.SYMBOL_TYPE_PARAMETER
SYMBOL_MACRO = _sourcetraildb.SYMBOL_MACRO
SYMBOL_UNION = _sourcetraildb.SYMBOL_UNION
REFERENCE_TYPE_USAGE = _sourcetraildb.REFERENCE_TYPE_USAGE
REFERENCE_USAGE = _sourcetraildb.REFERENCE_USAGE
REFERENCE_CALL = _sourcetraildb.REFERENCE_CALL
REFERENCE_INHERITANCE = _sourcetraildb.REFERENCE_INHERITANCE
REFERENCE_OVERRIDE = _sourcetraildb.REFERENCE_OVERRIDE
REFERENCE_TYPE_ARGUMENT = _sourcetraildb.REFERENCE_TYPE_ARGUMENT
REFERENCE_TEMPLATE_SPECIALIZATION = _sourcetraildb.REFERENCE_TEMPLATE_SPECIALIZATION
REFERENCE_INCLUDE = _sourcetraildb.REFERENCE_INCLUDE
REFERENCE_IMPORT = _sourcetraildb.REFERENCE_IMPORT
REFERENCE_MACRO_USAGE = _sourcetraildb.REFERENCE_MACRO_USAGE
REFERENCE_ANNOTATION_USAGE = _sourcetraildb.REFERENCE_ANNOTATION_USAGE

def getVersionString():
  """getVersionString() -> std::string"""
  return _sourcetraildb.getVersionString()

def getSupportedDatabaseVersion():
  """getSupportedDatabaseVersion() -> int"""
  return _sourcetraildb.getSupportedDatabaseVersion()

def getLastError():
  """getLastError() -> std::string"""
  return _sourcetraildb.getLastError()

def clearLastError():
  """clearLastError()"""
  return _sourcetraildb.clearLastError()

def open(*args):
  """open(std::string databaseFilePath) -> bool"""
  return _sourcetraildb.open(*args)

def close():
  """close() -> bool"""
  return _sourcetraildb.close()

def clear():
  """clear() -> bool"""
  return _sourcetraildb.clear()

def isEmpty():
  """isEmpty() -> bool"""
  return _sourcetraildb.isEmpty()

def isCompatible():
  """isCompatible() -> bool"""
  return _sourcetraildb.isCompatible()

def getLoadedDatabaseVersion():
  """getLoadedDatabaseVersion() -> int"""
  return _sourcetraildb.getLoadedDatabaseVersion()

def beginTransaction():
  """beginTransaction() -> bool"""
  return _sourcetraildb.beginTransaction()

def commitTransaction():
  """commitTransaction() -> bool"""
  return _sourcetraildb.commitTransaction()

def rollbackTransaction():
  """rollbackTransaction() -> bool"""
  return _sourcetraildb.rollbackTransaction()

def optimizeDatabaseMemory():
  """optimizeDatabaseMemory() -> bool"""
  return _sourcetraildb.optimizeDatabaseMemory()

def recordSymbol(*args):
  """recordSymbol(std::string serializedNameHierarchy) -> int"""
  return _sourcetraildb.recordSymbol(*args)

def recordSymbolDefinitionKind(*args):
  """recordSymbolDefinitionKind(int symbolId, DefinitionKind symbolDefinitionKind) -> bool"""
  return _sourcetraildb.recordSymbolDefinitionKind(*args)

def recordSymbolKind(*args):
  """recordSymbolKind(int symbolId, SymbolKind symbolKind) -> bool"""
  return _sourcetraildb.recordSymbolKind(*args)

def recordSymbolLocation(*args):
  """recordSymbolLocation(int symbolId, int fileId, int startLine, int startColumn, int endLine, int endColumn) -> bool"""
  return _sourcetraildb.recordSymbolLocation(*args)

def recordSymbolScopeLocation(*args):
  """recordSymbolScopeLocation(int symbolId, int fileId, int startLine, int startColumn, int endLine, int endColumn) -> bool"""
  return _sourcetraildb.recordSymbolScopeLocation(*args)

def recordSymbolSignatureLocation(*args):
  """recordSymbolSignatureLocation(int symbolId, int fileId, int startLine, int startColumn, int endLine, int endColumn) -> bool"""
  return _sourcetraildb.recordSymbolSignatureLocation(*args)

def recordReference(*args):
  """recordReference(int contextSymbolId, int referencedSymbolId, ReferenceKind referenceKind) -> int"""
  return _sourcetraildb.recordReference(*args)

def recordReferenceLocation(*args):
  """recordReferenceLocation(int referenceId, int fileId, int startLine, int startColumn, int endLine, int endColumn) -> bool"""
  return _sourcetraildb.recordReferenceLocation(*args)

def recordReferenceIsAmbiguous(*args):
  """recordReferenceIsAmbiguous(int referenceId) -> bool"""
  return _sourcetraildb.recordReferenceIsAmbiguous(*args)

def recordReferenceToUnsolvedSymhol(*args):
  """
    recordReferenceToUnsolvedSymhol(int contextSymbolId, ReferenceKind referenceKind, int fileId, int startLine, int startColumn, 
        int endLine, int endColumn) -> int
    """
  return _sourcetraildb.recordReferenceToUnsolvedSymhol(*args)

def recordQualifierLocation(*args):
  """
    recordQualifierLocation(int referencedSymbolId, int fileId, int startLine, int startColumn, int endLine, 
        int endColumn) -> bool
    """
  return _sourcetraildb.recordQualifierLocation(*args)

def recordFile(*args):
  """recordFile(std::string filePath) -> int"""
  return _sourcetraildb.recordFile(*args)

def recordFileLanguage(*args):
  """recordFileLanguage(int fileId, std::string languageIdentifier) -> bool"""
  return _sourcetraildb.recordFileLanguage(*args)

def recordLocalSymbol(*args):
  """recordLocalSymbol(std::string name) -> int"""
  return _sourcetraildb.recordLocalSymbol(*args)

def recordLocalSymbolLocation(*args):
  """recordLocalSymbolLocation(int localSymbolId, int fileId, int startLine, int startColumn, int endLine, int endColumn) -> bool"""
  return _sourcetraildb.recordLocalSymbolLocation(*args)

def recordAtomicSourceRange(*args):
  """recordAtomicSourceRange(int fileId, int startLine, int startColumn, int endLine, int endColumn) -> bool"""
  return _sourcetraildb.recordAtomicSourceRange(*args)

def recordError(*args):
  """
    recordError(std::string message, bool fatal, int fileId, int startLine, int startColumn, int endLine, 
        int endColumn) -> bool
    """
  return _sourcetraildb.recordError(*args)
# This file is compatible with both classic and new-style classes.

