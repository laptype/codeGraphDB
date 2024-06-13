from py2neo import Graph, Node, NodeMatcher, Relationship, RelationshipMatcher

class GraphDatabaseHandler:
    def __init__(self, uri, user, password, database_name='neo4j'):
        self.graph = Graph(uri, auth=(user, password), name=database_name)
        self.node_matcher = NodeMatcher(self.graph)
        self.rel_matcher = RelationshipMatcher(self.graph)

    def create_node_if_not_exists(self, label, **properties):
        existing_node = self.node_matcher.match(label, **properties).first()
        if not existing_node:
            node = Node(label, **properties)
            self.graph.create(node)
            return node
        return existing_node

    def create_relationship_if_not_exists(self, start_node, rel_type, end_node, **properties):
        existing_rel = self.rel_matcher.match((start_node, end_node), rel_type, **properties).first()
        if not existing_rel:
            rel = Relationship(start_node, rel_type, end_node, **properties)
            self.graph.create(rel)
            return rel
        return existing_rel
    
    def update_node(self, name, label=None, new_properties: dict={}):
        existing_node = self.node_matcher.match(name=name).first()
        if existing_node:
            existing_node.update(new_properties)
            self.graph.push(existing_node)
        else:
            assert label is not None, "label is none"
            existing_node = Node(label, name=name, **new_properties)
            self.graph.create(existing_node)
        return existing_node

    def update_edge(self, start_name, relationship_type, end_name, new_properties: dict = {}):
        start_node = self.node_matcher.match(name=start_name).first()
        end_node = self.node_matcher.match(name=end_name).first()
        if start_node and end_node:
            rel = self.rel_matcher.match((start_node, end_node), relationship_type).first()
            if rel:
                rel.update(new_properties)
                self.graph.push(rel)
                return rel
            else:
                rel = Relationship(start_node, relationship_type, end_node, **new_properties)
                self.graph.create(rel)
                return rel
        return None

    def get_edge(self, start_name, relationship_type, end_name):
        start_node = self.node_matcher.match(name=start_name).first()
        end_node = self.node_matcher.match(name=end_name).first()
        if start_node and end_node:
            rel = self.rel_matcher.match((start_node, end_node), relationship_type).first()
            if rel:
                return dict(rel)
        return None
   
    def clear_database(self):
        self.graph.run("MATCH (n) DETACH DELETE n")

if __name__ == "__main__":
    db = GraphDatabaseHandler(
        uri = 'http://localhost:7474', 
        user = 'neo4j', 
        password = '12345678', 
        database_name='neo4j'
    )
    db.update_node('test function 1', label='FUNCTION', new_properties={'context': 'helloworld test function 1'})
    db.update_node('test function 1', label='FUNCTION', new_properties={'context2': 'helloworld2 test function 1'})
    db.update_node('test function 2', label='FUNCTION', new_properties={'context': 'helloworld test function 2'})
    db.update_edge('test function 1', 'CALL', 'test function 2', new_properties={'context': 'helloworld edge'})
