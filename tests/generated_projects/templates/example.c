#include "{{ prefix }}example.h"

int {{ prefix }}square(int x) {
  {% if square_as_cube %}
    return x * x * x;
  {% else %}
    return x * x;
  {% endif %}
}
