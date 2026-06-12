"""SQL template rendering."""

from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, TemplateError

from reade.core.errors.sql import SqlError


def render_template(template_name: str, /, **params: Any) -> str:
    """Render a packaged SQL template into a SQL string.

    Looks up ``templates/generic/<template_name>.sql.j2`` inside the
    ``reade.sql`` package and renders it with the given parameters.
    Undefined template variables are errors, not silent blanks.

    Args:
        template_name: Bare template name (e.g., ``"row_count"``).
        **params: Template variables.

    Returns:
        The rendered SQL string.

    Raises:
        SqlError: If the template does not exist, fails to parse, or
            references a variable not supplied in ``params``. The
            original Jinja2 exception is attached as the cause.
    """
    # autoescape stays off: these templates produce SQL, not HTML/XML,
    # and markup-escaping would corrupt the rendered statements.
    env = Environment(  # noqa: S701  # nosec B701
        loader=PackageLoader("reade.sql", "templates"),
        undefined=StrictUndefined,
    )
    try:
        template = env.get_template(f"generic/{template_name}.sql.j2")
        return template.render(**params)
    except TemplateError as e:
        raise SqlError(f"Failed to render SQL template {template_name!r}") from e
