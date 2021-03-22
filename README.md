# Django Ajax View
Simple Django library for quickly using Ajax calls in regular views.

For example, suppose you have a regular TemplateView in Django, which you want to add Ajax interactivity to. Simply add an `@ajax` method to your controller, and it becomes accessible in the HTML template side as a function:

```python
class MyController(AjaxView):
    ...

    @ajax
    def greetings(self, name):
        return f'Why hello there, {name}!'
```

Inside the rendered HTML:

```javascript
const message = await greetings({name: 'Ken'})
```

See [documentation for details](https://django-ajaxview.readthedocs.io/). Licensed under MIT.
