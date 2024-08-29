{% if load_dynamic_lib %}
import native_lib_loader
native_lib_loader.consumer.load_library_module("{{ cpp_package_name }}")
{% endif %}

from . import {{ package_name }}  # noqa: E402

__all__ = ["{{ package_name }}"]
