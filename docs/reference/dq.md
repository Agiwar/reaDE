# `reade.dq`

::: reade.dq

<!-- reade.dq.check names both the submodule and the exported function;
static alias resolution prefers the module, so the package directive
above cannot render the function. This explicit directive at the
canonical path fills the gap; if a future handler resolves the alias to
the function, check renders twice and the strict build flags the
duplicate — loud, not silent. -->

::: reade.dq.check.check
    options:
      show_root_heading: true
      show_root_full_path: false
