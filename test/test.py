from graph_database.graphDB import GraphDatabaseHandler

if __name__ == "__main__":
    db = GraphDatabaseHandler(
        uri = 'http://localhost:7474', 
        user = 'neo4j', 
        password = '12345678', 
        database_name='neo4j'
    )
    # db.clear_database()
    db.update_node('test function 1', label='FUNCTION', new_properties={'context': 'helloworld test function 1'})
    db.update_node('test function 1', label='FUNCTION', new_properties={'context2': 'helloworld2 test function 1'})
    db.update_node('test function 2', label='FUNCTION', new_properties={'context': 'helloworld test function 2'})
    db.update_edge('test function 1', 'CALL', 'test function 2', new_properties={'context': 'helloworld edge'})
