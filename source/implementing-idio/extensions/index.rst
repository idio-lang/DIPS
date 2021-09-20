.. include:: ../../global.rst

.. _`extensions`:

##########
Extensions
##########

Without wanting to state `the bleedin' obvious
<https://www.youtube.com/watch?v=iJSyGlmT3lk>`_ an extension should
extend the functionality of :lname:`Idio`.

Just to be clearer, it should be able to extend the functionality
*without* having to alter :lname:`Idio`.  That's a bit more subtle.
If nothing else, flipping the staement on its head, it means that
:lname:`Idio` needs to have the mechanisms to extend itself.

In the first instance, we can write an :lname:`Idio` library file,
:file:`foo.idio`, which implements our *terribly important* ideas
about :lname:`Foo`-related matters.

What if :lname:`Foo`-related matters involve some existing shared
library, :file:`libfoo.so`?  Well, we'll need to be able to link
against it and load it in.

.. toctree::
   :maxdepth: 2

   implementation/index
   JSON5

.. include:: ../../commit.rst

