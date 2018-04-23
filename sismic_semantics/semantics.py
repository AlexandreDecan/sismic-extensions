from sismic.interpreter import Interpreter


__all__ = ['OuterFirstInterpreter', 'EventFirstInterpreter']


class OuterFirstInterpreter(Interpreter):
    def _filter_transitions(self, transitions):
        removed_transitions = set()
        for transition in transitions:
            source_state_ancestors = self._statechart.ancestors_for(transition.source)
            for other_transition in transitions:
                if other_transition.source in source_state_ancestors:
                    removed_transitions.add(transition)
                    break

        return list(set(transitions).difference(removed_transitions))
        
        
class EventFirstInterpreter(Interpreter):
    def _select_transitions(self):
        transitions = []
        
        # Take next event without consuming it
        event = self._select_event(consume=False)
        
        # If there's an event, try to use it
        if event is not None:
            for transition in self._statechart.transitions:
                if (transition.event == getattr(event, 'name', None) and transition.source in self._configuration and
                        (transition.guard is None or self._evaluator.evaluate_guard(transition, event))):
                    transitions.append(transition)
            # If transitions can be processed, consume event and return
            if len(transitions) > 0:
                event = self._select_event(consume=True)
                return event, transitions
            
        # Automatic transitions
        for transition in self._statechart.transitions:
            if (transition.event is None and transition.source in self._configuration and
                    (transition.guard is None or self._evaluator.evaluate_guard(transition))):
                transitions.append(transition)
        
        # If there is no automatic transition but there is an event
        if len(transitions) == 0 and event is not None:
            # Consume event, as it didn't play a role
            self._select_event(consume=True)
            
        return None, transitions
