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

def get_py_files(directory):
    py_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files

def indexSourceFile(sourceFilePath, environmentPath, workingDirectory, graph_db: GraphDatabaseHandler):
    # graph_db = GraphDatabaseHandler(uri="http://localhost:7474",
    #                                 user="neo4j",
    #                                 password="12345678",
    #                                 database_name='neo4j',
    #                                 task_id='test2')
    astVisitorClient = myClient.AstVisitorClient(graph_db)
    indexer.indexSourceFile(sourceFilePath, environmentPath, workingDirectory, astVisitorClient, False)
    # shallow_indexer.indexSourceFile(sourceFilePath, environmentPath, workingDirectory, astVisitorClient, False)


def run_single(graph_db: GraphDatabaseHandler, sourceFilePath='', srctrl_clear=False):
    workingDirectory = os.getcwd()
    unique_id = uuid.uuid4()
    databaseFilePath = os.path.join(workingDirectory, 'tmp_{}.srctrldb'.format(unique_id))

    if srctrl_clear:
        if not srctrl.clear():
            print('ERROR: ' + srctrl.getLastError())

    if not srctrl.open(databaseFilePath):
        print('ERROR: ' + srctrl.getLastError())

    srctrl.beginTransaction()
    indexSourceFile(sourceFilePath, None, workingDirectory, graph_db)
    srctrl.commitTransaction()

    if not srctrl.close():
        print('ERROR: ' + srctrl.getLastError())

    if os.path.exists(databaseFilePath):
        os.remove(databaseFilePath)

def run():
    repo_path = r'/home/lanbo/cceval_pipeline/cceval/data/crosscodeeval_rawdata/turboderp-exllama-a544085'
    task_id = 'project_cc_python/138_nost'

    # repo_path = ''
    # task_id = 'test01'
    parser = argparse.ArgumentParser(description='Python source code indexer that generates a Sourcetrail compatible database.')
    parser.add_argument('--repo_path', help='path to the source file to index', default=repo_path, type=str, required=False)
    parser.add_argument('--task_id', help='task_id', type=str, default=task_id ,required=False)
    args = parser.parse_args()
    if args.repo_path:
        file_list = get_py_files(args.repo_path)
    else:
        file_list = [
            r"/home/lanbo/repo/sklearn/metrics/cluster/__init__.py"
        ]
    task_id = args.task_id
    graph_db = GraphDatabaseHandler(uri="http://localhost:7474",
                                    user="neo4j",
                                    password="12345678",
                                    database_name='neo4j',
                                    task_id=task_id,
                                    use_lock=True)
    # 记录开始时间
    start_time = time.time()
    # 使用 ThreadPoolExecutor 并行运行 run_single
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_file = {executor.submit(run_single, graph_db, file_path): file_path for file_path in file_list}
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                future.result()
                print('Successfully processed {}'.format(file_path))
            except Exception as exc:
                print('{} generated an exception: {}'.format(file_path, exc))

    # 记录结束时间
    end_time = time.time()
    # 计算执行时间
    elapsed_time = end_time - start_time
    print("Time taken:", int(elapsed_time), "seconds")

if __name__ == '__main__':
    run()