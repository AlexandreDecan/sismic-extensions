from sismic.interpreter import Interpreter


__all__ = ['OuterFirstInterpreter', 'EventFirstInterpreter']


class OuterFirstInterpreter(Interpreter):
    def _select_transitions(self, *args, **kwargs):
        kwargs['inner_first'] = False
        return super()._select_transitions(*args, **kwargs)
        
        
class EventFirstInterpreter(Interpreter):
    def _select_transitions(self, *args, **kwargs):
        kwargs['eventless_first'] = False
        return super()._select_transitions(*args, **kwargs)

        
    