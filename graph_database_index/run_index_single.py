import os
import sys
import argparse
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 动态添加工作目录到 sys.path
# current_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(current_dir)
# sys.path.insert(0, parent_dir)

from graph_database_index import myClient
from graph_database_index import indexer
from graph_database_index import shallow_indexer
from graph_database_index.graphDB import GraphDatabaseHandler
# from graph_database_index.graphDB import GraphDatabaseHandlerNone as GraphDatabaseHandler
import graph_database_index.sourcetraildb as srctrl

def indexSourceFile(sourceFilePath, environmentPath, workingDirectory, graph_db: GraphDatabaseHandler, rootPath, shallow):
    # graph_db = GraphDatabaseHandler(uri="http://localhost:7474",
    #                                 user="neo4j",
    #                                 password="12345678",
    #                                 database_name='neo4j',
    #                                 task_id='test2')

    astVisitorClient = myClient.AstVisitorClient(graph_db, task_root_path=rootPath)
    # astVisitorClient = indexer_sh.AstVisitorClient()

    print('use shallow: '+ str(shallow))

    if not shallow:
        indexer.indexSourceFile(sourceFilePath, environmentPath, workingDirectory, astVisitorClient, False, rootPath)
    else:
        shallow_indexer.indexSourceFile(sourceFilePath, environmentPath, workingDirectory, astVisitorClient, False, rootPath)

def run_single(graph_db: GraphDatabaseHandler, sourceFilePath='', root_path='', srctrl_clear=False, shallow=True):
    workingDirectory = os.getcwd()
    unique_id = uuid.uuid4()
    print(sourceFilePath)

    tmp_save_folder = os.path.join(workingDirectory, 'tmp')
    if not os.path.exists(tmp_save_folder):
        os.makedirs(tmp_save_folder)

    databaseFilePath = os.path.join(tmp_save_folder, 'tmp_{}.srctrldb'.format(unique_id))
    databaseFile1PrjPath = os.path.join(tmp_save_folder, 'tmp_{}.srctrlprj'.format(unique_id))

    if srctrl_clear:
        if not srctrl.clear():
            print('ERROR: ' + srctrl.getLastError() + sourceFilePath)

    if not srctrl.open(databaseFilePath):
        print('ERROR: ' + srctrl.getLastError() + sourceFilePath)

    srctrl.beginTransaction()
    indexSourceFile(sourceFilePath, None, workingDirectory, graph_db, root_path, shallow)
    srctrl.commitTransaction()

    if not srctrl.close():
        print('ERROR: ' + srctrl.getLastError() + sourceFilePath)

    if os.path.exists(databaseFilePath):
        os.remove(databaseFilePath)
        os.remove(databaseFile1PrjPath)

def run():
    # task_id = 'test_sh'
    parser = argparse.ArgumentParser(description='Python source code indexer that generates a Sourcetrail compatible database.')
    parser.add_argument('--file_path', help='path to the source file to index', default='', type=str, required=False)
    parser.add_argument('--root_path', default='', required=False)
    parser.add_argument('--task_id', help='task_id', type=str, default='' ,required=False)
    parser.add_argument('--shallow', help='shallow', action='store_true', required=False)
    parser.add_argument('--clear', help='clear', action='store_true', required=False)
    args = parser.parse_args()

    if args.file_path == '':
        task_id = 'test_0621'
        file_path = r'/home/lanbo/repo/test_repo/main.py'
        root_path = r'/home/lanbo/repo/test_repo/'

        # file_path = r'/home/lanbo/cceval_pipeline/cceval/data/crosscodeeval_rawdata/turboderp-exllama-a544085/model.py'
        # root_path = r'/home/lanbo/cceval_pipeline/cceval/data/crosscodeeval_rawdata/turboderp-exllama-a544085/'
        is_shallow = True
        is_clear = True
    else:
        task_id = args.task_id
        file_path = args.file_path
        root_path = args.root_path
        is_shallow = args.shallow
        is_clear = args.clear

    graph_db = GraphDatabaseHandler(uri="http://localhost:7474",
                                    user="neo4j",
                                    password="12345678",
                                    database_name='neo4j',
                                    task_id=task_id,
                                    use_lock=True)
    if is_clear:
        graph_db.clear_task_data(task_id)

    run_single(graph_db, file_path, root_path, shallow=is_shallow)
    print('Success build graph')


if __name__ == '__main__':
    run()