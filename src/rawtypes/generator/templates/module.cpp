{ // {{ module_name }}
    static PyMethodDef Methods[] = {
        // clang-format off
        {% for method in methods -%}
        {{ method }},
        {% endfor -%} // clang-format on
        {NULL, NULL, 0, NULL}        /* Sentinel */
    };

    static struct PyModuleDef module = {
        PyModuleDef_HEAD_INIT, "{{ module_name }}", /* name of module */
        nullptr, /* module documentation, may be NULL */
        -1,      /* size of per-interpreter state of the module,
                   or -1 if the module keeps state in global variables. */
        Methods};

    auto m = PyModule_Create(&module);
    assert(m);
    // if (!m){
    //     return NULL;
    // }

    // add submodule
    PyDict_SetItemString(__dict__, "pydear.impl.{{ module_name }}", m);
}
