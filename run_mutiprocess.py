import subprocess
import concurrent.futures
import os
import time
from ast_search.ast_manage import AstManager
from graph_database_index.graphDB import clear_task, update_file_path

class TimerDecorator:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        start_time = time.time()
        result = self.func(*args, **kwargs)
        end_time = time.time()
        print(f"Function '{self.func.__name__}' executed in {end_time - start_time:.4f} seconds")
        return result

def get_py_files(directory):
    py_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files


def run_script_in_env(env_path, script_path, working_directory, script_args=None):
    # 构建虚拟环境的Python解释器路径
    python_executable = os.path.join(env_path, 'bin', 'python')

    # 检查虚拟环境的Python解释器是否存在
    if not os.path.exists(python_executable):
        raise FileNotFoundError("Python executable not found in the environment: {}".format(python_executable))

    # 构建命令
    command = [python_executable, script_path]

    # 添加脚本参数
    if script_args:
        command.extend(script_args)

    try:
        result = subprocess.run(command, cwd=working_directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = result.stdout.decode('utf-8')
        stderr = result.stderr.decode('utf-8')

        # 输出执行结果
        if result.returncode == 0:
            return "Script executed successfully:\n{}".format(stdout)
        else:
            return "Script execution failed:\n{}".format(stderr)
    except subprocess.CalledProcessError as e:
        return "Error: {}".format(e.stderr)


def run_single(path, root, task_id, shallow):
    # 定义虚拟环境和脚本路径
    env_path = '/root/miniconda3/envs/srctrl'
    script_path = '/home/lanbo/code_database/graph_database_index/run_index_single.py'
    working_directory = '/home/lanbo/code_database'

    if shallow:
        script_args = ['--file_path', path, '--root_path', root, '--task_id', task_id, '--shallow']
    else:
        script_args = ['--file_path', path, '--root_path', root, '--task_id', task_id]
    return run_script_in_env(env_path, script_path, working_directory, script_args)

@TimerDecorator
def main(path_list, root, task_id, shallow, max_workers=6):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_single, path, root, task_id, shallow): path for path in path_list}
        for future in concurrent.futures.as_completed(futures):
            path = futures[future]
            try:
                result = future.result()
                print("Output =========================== {}:\n{}".format(path, result))
            except Exception as e:
                print("Error ============================ processing {}: {}".format(path, e))


def run(repo_path=None, task_id='test', max_workers=8):

    root_path = ''
    # task_id = 'test_sh'

    if repo_path:
        file_list = get_py_files(repo_path)
        root_path = repo_path
    else:
        file_list = [
            # r"/home/lanbo/repo/sklearn/metrics/cluster/__init__.py",
            r"/home/lanbo/repo/test_repo/folder1/file1.py",
            # r"/home/lanbo/repo/test_repo/folder1/file2.py",
            # r"/home/lanbo/repo/test_repo/folder2/file3.py",
            # r"/home/lanbo/cceval_pipeline/cceval/data/crosscodeeval_rawdata/turboderp-exllama-a544085/generator.py"
            # r"/home/lanbo/repo/test_repo/main.py"
            # r"/home/lanbo/cceval_pipeline/cceval/data/crosscodeeval_rawdata/turboderp-exllama-a544085/example_alt_generator.py"
        ]

    main(file_list, root_path, task_id, shallow=True, max_workers=max_workers)

@TimerDecorator
def run_update_file_path(task_id, repo_path):
    update_file_path(task_id, repo_path)

if __name__ == "__main__":
    # repo_path = r'/home/lanbo/repo/test_repo'
    # repo_path = r'/home/lanbo/cceval_pipeline/cceval/data/crosscodeeval_rawdata/turboderp-exllama-a544085'
    repo_path = r'/home/lanbo/cceval_pipeline/cceval/data/crosscodeeval_rawdata/open-mmlab-Multimodal-GPT-9c73e47'
    task_id = 'test_0621'
    # clear_task(task_id)

    # 1. run shallow index
    # run(repo_path, task_id, max_workers=8)

    # 2. run AST
    ast_manage = AstManager(repo_path, task_id)
    ast_manage.run()
    print(ast_manage.class_inherited)


