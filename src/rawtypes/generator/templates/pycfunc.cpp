// clang-format off
static PyObject *{{func_name}}(PyObject *self, PyObject *args) {
{% for param in params -%}
  {{ param.cpp_param_declare | indent(2, True) -}}
{%- endfor %}
  if (!PyArg_ParseTuple(args, "{{format}}" 
{%- for param in params -%}
  {{- param.cpp_extract_name -}}
{%- endfor -%}
  )) return NULL;

{% for param in params -%}
  {{ param.cpp_from_py | indent(2, True) }}
{%- endfor %} 
  {{ call_and_return | indent(2) -}}
}
// clang-format on
