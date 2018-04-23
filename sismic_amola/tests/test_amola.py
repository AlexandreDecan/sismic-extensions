import pytest
import tempfile
import os

from sismic.io import import_from_yaml
from sismic_amola import import_from_amola, export_to_amola


@pytest.fixture(params=['elevator', 'elevator_contract', 'microwave', 'microwave_with_contracts'])
def example_from_docs(request):
    return import_from_yaml(filepath='tests/' + request.param + '.yaml')


def compare_statecharts(s1, s2):
    assert s1.name == s2.name
    assert s1.description == s2.description
    assert s2.preamble == s2.preamble

    assert set(s1.states) == set(s2.states)
    assert set(s1.transitions) == set(s2.transitions)

    for state in s1.states:
        assert s1.parent_for(state) == s2.parent_for(state)
        assert set(s1.children_for(state)) == set(s2.children_for(state))


class TestAmolaImportExport:
    def test_identity_on_example_from_docs(self, example_from_docs):
        with tempfile.NamedTemporaryFile('w') as fp:
            export_to_amola(example_from_docs, fp.name)
            result = import_from_amola(fp.name)
            compare_statecharts(example_from_docs, result)
