from ast import Tuple
from curses.ascii import isupper
from re import T
import networkx as nx
from collections import defaultdict, namedtuple
from collections.abc import MutableMapping

from ast_search.search import search_utils
from ast_search.search.search_utils import SearchResult
from ast_search.log import log_and_print

LineRange = namedtuple("LineRange", ["start", "end"])

ClassInheritedType = MutableMapping[str, list[tuple[str, list[str]]]]
ClassIndexType = MutableMapping[str, list[tuple[str, LineRange]]]
ClassFuncIndexType = MutableMapping[
    str, MutableMapping[str, list[tuple[str, LineRange]]]
]
FuncIndexType = MutableMapping[str, list[tuple[str, LineRange]]]

RESULT_SHOW_LIMIT = 3


class SearchManager:
    def __init__(self, project_path: str):
        self.project_path = project_path
        # list of all files ending with .py, which are likely not test files
        # These are all ABSOLUTE paths.
        self.parsed_files: list[str] = []

        # for file name in the indexes, assume they are absolute path
        # class name -> [(file_name, line_range)]
        self.class_index: ClassIndexType = {}

        self.class_inherited: ClassInheritedType = {}

        # {class_name -> {func_name -> [(file_name, line_range)]}}
        # inner dict is a list, since we can have (1) overloading func names,
        # and (2) multiple classes with the same name, having the same method
        self.class_func_index: ClassFuncIndexType = {}

        # function name -> [(file_name, line_range)]
        self.function_index: FuncIndexType = {}
        self._build_index()
        self.new_class_inherited = self.class_inherited
        # log_and_print(self.class_inherited)
        # raise

    def _build_index(self):
        """
        With all source code of the project, build two indexes:
            1. From class name to (source file, start line, end line)
            2. From function name to (source file, start line, end line)
        Since there can be two classes/functions with the same name, the mapping
        value is a list of tuples.
        This is for fast lookup whenever we receive a query.
        """
        self._update_indices(*self._build_python_index())

    def _update_indices(
        self,
        class_index: ClassIndexType,
        class_func_index: ClassFuncIndexType,
        function_index: FuncIndexType,
        parsed_files: list[str],
        class_inherited: ClassInheritedType,
    ) -> None:
        self.class_index.update(class_index)
        self.class_func_index.update(class_func_index)
        self.function_index.update(function_index)
        self.parsed_files.extend(parsed_files)
        self.class_inherited.update(class_inherited)

    def _build_python_index(
        self,
    ) -> tuple[
        ClassIndexType, ClassFuncIndexType, FuncIndexType, list[str], ClassInheritedType
    ]:
        class_inherited: ClassInheritedType = defaultdict(list)
        class_index: ClassIndexType = defaultdict(list)
        class_func_index: ClassFuncIndexType = defaultdict(lambda: defaultdict(list))
        function_index: FuncIndexType = defaultdict(list)

        py_files = search_utils.find_python_files(self.project_path)
        # holds the parsable subset of all py files
        parsed_py_files = []
        for py_file in py_files:
            file_info = search_utils.parse_python_file(py_file)
            if file_info is None:
                # parsing of this file failed
                continue
            parsed_py_files.append(py_file)
            # extract from file info, and form search index
            classes, class_to_funcs, top_level_funcs = file_info

            # (1) build class index
            for c, start, end, base_classes in classes:
                class_index[c].append((py_file, LineRange(start, end)))
                class_inherited[c].append((py_file, base_classes))

            # (2) build class-function index
            for c, class_funcs in class_to_funcs.items():
                for f, start, end in class_funcs:
                    class_func_index[c][f].append((py_file, LineRange(start, end)))

            # (3) build (top-level) function index
            for f, start, end in top_level_funcs:
                function_index[f].append((py_file, LineRange(start, end)))

        return (
            class_index,
            class_func_index,
            function_index,
            parsed_py_files,
            class_inherited,
        )

    def file_line_to_class_and_func(
        self, file_path: str, line_no: int
    ) -> tuple[str | None, str | None]:
        """
        Given a file path and a line number, return the class and function name.
        If the line is not inside a class or function, return None.
        """
        # check whether this line is inside a class
        for class_name in self.class_func_index:
            func_dict = self.class_func_index[class_name]
            for func_name, func_info in func_dict.items():
                for file_name, (start, end) in func_info:
                    if file_name == file_path and start <= line_no <= end:
                        return class_name, func_name

        # not in any class; check whether this line is inside a top-level function
        for func_name in self.function_index:
            for file_name, (start, end) in self.function_index[func_name]:
                if file_name == file_path and start <= line_no <= end:
                    return None, func_name

        # this file-line is not recorded in any of the indexes
        return None, None

    def _tmp_search_func_in_class(
        self, function_name: str, class_name: str
    ) -> list[SearchResult]:
        """
        Search for the function name in the class.
        Args:
            function_name (str): Name of the function.
            class_name (str): Name of the class.
        Returns:
            The list of code snippets searched.
        """
        result: list[SearchResult] = []
        if class_name not in self.class_func_index:
            return result
        if function_name not in self.class_func_index[class_name]:
            return result
        for fname, (start, end) in self.class_func_index[class_name][function_name]:
            func_code = search_utils.get_code_snippets(fname, start, end)
            res = SearchResult(fname, class_name, function_name, func_code)
            result.append(res)
        return result

    def dfs_inheritance_path(self, class_name: str, path=None, visited=None) -> list:
        if path is None:
            path = []
        if visited is None:
            visited = set()
            
        if class_name in visited:
            return path
        visited.add(class_name)
        
        path.append(class_name)
        if class_name not in self.class_inherited:
            return path
        inherited_res = self.class_inherited[class_name]
        bases = []
        for tmp_res in inherited_res:
            if len(tmp_res[1]) > 0:
                bases.append(tmp_res[1][0])
        bases.sort()
        for base_class in bases:
            self.dfs_inheritance_path(base_class, path, visited)
        return path

    def _search_func_in_class(
        self, function_name: str, class_name: str
    ) -> list[SearchResult]:
        """
        Search for the function name in the class.
        Args:
            function_name (str): Name of the function.
            class_name (str): Name of the class.
        Returns:
            The list of code snippets searched.
        """
        result: list[SearchResult] = []
        if class_name not in self.class_func_index:
            return result
        inherited_class_list = self.dfs_inheritance_path(class_name)
        for tmp_class in inherited_class_list:
            if tmp_class not in self.class_func_index or function_name not in self.class_func_index[tmp_class]:
                continue
            else:
                class_name = tmp_class
                break
        for fname, (start, end) in self.class_func_index[class_name][function_name]:
            func_code = search_utils.get_code_snippets(fname, start, end)
            res = SearchResult(fname, class_name, function_name, func_code)
            result.append(res)
        return result

    def _search_func_in_all_classes(self, function_name: str) -> list[SearchResult]:
        """
        Search for the function name in all classes.
        Args:
            function_name (str): Name of the function.
        Returns:
            The list of code snippets searched.
        """
        result: list[SearchResult] = []
        for class_name in self.class_index:
            res = self._search_func_in_class(function_name, class_name)
            result.extend(res)
        return result

    def _search_top_level_func(self, function_name: str) -> list[SearchResult]:
        """
        Search for top-level function name in the entire project.
        Args:
            function_name (str): Name of the function.
        Returns:
            The list of code snippets searched.
        """
        result: list[SearchResult] = []
        if function_name not in self.function_index:
            return result

        for fname, (start, end) in self.function_index[function_name]:
            func_code = search_utils.get_code_snippets(fname, start, end)
            res = SearchResult(fname, None, function_name, func_code)
            result.append(res)
        return result

    def _search_func_in_code_base(self, function_name: str) -> list[SearchResult]:
        """
        Search for this function, from both top-level and all class definitions.
        """
        result: list[SearchResult] = []  # list of (file_name, func_code)
        # (1) search in top level
        top_level_res = self._search_top_level_func(function_name)
        class_res = self._search_func_in_all_classes(function_name)
        result.extend(top_level_res)
        result.extend(class_res)
        return result

    ###############################
    ### Interfaces ################
    ###############################

    # not search API - for writing patch
    # if we are searching for only a class when writing patch, likely we do not have enough info
    # the result can be too long, so we just show the first two
    def get_class_full_snippet(self, class_name: str) -> tuple[str, str, bool]:
        summary = f"Class {class_name} did not appear in the codebase."
        tool_result = f"Could not find class {class_name} in the codebase."

        if class_name not in self.class_index:
            return tool_result, summary, False
        # class name -> [(file_name, start_line, end_line)]
        search_res: list[SearchResult] = []
        for fname, (start, end) in self.class_index[class_name]:
            code = search_utils.get_code_snippets(fname, start, end)
            res = SearchResult(fname, class_name, None, code)
            search_res.append(res)

        if not search_res:
            return tool_result, summary, False

        # the good path
        # for all the searched result, append them and form the final result
        tool_result = f"Found {len(search_res)} classes with name {class_name} in the codebase:\n\n"
        summary = tool_result
        if len(search_res) > 2:
            tool_result += "Too many results, showing full code for 2 of them:\n"
        for idx, res in enumerate(search_res[:2]):
            res_str = res.to_tagged_str(self.project_path)
            tool_result += f"- Search result {idx + 1}:\n```\n{res_str}\n```"
        return tool_result, summary, True

    def match_functions_in_call_graph(
        self, anchor_node, call_graph_nodes, threshold=70
    ):
        from fuzzywuzzy import fuzz
        similar_nodes = []
        similarities = []
        for node in call_graph_nodes:
            ratio = fuzz.ratio(anchor_node, node)
            similarities.append((node, ratio))

        similarities.sort(key=lambda x: x[1], reverse=True)
        top_similarities = similarities[:5]

        for node, similarity in top_similarities:
            if similarity >= threshold:
                similar_nodes.append(node)

        return similar_nodes

    def is_class_name(self, name: str):
        return name[0].isupper() or (name[1].isupper() and name[0] == "_")
    
    def search_code_by_dotted_name(
        self, dotted_name: str, G: nx.Graph, depth: int
    ) -> tuple[str, str | None, list[str] | str, list[str] | None, bool]:
        dotted_name_split = dotted_name.split(".")
        name_count = len(dotted_name_split)

        if name_count <= 1:
            return "unvalid input arguments", "unvalid input arguments", None, None, False

        last_name = dotted_name_split[-1]
        second_last_name = dotted_name_split[-2]

        if self.is_class_name(last_name):
            ## (1) a.b.c.D => a/b/c.py + D + null
            file_path = "/".join(dotted_name_split[:-1]) + ".py"
            class_name = last_name
            search_res, _, bool_res = self.search_class_in_file(class_name, file_path)
            if not bool_res:
                tmp_search_res, _, tmp_bool_res = self.search_class(class_name)
                if tmp_bool_res:
                    search_res = search_res + "\n" + tmp_search_res
                    bool_res = tmp_bool_res

        elif self.is_class_name(second_last_name):
            ## (2) a.b.C.d => a/b.py + C + d
            method_name, class_name = last_name, second_last_name
            search_res, _, bool_res = self.search_method_in_class(method_name, class_name)
            if not bool_res:
                file_path = "/".join(dotted_name_split[:-2]) + ".py"
                if method_name != "__init__":
                    tmp_search_res, _, tmp_bool_res = self.search_method_in_file(method_name, file_path)
                    if tmp_bool_res:
                        search_res, bool_res = tmp_search_res, tmp_bool_res
                else:
                    tmp_search_res, _, tmp_bool_res = self.search_class_in_file(class_name, file_path)
                    if tmp_bool_res:
                        search_res, bool_res = tmp_search_res, tmp_bool_res
        else:
            ## (3) a.b.c.d => a/b/c.py + null + d
            file_path = "/".join(dotted_name_split[:-1]) + ".py"
            method_name = last_name
            search_res, _, bool_res = self.search_method_in_file(method_name, file_path)
            if not bool_res:
                new_file_path = file_path[:-3] + "/__init__.py"
                tmp_search_res, _, tmp_bool_res = self.search_method_in_file(method_name, new_file_path)
                if tmp_bool_res:
                    search_res, bool_res = tmp_search_res, tmp_bool_res
                else:
                    new_file_path = "/".join(dotted_name_split[:-2]) + ".py"
                    tmp_search_res, _, tmp_bool_res = self.search_method_in_file(method_name, file_path)
                    if tmp_bool_res:
                        search_res, bool_res = tmp_search_res, tmp_bool_res

        if bool_res:
            _, edges, _, _ = self.search_child_nodes_in_call_graph(dotted_name, G, depth)
            if edges:
                return search_res, "", edges, None, True
            else:
                return search_res, "", None, None, True
        else:
            similar_nodes = self.match_functions_in_call_graph(dotted_name, list(G.nodes()))
            return search_res, "", None, similar_nodes, False

    def search_child_nodes_in_call_graph(
        self, anchor_node: str, G: nx.Graph, depth: int
    ) -> tuple[list[str], list[str], list[str] | None, bool]:
        child_nodes = []  # ["node 1", "node 2", ...]
        edges = []  # ["anchor_node -> node 1", "anchor_node -> node 2", ...]
        visited = set()

        def dfs(node, current_depth):
            if current_depth > depth:
                return

            visited.add(node)
            child_nodes.append(node)

            if current_depth < depth:
                for neighbor in G.neighbors(node):
                    if neighbor not in visited:
                        edges.append(f"{node} -> {neighbor}")
                        dfs(neighbor, current_depth + 1)

        try:
            dfs(anchor_node, 0)
            child_nodes.remove(anchor_node)
            return child_nodes, edges, None, True
        except:
            similar_nodes = self.match_functions_in_call_graph(anchor_node, list(G.nodes()))
            child_nodes.remove(anchor_node)
            return child_nodes, edges, similar_nodes, False

    def search_class(self, class_name: str) -> tuple[str, str, bool]:
        # initialize them to error case
        summary = f"Class {class_name} did not appear in the codebase."
        tool_result = f"Could not find class {class_name} in the codebase."

        if class_name not in self.class_index:
            return tool_result, summary, False

        search_res: list[SearchResult] = []
        for fname, _ in self.class_index[class_name]:
            # there are some classes; we return their signatures
            code = search_utils.get_class_signature(fname, class_name)
            res = SearchResult(fname, class_name, None, code)
            search_res.append(res)

        if not search_res:
            # this should not happen, but just in case
            return tool_result, summary, False

        # the good path
        # for all the searched result, append them and form the final result
        tool_result = f"Found {len(search_res)} classes with name {class_name} in the codebase:\n\n"
        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_result += "They appeared in the following files:\n"
            tool_result += SearchResult.collapse_to_file_level(
                search_res, self.project_path
            )
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_result += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        summary = f"The tool returned information about class `{class_name}`."
        return tool_result, summary, True

    def search_class_in_file(self, class_name, file_name: str) -> tuple[str, str, bool]:
        # (1) check whether we can get the file
        candidate_py_abs_paths = [f for f in self.parsed_files if f.endswith(file_name)]
        if not candidate_py_abs_paths:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # (2) search for this class in the entire code base (we do filtering later)
        if class_name not in self.class_index:
            tool_output = f"Could not find class {class_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # (3) class is there, check whether it exists in the file specified.
        search_res: list[SearchResult] = []
        for fname, (start_line, end_line) in self.class_index[class_name]:
            if fname in candidate_py_abs_paths:
                class_code = search_utils.get_code_snippets(fname, start_line, end_line)
                res = SearchResult(fname, class_name, None, class_code)
                search_res.append(res)

        if not search_res:
            tool_output = f"Could not find class {class_name} in file {file_name}."
            summary = tool_output
            return tool_output, summary, False

        # good path; we have result, now just form a response
        tool_output = f"Found {len(search_res)} classes with name {class_name} in file {file_name}:\n\n"
        summary = tool_output
        for idx, res in enumerate(search_res):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def search_method_in_object(self, method_name: str, class_name: str):
        """
        Check if a method is defined in the built-in 'object' class.
        """
        if method_name in dir(object):
            return f"Method '{method_name}' is not explicitly defined in class '{class_name}', it is inherited from the built-in 'object' class."
        else:
            return None

    def search_method_in_file(
        self, method_name: str, file_name: str
    ) -> tuple[str, str, bool]:
        # (1) check whether we can get the file
        # supports both when file_name is relative to project root, and when
        # it is just a short name
        candidate_py_abs_paths = [f for f in self.parsed_files if f.endswith(file_name)]
        # print(candidate_py_files)
        if not candidate_py_abs_paths:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # (2) search for this method in the entire code base (we do filtering later)
        search_res: list[SearchResult] = self._search_func_in_code_base(method_name)
        if not search_res:
            tool_output = f"The method {method_name} does not appear in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # (3) filter the search result => they need to be in one of the files!
        filtered_res: list[SearchResult] = [
            res for res in search_res if res.file_path in candidate_py_abs_paths
        ]

        new_filtered_res: list[SearchResult] = []
        for single_res in filtered_res:
            s_class_name = single_res.class_name
            s_code = single_res.code
            s_file_path = single_res.file_path
            flag = False
            for item in new_filtered_res:
                if (
                    item.code == s_code
                    and item.class_name == s_class_name
                    and item.file_path == s_file_path
                ):
                    flag = True
            if not flag:
                new_filtered_res.append(single_res)

        # (4) done with search, now prepare result
        if not new_filtered_res:
            tool_output = (
                f"There is no method with name `{method_name}` in file {file_name}."
            )
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(new_filtered_res)} methods with name `{method_name}` in file {file_name}:\n\n"
        summary = tool_output

        # when searching for a method in one file, it's rare that there are
        # many candidates, so we do not trim the result
        for idx, res in enumerate(new_filtered_res):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def search_method_in_class(
        self, method_name: str, class_name: str
    ) -> tuple[str, str, bool]:
        if class_name not in self.class_index:
            tool_output = f"Could not find class {class_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # has this class, check its methods
        search_res: list[SearchResult] = self._search_func_in_class(
            method_name, class_name
        )
        if not search_res:
            tool_output = f"Could not find method {method_name} in class {class_name}."
            search_res_in_object = self.search_method_in_object(method_name, class_name)
            if search_res_in_object:
                tool_output = search_res_in_object
            summary = tool_output
            return tool_output, summary, False

        # found some methods, prepare the result
        tool_output = f"Found {len(search_res)} methods with name {method_name} in class {class_name}:\n\n"
        summary = tool_output

        # There can be multiple classes defined in multiple files, which contain the same method
        # still trim the result, just in case
        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += f"Too many results, showing full code for {RESULT_SHOW_LIMIT} of them, and the rest just file names:\n"
        first_five = search_res[:RESULT_SHOW_LIMIT]
        for idx, res in enumerate(first_five):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        # for the rest, collect the file names into a set
        if rest := search_res[RESULT_SHOW_LIMIT:]:
            tool_output += "Other results are in these files:\n"
            tool_output += SearchResult.collapse_to_file_level(rest, self.project_path)
        return tool_output, summary, True

    def search_method(self, method_name: str) -> tuple[str, str, bool]:
        """
        Search for a method in the entire codebase.
        """
        search_res: list[SearchResult] = self._search_func_in_code_base(method_name)
        if not search_res:
            tool_output = f"Could not find method {method_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(search_res)} methods with name {method_name} in the codebase:\n\n"
        summary = tool_output

        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following files:\n"
            tool_output += SearchResult.collapse_to_file_level(
                search_res, self.project_path
            )
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"

        return tool_output, summary, True

    def search_code(self, code_str: str) -> tuple[str, str, bool]:
        # attempt to search for this code string in all py files
        all_search_results: list[SearchResult] = []
        for file_path in self.parsed_files:
            searched_line_and_code: list[tuple[int, str]] = (
                search_utils.get_code_region_containing_code(file_path, code_str)
            )
            if not searched_line_and_code:
                continue
            for searched in searched_line_and_code:
                line_no, code_region = searched
                # from line_no, check which function and class we are in
                class_name, func_name = self.file_line_to_class_and_func(
                    file_path, line_no
                )
                res = SearchResult(file_path, class_name, func_name, code_region)
                all_search_results.append(res)

        if not all_search_results:
            tool_output = f"Could not find code {code_str} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # good path
        tool_output = f"Found {len(all_search_results)} snippets containing `{code_str}` in the codebase:\n\n"
        summary = tool_output

        if len(all_search_results) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following files:\n"
            tool_output += SearchResult.collapse_to_file_level(
                all_search_results, self.project_path
            )
        else:
            for idx, res in enumerate(all_search_results):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def search_code_in_file(
        self, code_str: str, file_name: str
    ) -> tuple[str, str, bool]:
        code_str = code_str.removesuffix(")")

        candidate_py_files = [f for f in self.parsed_files if f.endswith(file_name)]
        if not candidate_py_files:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # start searching for code in the filtered files
        all_search_results: list[SearchResult] = []
        for file_path in candidate_py_files:
            searched_line_and_code: list[tuple[int, str]] = (
                search_utils.get_code_region_containing_code(file_path, code_str)
            )
            if not searched_line_and_code:
                continue
            for searched in searched_line_and_code:
                line_no, code_region = searched
                # from line_no, check which function and class we are in
                class_name, func_name = self.file_line_to_class_and_func(
                    file_path, line_no
                )
                res = SearchResult(file_path, class_name, func_name, code_region)
                all_search_results.append(res)

        if not all_search_results:
            tool_output = f"Could not find code {code_str} in file {file_name}."
            summary = tool_output
            return tool_output, summary, False

        # good path
        # There can be a lot of results, from multiple files.
        tool_output = f"Found {len(all_search_results)} snippets with code {code_str} in file {file_name}:\n\n"
        summary = tool_output
        if len(all_search_results) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following methods:\n"
            tool_output += SearchResult.collapse_to_method_level(
                all_search_results, self.project_path
            )
        else:
            for idx, res in enumerate(all_search_results):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def retrieve_code_snippet(
        self, file_path: str, start_line: int, end_line: int
    ) -> str:
        return search_utils.get_code_snippets(file_path, start_line, end_line)
