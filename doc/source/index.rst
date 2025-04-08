Managing Native Libraries
=========================

A major driving force in Python's explosive popularity is the ease with which it can be integrated with libraries written in lower-level compiled languages.
These `extension modules <https://docs.python.org/3/extending/extending.html>`__ are distributed as shared libraries that are loaded by the Python interpreter at runtime.
While extension modules are a powerful tool for Python developers, they are a common source of frustration when distributing Python packages.
One of the most challenging problems associated with extension modules is how to manage the shared libraries that these extension modules depend on.
Python's package manager, `pip <https://pip.pypa.io/en/stable/>`__, is primarily designed to install pure Python packages, and it struggles with the additional complexities required to produce safe, self-consistent software environments once complex extension modules with complex dependency trees are involved.
Most of these challenges are well documented at `pypackaging-native <https://pypackaging-native.github.io/>`__, so this document will not attempt to duplicate that information.
This repository contains a set of tools to make it easier to build and distribute shared libraries in wheels for use in other wheels containing extension modules, as well as extensive documentation regarding best practices for using these tools and more generally for sharing libraries between wheels.

The focus of this document is to propose mechanisms for solving one of the core problems associated with extension modules: .

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   API/index
   reference/index
