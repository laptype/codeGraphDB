import os.path
import git
from graph_database_index.graphDB import GraphDatabaseHandler
from run_mutiprocess import main as multiprocess_graph_index
from ast_search.ast_manage import AstManager

"""
repo version 1 --> repo version 2
1. 保留不变的文件：
    input: [change list] in repo version 1
        遍历Node: {label: [version 1]}
            除了[change list] 里面的文件:
                Node add 添加{label: [version 2]}
        # 如果有第三方库，也会保留
2. 添加改动文件的节点：
    input: [change list] in repo version 2
        遍历 [change list] file:
            正常解析file
"""

def add_new_label_in_old_node(task_id_old, task_id_new, change_list: list):
    graphDB = GraphDatabaseHandler(uri="http://localhost:7474",
                                    user="neo4j",
                                    password="12345678",
                                    database_name='neo4j',
                                    task_id=task_id_old,
                                    use_lock=True)

    query = f"MATCH (m:`{task_id_old}`) RETURN m"
    nodes = graphDB.execute_query(query)

    for node in nodes:
        node_id = node['m'].identity
        node_properties = dict(node['m'])
        node_path = node_properties.get('file_path', None)  # 获取file_path属性，如果不存在则为None
        if node_path and node_path not in change_list:
            query_add = f"""
MATCH (n)
WHERE id(n) = {node_id}
SET n:`{task_id_new}`
"""
            graphDB.execute_query(query_add)

    print(f"Added label `{task_id_new}` to {len(nodes)} nodes.")


def get_change_list(repo_path, commit1, commit2):
    repo = git.Repo(repo_path)

    # Fetch the diffs between the two commits
    diff = repo.git.diff(commit1, commit2, name_only=True)

    # Split the diff output into a list of file paths
    change_list = diff.split('\n')

    return change_list

def update_version(task_id_old, task_id_new, change_list: list, root_path):
    add_new_label_in_old_node(task_id_old, task_id_new, change_list)

    # 1. 改为绝对路径 -----------------------------------------
    change_files = []
    for file in change_list:
        new_file_path = os.path.join(root_path, file)
        if os.path.exists(new_file_path):
            change_files.append(new_file_path)
    # 2. indexing change file ------------------------------
    multiprocess_graph_index(change_files, root_path, task_id_new, shallow=True, max_workers=2)

    # 3. ast manager ---------------------------------------
    ast_manage = AstManager(repo_path, task_id_new)
    ast_manage.run()
    print(ast_manage.class_inherited)



if __name__ == '__main__':
    """
    1. 获取 change list
    """
    repo_path = '/home/liuxiangyan/scikit-learn'  # 替换为你的Git仓库路径
    commit1 = '30cf4a0e8e999303591737d3be120ba36bfb3d84'
    commit2 = '9337a1a2bdd9968bb665f076ffb1df19018c1f8f'

    change_list = get_change_list(repo_path, commit1, commit2)
    print(change_list)

    """
    2. index new version
    """
    # 假设这个change_list
    change_list = [
        'main.py',
        'main2.py',
        'folder1/folder11/file.py'
    ]
    repo_path = r'/home/lanbo/repo/test_repo2/'
    task_id_old = 'test_0621'
    task_id_new = 'test_0621_2'
    update_version(task_id_old, task_id_new, change_list, root_path=repo_path)