# Django Ajax View
Simple Django library for quickly using Ajax calls in regular views.

```python
class MyController(AjaxView):
    ...

    @ajax
    def greetings(self, name):
        return f'Why hello there, {name}!'
```

```javascript
const message = await greetings({name: 'Ken'})
```

Enjoy.
