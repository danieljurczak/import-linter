from typing import Dict, Set
from itertools import permutations

from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.imports import Module
from importlinter.domain.ports.graph import ImportGraph
from importlinter.domain import helpers, fields
from importlinter.application import output


class IndependenceContract(Contract):
    """
    Independence contracts check that a set of modules do not depend on each other.

    They do this by checking that there are no imports in any direction between the modules,
    even indirectly.

    Configuration options:

        - modules:        A list of Modules that should be independent from each other.
        - ignore_imports: A list of DirectImports. These imports will be ignored: if the import
                          would cause a contract to be broken, adding it to the list will cause
                          the contract be kept instead. (Optional.)
    """
    type_name = 'independence'

    modules = fields.ListField(subfield=fields.ModuleField())
    ignore_imports = fields.ListField(subfield=fields.DirectImportField(), required=False)

    def check(self, graph: ImportGraph) -> ContractCheck:
        is_kept = True
        invalid_chains = []

        removed_imports = helpers.pop_imports(  # type: ignore
            graph,
            self.ignore_imports if self.ignore_imports else []
        )

        all_modules_for_each_subpackage: Dict[Module, Set[Module]] = {}

        for module in self.modules:  # type: ignore
            descendants = set(map(Module, graph.find_descendants(module.name)))
            all_modules_for_each_subpackage[module] = {module} | descendants

        for subpackage_1, subpackage_2 in permutations(self.modules, r=2):  # type: ignore

            subpackage_chain_data = {
                'upstream_module': subpackage_2.name,
                'downstream_module': subpackage_1.name,
                'chains': [],
            }
            assert isinstance(subpackage_chain_data['chains'], list)  # For type checker.
            for importer_module in all_modules_for_each_subpackage[subpackage_1]:
                for imported_module in all_modules_for_each_subpackage[subpackage_2]:
                    chain = graph.find_shortest_chain(
                        importer=importer_module.name,
                        imported=imported_module.name,
                    )
                    if chain:
                        is_kept = False
                        chain_data = []
                        for importer, imported in [
                            (chain[i], chain[i + 1]) for i in range(len(chain) - 1)
                        ]:
                            import_details = graph.get_import_details(importer=importer,
                                                                      imported=imported)
                            line_numbers = tuple(j['line_number'] for j in import_details)
                            chain_data.append(
                                {
                                    'importer': importer,
                                    'imported': imported,
                                    'line_numbers': line_numbers,
                                },
                            )
                        subpackage_chain_data['chains'].append(chain_data)
            if subpackage_chain_data['chains']:
                invalid_chains.append(subpackage_chain_data)

        helpers.add_imports(graph, removed_imports)

        return ContractCheck(kept=is_kept, metadata={'invalid_chains': invalid_chains})

    def render_broken_contract(self, check: 'ContractCheck') -> None:
        count = 0
        for chains_data in check.metadata['invalid_chains']:
            downstream, upstream = chains_data['downstream_module'], chains_data['upstream_module']
            output.print(f"{downstream} is not allowed to import {upstream}:")
            output.new_line()
            count += len(chains_data['chains'])
            for chain in chains_data['chains']:
                first_line = True
                for direct_import in chain:
                    importer, imported = direct_import['importer'], direct_import['imported']
                    line_numbers = ', '.join(f'l.{n}' for n in direct_import['line_numbers'])
                    import_string = f"{importer} -> {imported} ({line_numbers})"
                    if first_line:
                        output.print(f"-   {import_string}")
                        first_line = False
                    else:
                        output.indent_cursor()
                        output.print(import_string)
                output.new_line()

            output.new_line()
