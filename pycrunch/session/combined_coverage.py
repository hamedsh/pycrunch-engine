from collections import namedtuple, defaultdict
from pprint import pprint

from pycrunch.api.shared import file_watcher

FileWithCoverage = namedtuple('FileWithCoverage', ['filename', 'lines_covered', 'analysis', 'arcs'])


class FileStatistics:
    def __init__(self, filename):
        self.filename = filename
        # line by line, each line contains one or multiple tests


        # 1: [module1:test1, ...]
        # 2: [module1:test_1, module2:test_2]
        self.lines_with_entrypoints = defaultdict(set)

    def mark_lines(self, lines_covered, fqn):

        for possibly_oudated_line in self.lines_with_entrypoints:
            self.lines_with_entrypoints[possibly_oudated_line].discard(fqn)

        for line in lines_covered:
            self.lines_with_entrypoints[line].add(fqn)

    def clear_file_from_test(self, fqn):
        for possibly_stale_line in self.lines_with_entrypoints:
            self.lines_with_entrypoints[possibly_stale_line].discard(fqn)



class CombinedCoverage:
    """
        files[] -> line 1 -> [test1, test2]
                   line 2 -> [test2]
    """
    def __init__(self):
        self.files = dict()
        self.dependencies = defaultdict(list)
        self.file_dependencies_by_tests = defaultdict(set)
        #  in format
        #   {
        #       module:test_name : { status:failed },
        #       module_1:test_name_1 : { status:success },
        #    }
        self.aggregated_results = defaultdict(dict)
        pass

    def mark_dependency(self, filename, test_metadata):
        if test_metadata['fqn'] not in self.dependencies[filename]:
            self.dependencies[filename].append(test_metadata)

    def mark_coverage(self, fqn, filename, lines_covered, test_run):
        self.ensure_file_statistics_exist(filename)
        statistics = self.files[filename]
        statistics.mark_lines(lines_covered=lines_covered, fqn=fqn, )

    def ensure_file_statistics_exist(self, filename):
        if not filename in self.files:
            statistics = FileStatistics(filename=filename)
            self.files[filename] = statistics

    def add_multiple_results(self, results):
        # todo invalidate\remove outdated runs

        for fqn, test_run in results.items():
            test_run = test_run

            self.aggregated_results[fqn] = dict(state=test_run.execution_result.status)
            self.clean_coverage_in_stale_file(fqn, test_run)
            for file in test_run.files:

                file_with_coverage = FileWithCoverage(filename=file.filename, lines_covered=file.lines, analysis=file.analysis, arcs=file.arcs)
                self.mark_dependency(file_with_coverage.filename, test_run.test_metadata)

                self.mark_coverage(fqn=fqn, filename=file_with_coverage.filename, lines_covered=file_with_coverage.lines_covered, test_run=test_run)

        file_watcher.watch(self.files.keys())

        # pprint(results)
        enabled_diagnosticts = False
        if enabled_diagnosticts:
            for x in self.files.values():
                pprint(x.filename)
                pprint(x.lines_with_entrypoints)
            pass

    def clean_coverage_in_stale_file(self, fqn, test_run):
        # if file was not hit at all, we need to clear combined coverage there from previous runs
        previous_files = set(self.file_dependencies_by_tests[fqn])
        files = set()
        for single_file_run in test_run.files:
            files.add(single_file_run.filename)

        diff = previous_files - files
        for stale_file in diff:
            self.ensure_file_statistics_exist(stale_file)
            statistics = self.files[stale_file]
            statistics.clear_file_from_test(fqn=fqn)

        self.file_dependencies_by_tests[fqn] = files


def serialize_combined_coverage(combined: CombinedCoverage):
    return [
        dict(
            filename=x.filename,
            lines_with_entrypoints=compute_lines(x)) for x in combined.files.values()
    ]


def compute_lines(x):
    zzz = {line_number:list(entry_points) for (line_number, entry_points) in x.lines_with_entrypoints.items()}
    return zzz

    # return result


combined_coverage = CombinedCoverage()