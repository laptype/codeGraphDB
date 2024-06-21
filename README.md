# codeGraphDB
代码-图数据库











module/class/function: 路径：

```
indexer_visitor.py: 
def beginVisitName这个函数
```

```
for definition in self.getDefinitionsOfNode(node, self.sourceFilePath):
# 这个definition里面就包含有路径信息
definition.module_path
```



外部库相关的：

```
getNameHierarchyOfClassOrFunctionDefinition
```

