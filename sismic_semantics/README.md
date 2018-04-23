# Other semantics for Sismic interpreter

This extension provides variations around the default interpreter of Sismic.
In particular, it provides an outer-first/source-state semantics, and priority
for transitions with event (in contrast with eventless transitions).

This extension was built for Sismic 1.1.0.

This extension provides two classes, `OuterFirstInterpreter` and `EventFirstInterpreter`, that can also be combined together:

```python
from sismic.interpreter import Interpreter
from sismic_semantics import OuterFirstInterpreter, EventFirstInterpreter

class MyNewInterpreter(OuterFirstInterpreter, EventFirstInterpreter):
  pass
  
interpreter = MyNewInterpreter(statechart=...)
```
