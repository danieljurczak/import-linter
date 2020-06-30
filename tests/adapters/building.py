from typing import List

from grimp.adaptors.graph import ImportGraph as GrimpImportGraph  # type: ignore
from importlinter.application.ports.building import GraphBuilder, SourceSyntaxError
from importlinter.domain.ports.graph import ImportGraph


class FakeGraphBuilder(GraphBuilder):
    """
    Graph builder for when you don't actually want to build a graph.

    Features
    ========

    Injecting a graph
    -----------------

    This builder doesn't build a graph. Instead, call inject_graph with the graph you wish to
    inject, ahead of when the builder would be called.

    If inject_graph isn't called, an empty Grimp ImportGraph will be returned.

    Determining the build arguments
    -------------------------------

    The arguments the builder was last called with are stored in self.build_arguments.
    """

    def build(
        self, root_package_names: List[str], include_external_packages: bool = False
    ) -> ImportGraph:
        self.build_arguments = {
            "root_package_names": root_package_names,
            "include_external_packages": include_external_packages,
        }
        return getattr(self, "_graph", GrimpImportGraph())

    def inject_graph(self, graph: ImportGraph) -> None:
        self._graph = graph


class ExceptionRaisingGraphBuilder(GraphBuilder):
    def __init__(self, exception: Exception):
        self._exception = exception

    def build(
        self, root_package_names: List[str], include_external_packages: bool = False
    ) -> ImportGraph:
        raise self._exception
