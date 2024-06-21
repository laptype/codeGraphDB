import os
import sys
import argparse
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 动态添加工作目录到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from graph_database import myClient
from graph_database import indexer
from graph_database import shallow_indexer
from graph_database.graphDB import GraphDatabaseHandler
import sourcetraildb as srctrl

def indexSourceFile(sourceFilePath, environmentPath, workingDirectory, graph_db: GraphDatabaseHandler, rootPath):
    # graph_db = GraphDatabaseHandler(uri="http://localhost:7474",
    #                                 user="neo4j",
    #                                 password="12345678",
    #                                 database_name='neo4j',
    #                                 task_id='test2')

    astVisitorClient = myClient.AstVisitorClient(graph_db)
    # astVisitorClient = indexer_sh.AstVisitorClient()

    indexer.indexSourceFile(sourceFilePath, environmentPath, workingDirectory, astVisitorClient, False, rootPath)
    # shallow_indexer.indexSourceFile(sourceFilePath, environmentPath, workingDirectory, astVisitorClient, False, rootPath)

def run_single(graph_db: GraphDatabaseHandler, sourceFilePath='', root_path='',srctrl_clear=False):
    workingDirectory = os.getcwd()
    unique_id = uuid.uuid4()
    print(sourceFilePath)
    databaseFilePath = os.path.join(workingDirectory, 'tmp_{}.srctrldb'.format(unique_id))
    databaseFile1PrjPath = os.path.join(workingDirectory, 'tmp_{}.srctrlprj'.format(unique_id))

    if srctrl_clear:
        if not srctrl.clear():
            print('ERROR: ' + srctrl.getLastError() + sourceFilePath)

    if not srctrl.open(databaseFilePath):
        print('ERROR: ' + srctrl.getLastError() + sourceFilePath)

    srctrl.beginTransaction()
    indexSourceFile(sourceFilePath, None, workingDirectory, graph_db, root_path)
    srctrl.commitTransaction()

    if not srctrl.close():
        print('ERROR: ' + srctrl.getLastError() + sourceFilePath)

    if os.path.exists(databaseFilePath):
        os.remove(databaseFilePath)
        os.remove(databaseFile1PrjPath)

def run():
    task_id = 'test_0621'
    file_path = r'/home/lanbo/repo/test_repo/main.py'
    root_path = r'/home/lanbo/repo/test_repo'

    # task_id = 'test_sh'
    parser = argparse.ArgumentParser(description='Python source code indexer that generates a Sourcetrail compatible database.')
    parser.add_argument('--file_path', help='path to the source file to index', default=file_path, type=str, required=False)
    parser.add_argument('--root_path', default=root_path, required=False)
    parser.add_argument('--task_id', help='task_id', type=str, default=task_id ,required=False)
    args = parser.parse_args()

    task_id = args.task_id
    file_path = args.file_path
    root_path = args.root_path

    graph_db = GraphDatabaseHandler(uri="http://localhost:7474",
                                    user="neo4j",
                                    password="12345678",
                                    database_name='neo4j',
                                    task_id=task_id,
                                    use_lock=True)
    graph_db.clear_task_data(task_id)
    run_single(graph_db, file_path, root_path)


if __name__ == '__main__':
    run()