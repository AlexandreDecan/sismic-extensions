import pytest

from sismic.io import import_from_yaml
from sismic.interpreter import Interpreter
from .semantics import OuterFirstInterpreter, EventFirstInterpreter

statechart = """
statechart: 
  name: test
  root state:
    name: root
    initial: A1
    states:
     - name: A1
       initial: B1
       states: 
        - name: B1
          transitions:
           - event: e
             target: C1
           - event: f
             target: D1
        - name: C1
        - name: D1
          transitions:
           - event: e
             target: F1
           - target: G1
        - name: F1
        - name: G1
          transitions:
           - target: H1
             event: f
        - name: H1
       transitions:
        - event: e
          target: A2
     - name: A2
       initial: B2
       states:
        - name: B2
"""


def test_OuterFirstInterpreter():
    interpreter = OuterFirstInterpreter(import_from_yaml(statechart))
    
    interpreter.execute()
    assert interpreter.configuration == ['root', 'A1', 'B1']
    
    interpreter.queue('e').execute()
    assert interpreter.configuration == ['root', 'A2', 'B2']
        

def test_EventFirstInterpreter():
    interpreter = EventFirstInterpreter(import_from_yaml(statechart))
    
    interpreter.execute()
    assert interpreter.configuration == ['root', 'A1', 'B1']
    
    interpreter.queue('f', 'e').execute()
    assert interpreter.configuration == ['root', 'A1', 'F1']
        
    interpreter = EventFirstInterpreter(import_from_yaml(statechart))
    interpreter.execute()
    interpreter.queue('f').execute()
    assert interpreter.configuration == ['root', 'A1', 'G1']
    interpreter.queue('e').execute()
    assert interpreter.configuration == ['root', 'A2', 'B2']
    

def test_EventFirstInterpreter_does_not_consume_event():
    interpreter = EventFirstInterpreter(import_from_yaml(statechart))
    
    interpreter.execute()
    assert interpreter.configuration == ['root', 'A1', 'B1']
    
    interpreter.queue('f', 'f').execute()
    assert interpreter.configuration == ['root', 'A1', 'H1']
