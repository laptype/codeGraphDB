from py2neo import Graph, Node, NodeMatcher, Relationship, RelationshipMatcher
import fasteners
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
        self.graph = Graph(uri, auth=(user, password), name=database_name)
        self.node_matcher = NodeMatcher(self.graph)
        self.rel_matcher = RelationshipMatcher(self.graph)
        self.none_label = 'none'
        self.task_id = task_id
        self.lock = FileLock(lockfile) if use_lock else NoOpLock()

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

    def get_cypher_response(self, query):
        with self.lock:
            # Define the task label based on task_id
            task_label = self.task_id

            # Construct the APOC script
            apoc_script = """
            CALL apoc.cypher.run(
                "MATCH (n) WHERE n:`{task_label}`
                 WITH collect(n) AS nodes
                 CALL apoc.create.subgraph({{nodes: nodes}}) YIELD graph
                 RETURN graph",
                {{}}
            ) YIELD value
            WITH value.graph AS taskGraph
            CALL apoc.cypher.run(
                "UNWIND $taskGraph.nodes AS n
                 UNWIND $taskGraph.rels AS r
                 {query}",
                {{taskGraph: taskGraph}}
            ) YIELD value
            RETURN value
            """.format(task_label=task_label, query=query)

            # Execute the APOC script
            result = self.graph.run(apoc_script).data()
            return result

def clear_task(task_id):
    graphDB = GraphDatabaseHandler(uri="http://localhost:7474",
                                        user="neo4j",
                                        password="12345678",
                                        database_name='neo4j',
                                        task_id=task_id,
                                        use_lock=True)
    graphDB.clear_task_data(task_id)

if __name__ == '__main__':

    # task_label = "project_cc_python/102"
    task_label = 'test_0621'
    graph_db = GraphDatabaseHandler(uri="http://localhost:7474",
                                    user="neo4j",
                                    password="12345678",
                                    database_name='neo4j',
                                    task_id=task_label,
                                    use_lock=True)

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