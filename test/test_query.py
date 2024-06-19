from graph_database.graphDB import GraphDatabaseHandler

if __name__ == "__main__":
    db = GraphDatabaseHandler(
        uri = 'http://localhost:7474',
        user = 'neo4j',
        password = '12345678',
        database_name='neo4j'
    )

    results = db.execute_query("MATCH (n) RETURN n LIMIT 5")

    # 打印结果
    for result in results:
        print(result)