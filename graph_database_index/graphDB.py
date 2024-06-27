import os

from py2neo import Graph, Node, NodeMatcher, Relationship, RelationshipMatcher
import fasteners
import subprocess
import codecs
import re
import json

class NoOpLock:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class FileLock:
    # 读写锁
    def __init__(self, lockfile):
        self.lockfile = lockfile
        self.lock = fasteners.InterProcessLock(self.lockfile)
        self.lock_acquired = False

    def __enter__(self):
        self.lock_acquired = self.lock.acquire(blocking=True)
        if not self.lock_acquired:
            raise RuntimeError("Unable to acquire the lock")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock_acquired:
            self.lock.release()
            self.lock_acquired = False


class GraphDatabaseHandler:
    def __init__(self, uri, user, password, database_name='neo4j', task_id='', use_lock=False, lockfile='neo4j.lock'):
        self.graph = self._connect_to_graph(uri, user, password, database_name)
        self.node_matcher = NodeMatcher(self.graph)
        self.rel_matcher = RelationshipMatcher(self.graph)
        self.none_label = 'none'
        self.task_id = task_id
        self.lock = FileLock(lockfile) if use_lock else NoOpLock()

    def _connect_to_graph(self, uri, user, password, database_name):
        try:
            return Graph(uri, auth=(user, password), name=database_name)
        except Exception as e:
            self._start_neo4j()
            try:
                return Graph(uri, auth=(user, password), name=database_name)
            except Exception as e:
                raise ConnectionError(
                    "Failed to connect to Neo4j at {} after attempting to start the service.".format(uri)) from e

    def _start_neo4j(self):
        # 使用系统命令启动Neo4j
        # 这里假设Neo4j的启动脚本或命令是 "neo4j start"
        # 根据你的系统和安装配置，这可能会有所不同
        try:
            subprocess.check_call(["neo4j", "start"], shell=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError("Failed to start Neo4j service.") from e

    def _match_node(self, full_name):
        if self.task_id:
            existing_node = self.node_matcher.match(self.task_id, full_name=full_name).first()
        else:
            existing_node = self.node_matcher.match(full_name=full_name).first()
        return existing_node

    def _create_node(self, label=None, full_name='', parms={}):
        if label is None or label == '':
            label = self.none_label
        if self.task_id:
            node = Node(self.task_id, label, full_name=full_name, **parms)
        else:
            node = Node(label, full_name=full_name, **parms)
        self.graph.create(node)
        return node

    def _update_node_label(self, full_name, label):
        existing_node = self._match_node(full_name)
        if existing_node:
            query = (
                "MATCH (n:{0} {{full_name: $full_name}}) "
                "REMOVE n:{0} "
                "SET n:{1}"
            ).format(self.none_label, label)
            self.graph.run(query, full_name=full_name)
            return True
        return False

    def clear_task_data(self, task_id):
        """
        Delete all nodes with the specified label.
        """
        query = "MATCH (n:`{label}`) DETACH DELETE n".format(label=task_id)
        with self.lock:
            self.graph.run(query)

    def clear_database(self):
        with self.lock:
            self.graph.run("MATCH (n) DETACH DELETE n")

    def execute_query(self, query):
        with self.lock:
            result = self.graph.run(query)
            return [record for record in result]

    def update_node(self, full_name, parms={}):
        with self.lock:
            existing_node = self._match_node(full_name)
            if existing_node:
                existing_node.update(parms)
                self.graph.push(existing_node)

    def add_node(self, label, full_name, parms={}):
        with self.lock:
            existing_node = self._match_node(full_name)
            if existing_node:
                if self.none_label in list(existing_node.labels):
                    self._update_node_label(full_name, label)
                existing_node.update(parms)
                self.graph.push(existing_node)
            else:
                existing_node = self._create_node(label, full_name, parms=parms)
            return existing_node

    def add_edge(self, start_label=None, start_name='', relationship_type='', end_label=None, end_name='', params={}):
        with self.lock:
            start_node = self._match_node(full_name=start_name)
            end_node = self._match_node(full_name=end_name)

            if not start_node:
                start_node = self._create_node(start_label, full_name=start_name, parms=params)
            if not end_node:
                end_node = self._create_node(end_label, full_name=end_name, parms=params)

            if start_node and end_node:
                rel = self.rel_matcher.match((start_node, end_node), relationship_type).first()
                if rel:
                    rel.update(params)
                    self.graph.push(rel)
                    return rel
                else:
                    rel = Relationship(start_node, relationship_type, end_node, **params)
                    self.graph.create(rel)
                    return rel
            return None

    def update_file_path(self, root_path):
        with self.lock:
            # 获取所有包含 file_path 属性的节点
            query = (
                "MATCH (n:`{0}`) "
                "WHERE exists(n.file_path)"
                "RETURN n.file_path as file_path, n.full_name as full_name"
            ).format(self.task_id)

            nodes_with_file_path = self.execute_query(query)
            # 遍历每个节点并更新 file_path
            for node in nodes_with_file_path:
                full_name = node['full_name']
                file_path = node['file_path']
                # old_path = node['file_path']
                if file_path.startswith(root_path):
                    file_path = file_path[len(root_path):]
                    self.update_node(full_name=full_name, parms={
                        "file_path": file_path
                    })

class GraphDatabaseHandlerNone():
    def __init__(self, *args, **params):
        pass

    def add_node(self, label, full_name, parms={}):
        pass

    def add_edge(self, start_label=None, start_name='', relationship_type='', end_label=None, end_name='', params={}):
        pass


def clear_task(task_id):
    graphDB = GraphDatabaseHandler(uri="http://localhost:7474",
                                   user="neo4j",
                                   password="12345678",
                                   database_name='neo4j',
                                   task_id=task_id,
                                   use_lock=True)
    graphDB.clear_task_data(task_id)


def update_file_path(task_id, root_path):
    graphDB = GraphDatabaseHandler(uri="http://localhost:7474",
                                   user="neo4j",
                                   password="12345678",
                                   database_name='neo4j',
                                   task_id=task_id,
                                   use_lock=True)

    graphDB.update_file_path(root_path)


def extract_code_from_file(file_path, start_line, end_line, is_indent=True):
    if start_line < 1:
        start_line = 1
    try:
        with codecs.open(file_path, 'r', encoding='utf-8') as input:
            sourceCode = input.read()
        source_code_lines = sourceCode.split('\n')
        extracted_lines = source_code_lines[start_line - 1:end_line]
    except:
        return ''
    # 去除指定数量的缩进
    if is_indent:
        first_line_indent = len(extracted_lines[0]) - len(extracted_lines[0].lstrip())

        extracted_lines = [line[first_line_indent:] if len(line) > first_line_indent else '' for line in
                           extracted_lines]

    extracted_code = '\n'.join(extracted_lines)
    return extracted_code

def process_string(input_string, repo_path, folded_len=10, is_indent=False):
    # 定义正则表达式，匹配 <CODE></CODE> 之间的内容
    pattern = re.compile(r'<CODE>(.*?)</CODE>')
    matches = pattern.findall(input_string)

    for match in matches:

        code_dict = json.loads(match)
        file_path = os.path.join(repo_path, code_dict["F"])
        start_line = int(code_dict["S"])
        end_line = int(code_dict["E"])

        code_snippet = extract_code_from_file(file_path, start_line, end_line, is_indent=is_indent)

        if len(matches) > 1 and len(code_snippet) > folded_len:
            # 只显示前10个非空格字符
            trimmed_snippet = code_snippet
            folded_snippet = "{0}...(code folded)".format(trimmed_snippet.strip()[:folded_len])
            input_string = input_string.replace('<CODE>{}</CODE>'.format(match), folded_snippet)
        else:
            input_string = input_string.replace('<CODE>{}</CODE>'.format(match), code_snippet)


    return input_string

if __name__ == '__main__':
    # task_label = "project_cc_python/102"
    repo_path = r'/home/lanbo/repo/test_repo'
    task_label = 'sklearn'
    graph_db = GraphDatabaseHandler(uri="http://localhost:7474",
                                    user="neo4j",
                                    password="12345678",
                                    database_name='neo4j',
                                    task_id=task_label,
                                    use_lock=True)
    user_query = """
    MATCH (c:`sklearn`:CLASS {name: 'Person'})
    RETURN c
    """
    response = graph_db.execute_query(user_query)
    for record in response:
        print(str(record))
        print((process_string(str(record), repo_path)))
        print()

    # user_query = """
    # MATCH (c:CLASS {name: "ExLlamaTokenizer"})-[:HAS_METHOD]->(m:METHOD)
    # RETURN m.name AS MethodName, m.signature AS MethodSignature, m.code AS MethodCode
    # """
    # user_query = """
    # MATCH (c:project_cc_python/102:CLASS)
    # RETURN c
    # """
    # # response = graph_db.get_cypher_response(user_query)
    # # print(response)
    # # graph_db.clear_task_data("project_cc_python/138")
    # response = graph_db.execute_query(user_query)
    # print(response)
#     module_name = 'folder1.file2'
#     target_name = 'add_numbers'
#     query = f"""
# MATCH (m:MODULE {{full_name: '{module_name}'}})-[:CONTAINS]->(c {{name: '{target_name}'}})
# RETURN c.full_name as full_name, labels(c) AS labels
#     """
#     response = graph_db.execute_query(query)
#     # 提取full_name
#     full_name, labels = response[0]['full_name'], response[0]['labels']
#     label = next(l for l in labels if l != task_label)
#     print(full_name, label)
# 打印结果
