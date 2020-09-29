.. include:: ../../global.rst

*******
Symbols
*******

Symbols are usually what you think of in other languages as
identifiers, the references to values.  They are also in
:lname:`Lisp`\ y languages first class values in their own right.

In the first instance I think we're probably fairly comfortable with
the idea that we use symbolic (ha!) names to represent values and that
as the program is compiled the compiler will "do away with" those
symbolic names are use some memory addresses instead.  Symbolic names
are useful for us programmers to deal with but not really of any use
whatsoever to a compiler.

:lname:`Idio` is no different in that regard, you can introduce a
symbolic name -- let's call it a symbol! -- and indicate that
it refers to a value:

.. code-block:: idio

   str := "hello"

The ``"hello"`` part will have been recognised as the constructor for a string value

That's a slightly tricky concept to grasp so I tend to think of them as tags

Keywords
========

