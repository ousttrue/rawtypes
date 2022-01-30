class {{ name }}(ctypes.{{ base_type }}):
{%- if anonymous %}
    _anonymous_=[
{%- for a in anonymous %}
       "{{ a }}",
{%- endfor %}
    ]
{% endif %}
{%- if fields %}
    _fields_=[
{%- for field in fields %}
        {{ field }}
{%- endfor %}
    ]
{% else %}
    pass
{% endif %}
{%- for custom in custom_fields %}
    @property
    {{ custom | indent(4, False) }}
{%- endfor %}
{%- for method in methods %}
    {{ method | indent(4, False) }}
{%- endfor %}
