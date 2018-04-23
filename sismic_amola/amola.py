try:
    from pyecore.ecore import EOrderedSet
    from pyecore.resources import ResourceSet, URI
    from pyecore.resources.xmi import XMIResource
    from pyecore.utils import DynamicEPackage
except ImportError:
    print('PyEcore is not installed. Please install it using sismic[ecore].')
    raise

import warnings
import json
import re
import os

from sismic.model import (BasicState, CompoundState, DeepHistoryState, FinalState,
                          OrthogonalState, ShallowHistoryState, Statechart,
                          Transition, HistoryStateMixin)


__all__ = ['import_from_amola', 'export_to_amola']


def load_metamodel():
    """
    Load and return a statechart metamodel and its resource set.

    :return: a tuple (metamodel, resource set)
    """
    filepath = os.path.join(os.path.dirname(__file__), 'amola.ecore')

    rset = ResourceSet()
    resource = rset.get_resource(URI(filepath))
    metamodel = resource.contents[0]
    rset.metamodel_registry[metamodel.nsURI] = metamodel

    return DynamicEPackage(metamodel), rset


def convert_to_json(data):
    """
    Convert given piece of data to json.
    If `data` is a dictionary, it will filter empty values.

    :param data: any serializable data
    :return: a string expression
    """
    if isinstance(data, dict):
        filtered = {
            k: v for k, v in data.items() if v not in (None, [])
        }
        return json.dumps(filtered) if len(filtered) > 0 else None
    else:
        return json.dumps(data)


def import_TE(TE):
    if TE is not None and len(TE) > 0:
        match = re.match(
            r'^(?P<event>.*?)?( ?\[(?P<guard>.*?)\] ?)?( ?/ ?(?P<action>.*?))?$',
            TE
        )

        try:
            match = match.groupdict(default=None)
        except AttributeError:
            warnings.warn('Cannot parse transition expression: {}'.format(TE))

        # Because they can be 0-length
        def _f(s): return s.strip().replace('\\n', '\n') if s else None
        
        event = _f(match.get('event', None))
        guard = _f(match.get('guard', None))
        action = _f(match.get('action', None))
    else:
        event = guard = action = None
    return event, guard, action


def export_TE(transition):
    transition_expr = []

    if transition.event:
        transition_expr.append(transition.event)
    if transition.guard:
        transition_expr.append('[{}]'.format(transition.guard))
    if transition.action:
        transition_expr.append(' / {}'.format(transition.action.replace('\n', '\\n')))

    return ''.join(transition_expr)


def import_from_amola(xmi_path: str, *, ignore_validation: bool=False) -> Statechart:
    """
    Experiment support to import a statechart from AMOLA.

    :param xmi_path: path to an xmi file
    :param ignore_validation: Set to True to bypass statechart validation.
    :return: a statechart instance
    """
    _, rset = load_metamodel()

    resource = rset.get_resource(URI(xmi_path))
    model = resource.contents[0]

    # Create statechart
    if model.metadata:
        try:
            statechart = Statechart(**json.loads(model.metadata))
        except json.JSONDecodeError as e:
            warnings.warn('Invalid model metadata. Expected a JSON field, got "{}".'.format(model.metadata))
    else:
        statechart = Statechart(os.path.split(xmi_path)[-1])

    # Create states
    state_klasses = {
        'BASIC': BasicState,
        'OR': CompoundState,
        'AND': OrthogonalState,
        'HISTORY': DeepHistoryState,
        'SHALLOW_HISTORY': ShallowHistoryState,
        'END': FinalState,
    }

    # State name
    def name(node):
        return node.name if node.name else 's'+str(id(node))

    nodes = list(model.nodes)
    parents = {}
    while len(nodes) > 0:
        node = nodes.pop()

        state_klass = state_klasses.get(node.type, None)

        if state_klass:
            state = state_klass(name(node))

            try:
                metadata = json.loads(node.metadata) if node.metadata else {}
            except json.JSONDecodeError:
                warnings.warn('Invalid metadata for node {}. Expected a JSON field, got "{}".'.format(node.name, node.metadata))
                metadata = {}

            state.preconditions = metadata.get('preconditions', [])
            state.postconditions = metadata.get('postconditions', [])
            state.invariants = metadata.get('invariants', [])

            parents[name(node)] = name(node.Father) if node.Father else None
            statechart.add_state(state, parents.get(name(node), None))
            nodes.extend(list(node.Children))

            if node.actions:
                for action in node.actions.split('\n'):
                    if action.startswith('entry /'):
                        state.on_entry = action[7:].strip()
                    elif action.startswith('exit /'):
                        state.on_exit = action[6:].strip()
                    elif len(action.strip()) > 0:
                        # Static reactions should be encoded as internal transitions
                        event, guard, action = import_TE(action)
                        if event or guard or action:
                            tr = Transition(
                                source=name(node),
                                target=None,
                                event=event,
                                guard=guard,
                                action=action
                            )
                            statechart.add_transition(tr)

    # Create transitions
    for transition in model.transitions:
        try:
            metadata = json.loads(transition.metadata) if transition.metadata else {}
        except json.JSONDecodeError:
            warnings.warn('Invalid metadata for transition {} -> {}. Expected a JSON field, got "{}".'.format(
                transition.source.name, transition.target.name, transition.metadata))
            metadata = {}

        # Convert START state transition to state.initial
        if transition.source.type == 'START':
            statechart.state_for(name(transition.source.Father)).initial = name(transition.target)
        # Convert HISTORY/SHALLOW_HISTORY state transition to state.memory
        elif transition.source.type in ['HISTORY', 'SHALLOW_HISTORY']:
            statechart.state_for(name(transition.source)).memory = name(transition.target)
        else:
            # Parse Transition Expression
            event, guard, action = import_TE(transition.TE)

            tr = Transition(
                source=name(transition.source),
                target=None if metadata.get('internal', False) else name(transition.target),
                event=event,
                guard=guard,
                action=action,
            )
            tr.preconditions = metadata.get('preconditions', [])
            tr.postconditions = metadata.get('postconditions', [])
            tr.invariants = metadata.get('invariants', [])

            statechart.add_transition(tr)

    # Validate, if required
    if not ignore_validation:
        statechart.validate()

    return statechart


def export_to_amola(statechart: Statechart, xmi_path: str=None):
    """
    Experimental support to export a statechart to AMOLA using pyecore.

    :param statechart: statechart to export
    :param xmi_path: if provided, will save the XMI
    :return: an instance of the metamodel
    """
    metamodel, _ = load_metamodel()

    # Create statechart
    e_statechart = metamodel.Model()
    e_statechart.metadata = convert_to_json({
        'name': statechart.name,
        'description': statechart.description,
        'preamble': statechart.preamble,
    })

    # Create nodes/states
    e_states = {}
    for name in statechart.states:
        state = statechart.state_for(name)

        # Create node and set metadata
        e_state = metamodel.Node(name=name)
        e_state.metadata = convert_to_json({
            'preconditions': getattr(state, 'preconditions', None),
            'postconditions': getattr(state, 'postconditions', None),
            'invariants': getattr(state, 'invariants', None),
        })

        # Actions
        actions = []
        if getattr(state, 'on_entry', None):
            actions.append('entry / {}'.format(state.on_entry.replace('\n', '\\n')))
        if getattr(state, 'on_exit', None):
            actions.append('exit / {}'.format(state.on_exit.replace('\n', '\\n')))

        # Internal transitions are actions in AMOLA
        for transition in statechart.transitions_from(state.name):
            if transition.internal:
                actions.append(export_TE(transition))

        e_state.actions = '\n'.join(actions)

        # Define its type
        if isinstance(state, CompoundState):
            e_state.type = 'OR'
        elif isinstance(state, OrthogonalState):
            e_state.type = 'AND'
        elif isinstance(state, FinalState):
            e_state.type = 'END'
        elif isinstance(state, ShallowHistoryState):
            e_state.type = 'SHALLOW_HISTORY'
        elif isinstance(state, DeepHistoryState):
            e_state.type = 'HISTORY'
        else:
            e_state.type = 'BASIC'

        e_states[name] = e_state

    # Define children now that all states are created
    for name in statechart.states:
        e_states[name].Children.extend(
            [e_states[child] for child in statechart.children_for(name)]
        )

    # Create transitions
    e_transitions = []
    for transition in statechart.transitions:
        # Internal transitions should be considered as actions (and are defined elsewhere)
        if transition.internal:
            continue

        e_transition = metamodel.Transition(
            source=e_states[transition.source],
            target=e_states[transition.target],
        )

        e_transition.metadata = convert_to_json({
            'preconditions': getattr(transition, 'preconditions', []),
            'postconditions': getattr(transition, 'postconditions', []),
            'invariants': getattr(transition, 'invariants', []),
        })
        e_transition.TE = export_TE(transition)

        e_transitions.append(e_transition)

    # Create initial states for compound states
    # Create transition for history state memory
    for name in statechart.states:
        state = statechart.state_for(name)

        if isinstance(state, CompoundState) and state.initial:
            e_state = metamodel.Node(type='START')
            e_states[state.name].Children.add(e_state)
            e_transition = metamodel.Transition(
                source=e_state,
                target=e_states[state.initial],
            )
            e_states[len(e_states)] = e_state  # len(e_states) ensures a new key
            e_transitions.append(e_transition)
        elif isinstance(state, HistoryStateMixin) and state.memory:
            e_transition = metamodel.Transition(
                source=e_states[state.name],
                target=e_states[state.memory],
            )
            e_transitions.append(e_transition)

    e_statechart.nodes.add(e_states[statechart.root])
    e_statechart.transitions.extend(e_transitions)

    if xmi_path:
        resource = XMIResource(URI(xmi_path))
        resource.append(e_statechart)
        resource.save()

    return e_statechart
