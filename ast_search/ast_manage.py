import os
import ast
import pathlib
from ast_search.ast_utils import get_py_files, get_dotted_name, get_module_name, module_name_to_path, TimerDecorator, method_decorator
from graph_database_index.graphDB import GraphDatabaseHandler


class AstManager:
    def __init__(self, project_path: str, task_id: str):
        self.project_path = project_path
        self.root_path = project_path
        self.graphDB = GraphDatabaseHandler(uri="http://localhost:7474",
                                             user="neo4j",
                                             password="12345678",
                                             database_name='neo4j',
                                             task_id=task_id,
                                             use_lock=True)
        self.task_id = task_id
        # self._build_index()
        self.class_inherited = {}
        self.processed_relations = set()  # 用于记录已经处理过的关系
        self.visited = []

    def get_full_name_from_graph(self, module_full_name, target_name):
        query = f"""
MATCH (m:MODULE:`{self.task_id}` {{full_name: '{module_full_name}'}})-[:CONTAINS]->(c {{name: '{target_name}'}})
RETURN c.full_name as full_name, labels(c) AS labels
"""
        response = self.graphDB.execute_query(query)
        if response:
            full_name, labels = response[0]['full_name'], response[0]['labels']
            label = next(l for l in labels if l != self.task_id)
            return full_name, label
        else:
            return None, None

    def get_all_method_of_class(self, class_full_name):
        query = f"""
MATCH (c:CLASS:`{self.task_id}` {{full_name: '{class_full_name}'}})-[:HAS_METHOD]->(m)
RETURN m.full_name as full_name
"""
        response = self.graphDB.execute_query(query)
        if response:
            methods = [record['full_name'] for record in response]
            return methods
        else:
            return None

    @method_decorator
    def run(self):
        py_files = get_py_files(self.project_path)

        for py_file in py_files:
            self.build_modules_contain(py_file)

        for py_file in py_files:
            self.build_inherited(py_file)

        for cur_class_full_name in self.class_inherited.keys():
            for base_class_full_name in self.class_inherited[cur_class_full_name]:
                self._build_inherited_method(cur_class_full_name, base_class_full_name)

    def _build_inherited_method(self, cur_class_full_name, base_class_full_name):
        # 创建一个关系的唯一标识符
        relation_key = (cur_class_full_name, base_class_full_name)
        # 如果这个关系已经处理过，直接返回
        if relation_key in self.processed_relations:
            return
        # 将当前关系标记为已处理
        self.processed_relations.add(relation_key)

        methods = self.get_all_method_of_class(base_class_full_name)
        if methods is None:
            return
        for method in methods:
            if '__init__' in method:
                continue
            edge = self.graphDB.add_edge(start_label='CLASS', start_name=cur_class_full_name,
                                         relationship_type='HAS_METHOD', end_name=method)

        if base_class_full_name in self.class_inherited.keys():
            for base_base_class_full_name in self.class_inherited[base_class_full_name]:
                self._build_inherited_method(cur_class_full_name, base_base_class_full_name)

    def build_modules_contain(self, file_full_path):
        if file_full_path in self.visited:
            return None
        self.visited.append(file_full_path)

        try:
            file_content = pathlib.Path(file_full_path).read_text()
            tree = ast.parse(file_content)
        except Exception:
            # failed to read/parse one file, we should ignore it
            return None

        if '__init__.py' in file_full_path:
            cur_module_full_name = get_dotted_name(self.root_path, os.path.dirname(file_full_path))
        else:
            cur_module_full_name = get_dotted_name(self.root_path, file_full_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                target_module_full_name = get_module_name(file_full_path, node, self.root_path)
                if not target_module_full_name:
                    continue
                for target in node.names:
                    target_name = target.name
                    target_full_name, target_label = self.get_full_name_from_graph(target_module_full_name, target_name)
                    if target_full_name:
                        # print(cur_module_full_name, '->', target_full_name, target_name)
                        edge = self.graphDB.add_edge(start_label='MODULE', start_name=cur_module_full_name,
                                              relationship_type='CONTAINS', end_name=target_full_name, params={"association_type": target_label})
                    else:
                        # continue
                        module_path = module_name_to_path(target_module_full_name, self.root_path)
                        file_path = os.path.join(self.root_path, module_path, '__init__.py')
                        if os.path.exists(file_path):
                            self.build_modules_contain(file_path)
                            target_full_name, target_label = self.get_full_name_from_graph(target_module_full_name, target_name)
                            if target_full_name:
                                # print(cur_module_full_name, '->', target_full_name, target_name)
                                edge = self.graphDB.add_edge(start_label='MODULE', start_name=cur_module_full_name,
                                                             relationship_type='CONTAINS', end_name=target_full_name,
                                                             params={"association_type": target_label})

    def build_inherited(self, file_full_path):
        try:
            file_content = pathlib.Path(file_full_path).read_text()
            tree = ast.parse(file_content)
        except Exception:
            # failed to read/parse one file, we should ignore it
            return None

        if '__init__.py' in file_full_path:
            cur_module_full_name = get_dotted_name(self.root_path, os.path.dirname(file_full_path))
        else:
            cur_module_full_name = get_dotted_name(self.root_path, file_full_path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            class_name = node.name
            cur_class_full_name = cur_module_full_name + '.' + class_name
            for base in node.bases:
                if not isinstance(base, ast.Name):
                    continue
                base_class_full_name, _ = self.get_full_name_from_graph(cur_module_full_name, base.id)
                if base_class_full_name is None:
                    print('base_class_full_name is None: ', cur_class_full_name, base.id)
                if cur_class_full_name not in self.class_inherited.keys():
                    self.class_inherited[cur_class_full_name] = []
                self.class_inherited[cur_class_full_name].append(base_class_full_name)
                if base_class_full_name:
                    edge = self.graphDB.add_edge(start_name=cur_class_full_name,
                                                 relationship_type='INHERITS', end_name=base_class_full_name)
                # self._build_inherited_method(cur_class_full_name, base_class_full_name)




if __name__ == '__main__':
    repo_path = r'/home/lanbo/repo/test_repo'
    task_id = 'test_0621'
    ast_manage = AstManager(repo_path, task_id)
