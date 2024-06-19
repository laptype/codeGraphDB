import sourcetraildb as srctrl
import ast
from graph_database.graphDB import GraphDatabaseHandler
from graph_database import test
from graph_database.index_utils import SourcetrailScript
class AstVisitorClient:

    def __init__(self, graphDB: GraphDatabaseHandler):
        self.indexedFileId = 0
        if srctrl.isCompatible():
            print('INFO: Loaded database is compatible.')
        else:
            print('WARNING: Loaded database is not compatible.')
            print('INFO: Supported DB Version: ' + str(srctrl.getSupportedDatabaseVersion()))
            print('INFO: Loaded DB Version: ' + str(srctrl.getLoadedDatabaseVersion()))

        self.graphDB = graphDB
        self.this_module = ''
        self.this_file_path = ''
        self.this_script = None
        self.this_source_code_lines = []
        # self.graphDB.clear_database()
        self.symbol_data = {}
        self.symbol_data['builtins'] = {
            "name": "builtins",
            "kind": 'MODULE',
            "parent_name": '',
        }
        self.symbolId_to_Name = {}
        self.indexedFileId_to_path = {}
        self.referenceId_to_data = {}
        self.referenceId_to_data['Unsolved'] = []

    def extract_signature(self, code):
        pass
        # parsed_code = ast.parse(code)
        # function_def = parsed_code.body[0]
        # a = 0

    def extract_code_between_lines(self, start_line, end_line, is_indent=False):
        extracted_lines = self.this_source_code_lines[start_line-1:end_line]

        # 去除指定数量的缩进
        if is_indent:
            extracted_lines = self.this_source_code_lines[start_line-1:end_line-1]
            first_line_indent = len(extracted_lines[0]) - len(extracted_lines[0].lstrip())

            extracted_lines = [line[first_line_indent:] if len(line) > first_line_indent else '' for line in extracted_lines]

        extracted_code = '\n'.join(extracted_lines)
        return extracted_code

    def get_module_name(self, symbol):
        if symbol not in self.symbol_data.keys():
            return ''
        if self.symbol_data[symbol]['kind'] == 'MODULE':
            return symbol
        return self.get_module_name(self.symbol_data[symbol]['parent_name'])

    def get_parent_class(self, symbol):
        parent_name = self.symbol_data[symbol]['parent_name']
        if parent_name in self.symbol_data.keys():
            parent_type = self.symbol_data[parent_name]['kind']
            if parent_type == 'CLASS':
                return parent_name
        return ''

    def recordSymbol(self, nameHierarchy):

        if nameHierarchy is not None:
            symbolId = srctrl.recordSymbol(nameHierarchy.serialize())
            # TODO: edge: CONTAINS
            name = nameHierarchy.getDisplayString()
            parent_name = nameHierarchy.getParentDisplayString()
            self.symbolId_to_Name[symbolId] = name
            if name not in self.symbol_data.keys():
                self.symbol_data[name] = {
                    "name": name,
                    "kind": '',
                    "parent_name": parent_name,
                }
            return symbolId
        return 0

    def recordSymbolDefinitionKind(self, symbolId, symbolDefinitionKind):
        # TODO: check Definition kind
        # definition 的类型
        name = self.symbolId_to_Name[symbolId]
        kind = test.symbolDefinitionKindToString(symbolDefinitionKind)
        # self.symbol_to_Type[name] = kind
        srctrl.recordSymbolDefinitionKind(symbolId, symbolDefinitionKind)

    def recordSymbolKind(self, symbolId, symbolKind):
        full_name = self.symbolId_to_Name[symbolId]
        kind = test.symbolKindToString(symbolKind)
        self.symbol_data[full_name]['kind'] = kind
        # create node
        if kind == 'MODULE':
            if full_name == self.this_module:
                self.graphDB.add_node(label='MODULE', full_name=full_name, parms={
                    "name": full_name,
                    "file_path": self.this_file_path,
                })
            else:
                self.graphDB.add_node(label='MODULE', full_name=full_name, parms={
                    "name": full_name
                })
        elif kind in ['CLASS', 'FUNCTION', 'METHOD', 'GLOBAL_VARIABLE', 'FIELD']:
            data = {
                "name": full_name.split('.')[-1]
            }
            if self.symbol_data[full_name]['parent_name'] == self.this_module:
                data['file_path'] = self.this_file_path

            if kind in ['FUNCTION', 'METHOD', 'GLOBAL_VARIABLE', 'FIELD']:
                parent_class = self.get_parent_class(full_name)
                if parent_class:
                    data["class"] = parent_class
                    if self.symbol_data[parent_class]['parent_name'] == self.this_module:
                        data['file_path'] = self.this_file_path
                    if kind == 'FUNCTION':
                        kind = 'METHOD'
                        self.symbol_data[full_name]['kind'] = kind
            # 创建节点 ------------------------------------------------------------------
            self.graphDB.add_node(label=kind, full_name=full_name, parms=data)
            # 边的关系 ------------------------------------------------------------------
            if kind in ['CLASS', 'FUNCTION', 'GLOBAL_VARIABLE']:
                module_name = self.get_module_name(full_name)
                self.graphDB.add_edge(start_label='MODULE', start_name=module_name,
                                      relationship_type='CONTAINS',
                                      end_label=kind, end_name=full_name, params={"association_type": kind})
                self.graphDB.add_edge(start_label='MODULE', start_name=self.this_module,
                                      relationship_type='CONTAINS',
                                      end_label=kind, end_name=full_name, params={"association_type": kind})
            if kind == 'METHOD':
                parent_class = self.get_parent_class(full_name)
                self.graphDB.add_edge(start_label='CLASS', start_name=parent_class,
                                      relationship_type='HAS_METHOD',
                                      end_label=kind, end_name=full_name)
            if kind == 'FIELD':
                parent_class = self.get_parent_class(full_name)
                self.graphDB.add_edge(start_label='CLASS', start_name=parent_class,
                                      relationship_type='HAS_FIELD',
                                      end_label=kind, end_name=full_name)

        srctrl.recordSymbolKind(symbolId, symbolKind)

    def recordSymbolLocation(self, symbolId, sourceRange):
        """
		这个是Symbol【定义的时候】所处的行号
		"""
        name = self.symbolId_to_Name[symbolId]
        kind = self.symbol_data[name]['kind']

        if kind in ['CLASS', 'FUNCTION', 'METHOD']:
            code = self.extract_code_between_lines(sourceRange.startLine, sourceRange.endLine)
            self.graphDB.add_node(kind, full_name=name, parms={
                'signature': code.strip()
            })

        srctrl.recordSymbolLocation(
            symbolId,
            self.indexedFileId,
            sourceRange.startLine,
            sourceRange.startColumn,
            sourceRange.endLine,
            sourceRange.endColumn
        )

    def recordSymbolScopeLocation(self, symbolId, sourceRange):
        """
		这个是Symbol的作用域范围 [start_line, end_line)
		"""
        name = self.symbolId_to_Name[symbolId]
        kind = self.symbol_data[name]['kind']
        file_path = self.indexedFileId_to_path[self.indexedFileId]

        if kind in ['FUNCTION', 'METHOD']:
            code = self.extract_code_between_lines(sourceRange.startLine, sourceRange.endLine, is_indent=True)
            self.graphDB.add_node(kind, full_name=name, parms={
                'code': code
            })
            self.extract_signature(code)
            data = {
                "name": name,
                "file_path": file_path,
                "startLine": sourceRange.startLine,
                "endLine": sourceRange.endLine,
            }
        srctrl.recordSymbolScopeLocation(
            symbolId,
            self.indexedFileId,
            sourceRange.startLine,
            sourceRange.startColumn,
            sourceRange.endLine,
            sourceRange.endColumn
        )

    def recordSymbolSignatureLocation(self, symbolId, sourceRange):
        """
			这个没有用到
		"""
        name = self.symbolId_to_Name[symbolId]
        file_path = self.indexedFileId_to_path[self.indexedFileId]
        data = {
            "name": name,
            "file_path": file_path,
            "startLine": sourceRange.startLine,
            "endLine": sourceRange.endLine,
        }
        srctrl.recordSymbolSignatureLocation(
            symbolId,
            self.indexedFileId,
            sourceRange.startLine,
            sourceRange.startColumn,
            sourceRange.endLine,
            sourceRange.endColumn
        )

    def recordReference(self, contextSymbolId, referencedSymbolId, referenceKind):
        """
		这个就是调用关系 contextName -> referenceName
		referenceKindStr: CALL, TYPE_USAGE, INHERITANCE, OVERRIDE, ...
		"""
        referenceKindStr = test.referenceKindToString(referenceKind)
        referenceName = self.symbolId_to_Name[referencedSymbolId]
        contextName = self.symbolId_to_Name[contextSymbolId]

        if referenceKindStr == 'IMPORT':
            contextKind = self.symbol_data[contextName]['kind']
            referenceNameKind = self.symbol_data[referenceName]['kind']
            # self.graphDB.add_edge(start_label="MODULE", start_name=contextName,
            #                          relationship_type='CONTAINS',
            #                          end_label=referenceNameKind, end_name=referenceName,
            #                          params={"association_type": referenceNameKind})

        if referenceKindStr == 'CALL':
            contextKind = self.symbol_data[contextName]['kind']
            referenceNameKind = self.symbol_data[referenceName]['kind']
            if contextKind != 'MODULE':
                self.graphDB.add_edge(start_label=contextKind, start_name=contextName,
                                      relationship_type='CALL',
                                      end_label=referenceNameKind, end_name=referenceName)

        if referenceKindStr in ['USAGE']:
            contextKind = self.symbol_data[contextName]['kind']
            referenceNameKind = self.symbol_data[referenceName]['kind']
            if contextKind in ['FUNCTION', 'METHOD'] and referenceNameKind in ['GLOBAL_VARIABLE', 'FIELD']:
                self.graphDB.add_edge(start_label=contextKind, start_name=contextName,
                                      relationship_type='USES',
                                      end_label=referenceNameKind, end_name=referenceName)
        if referenceKindStr == 'INHERITANCE':
            contextKind = self.symbol_data[contextName]['kind']
            referenceNameKind = self.symbol_data[referenceName]['kind']
            self.graphDB.add_edge(start_label=contextKind, start_name=contextName,
                                  relationship_type='INHERITS',
                                  end_label=referenceNameKind, end_name=referenceName)

        referenceId = srctrl.recordReference(contextSymbolId,
                                             referencedSymbolId,
                                             referenceKind)

        self.referenceId_to_data[referenceId] = {
            "contextName": contextName,
            "referenceName": referenceName,
            "referenceKindStr": referenceKindStr
        }
        return referenceId

    def recordReferenceLocation(self, referenceId, sourceRange):
        """
		记录reference的位置
		"""
        referenceData = self.referenceId_to_data[referenceId]
        file_path = self.indexedFileId_to_path[self.indexedFileId]
        data = {
            "data": referenceData,
            "file_path": file_path,
            "startLine": sourceRange.startLine,
            "endLine": sourceRange.endLine,
        }
        self.referenceId_to_data[referenceId]['location'] = {
            "file_path": file_path,
            "startLine": sourceRange.startLine,
            "endLine": sourceRange.endLine,
        }
        srctrl.recordReferenceLocation(
            referenceId,
            self.indexedFileId,
            sourceRange.startLine,
            sourceRange.startColumn,
            sourceRange.endLine,
            sourceRange.endColumn
        )

    def recordReferenceIsAmbiguous(self, referenceId):
        """
		未使用
		"""
        return srctrl.recordReferenceIsAmbiguous(referenceId)

    def recordReferenceToUnsolvedSymhol(self, contextSymbolId, referenceKind, sourceRange):
        """
		记录无法跟踪的情况
		"""
        contextName = self.symbolId_to_Name[contextSymbolId]
        referenceKindStr = test.referenceKindToString(referenceKind)
        file_path = self.indexedFileId_to_path[self.indexedFileId]
        self.referenceId_to_data['Unsolved'].append({
            "contextName": contextName,
            "referenceKindStr": referenceKindStr,
            "location": {
                "file_path": file_path,
                "startLine": sourceRange.startLine,
                "endLine": sourceRange.endLine,
            }
        })

        return srctrl.recordReferenceToUnsolvedSymhol(
            contextSymbolId,
            referenceKind,
            self.indexedFileId,
            sourceRange.startLine,
            sourceRange.startColumn,
            sourceRange.endLine,
            sourceRange.endColumn
        )

    def recordQualifierLocation(self, referencedSymbolId, sourceRange):
        """
        TODO: 暂时当作和recordReferenceLocation一样的
        """
        return srctrl.recordQualifierLocation(
            referencedSymbolId,
            self.indexedFileId,
            sourceRange.startLine,
            sourceRange.startColumn,
            sourceRange.endLine,
            sourceRange.endColumn
        )

    def recordFile(self, filePath):
        self.indexedFileId = srctrl.recordFile(filePath.replace('\\', '/'))
        self.indexedFileId_to_path[self.indexedFileId] = filePath.replace('\\', '/')
        self.this_file_path = self.indexedFileId_to_path[self.indexedFileId]
        srctrl.recordFileLanguage(self.indexedFileId, 'python')
        return self.indexedFileId

    def recordFileLanguage(self, fileId, languageIdentifier):
        srctrl.recordFileLanguage(fileId, languageIdentifier)

    def recordLocalSymbol(self, name):
        return srctrl.recordLocalSymbol(name)

    def recordLocalSymbolLocation(self, localSymbolId, sourceRange):
        srctrl.recordLocalSymbolLocation(
            localSymbolId,
            self.indexedFileId,
            sourceRange.startLine,
            sourceRange.startColumn,
            sourceRange.endLine,
            sourceRange.endColumn
        )

    def recordAtomicSourceRange(self, sourceRange):
        srctrl.recordAtomicSourceRange(
            self.indexedFileId,
            sourceRange.startLine,
            sourceRange.startColumn,
            sourceRange.endLine,
            sourceRange.endColumn
        )

    def recordError(self, message, fatal, sourceRange):
        srctrl.recordError(
            message,
            fatal,
            self.indexedFileId,
            sourceRange.startLine,
            sourceRange.startColumn,
            sourceRange.endLine,
            sourceRange.endColumn
        )
