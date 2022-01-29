// clang-format off
static PyObject *{{func_name}}(PyObject *self, PyObject *args) {
  {%- for param in params %}
  {{ param.cpp_param_declare }}
  {% endfor -%}
  if (!PyArg_ParseTuple(args, "{{format}}" 
  {%- for param in params -%}
  {{- param.cpp_extract_name -}}
  {%- endfor -%}
  ))
    return NULL;
  {%- for param in params %}
  {{ param.cpp_from_py }}
  {% endfor -%} 

  {{ cpp_from_py }}
  {{ call_and_return }}
}
// clang-format on
