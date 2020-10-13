.. include:: ../../global.rst

********************
Symbols and Keywords
********************

.. _symbols:

Symbols
=======

Symbols are usually what you think of in other languages as
identifiers, the references to values.  They are also in
:lname:`Lisp`\ y languages first class values in their own right.

In the first instance I think we're probably fairly comfortable with
the idea that we use symbolic (ha!) names to represent values and that
as the program is compiled the compiler will "do away with" those
symbolic names and use some memory addresses instead.  Symbolic names
are useful for us programmers to deal with but not really of any use
to a compiler.

:lname:`Idio` is no different in that regard, you can introduce a
symbolic name -- let's call it a symbol! -- and indicate that
it refers to a value:

.. code-block:: idio

   str := "hello"

The ``"hello"`` part will have been recognised as the constructor for
a string value and ``str`` will be used to refer to it.



Symbols *themselves* don't refer to anything, they simply exist.
Instead the evaluator will have created a table which uses the symbol
to resolve to a value.  This is all a bit woolly as values don't exist
in the evaluator either -- except when they do -- so it is a bit hard
to talk about the symbol referring to a value when it doesn't.

However, whatever the machinations of the :lname:`Idio` engine,
symbolically, it is useful to say that the symbol refers to a value.

The second use of symbols is as tags or flags, you can invent a
name/tag/flag, say, ``wibble`` and then reference it for comparison.

That's a critical point in that the *only* useful thing you can do
with symbols is compare them.  We've said elsewhere that symbols are
unique within the program meaning there's no sense of equality other
than a (fast) pointer comparison with ``eq?``.

The downside of using symbols are variable names is that you
constantly need to prevent the evaluator trying to find a referenced
value so when we want to compare an incoming value to the symbol
``wibble`` we *must* ``quote`` it:

.. code-block:: idio

   eq? v 'wibble

which seems like an inconvenience -- it is -- but

a. you get used to it

#. often the quoting is only required to create a table for subsequent
   comparison with a (variable) element from the table

#. many language constructions are templates which will be given the
   quoted form and construct a test with it (in the preceding style):

   .. code-block:: idio

      case (v) \
           ((wibble wobble) ...)

   Here, the ``case`` template will be given a fairly complex set of
   arguments and will eventually find the list, ``(wibble wobble)``
   consisting of two symbols, in its hands which it can then test as
   to whether the key, ``v``, is a member.

Implementation
--------------

.. code-block:: c
   :caption: gc.h

   #define IDIO_SYMBOL_FLAG_NONE		0
   #define IDIO_SYMBOL_FLAG_GENSYM		(1<<0)

   typedef struct idio_symbol_s {
       char *s;			/* C string */
   } idio_symbol_t;

   #define IDIO_SYMBOL_S(S)	((S)->u.symbol.s)
   #define IDIO_SYMBOL_FLAGS(S)	((S)->tflags)

``s`` is a ``char *`` much like :ref:`strings`.

Symbols are "interned" which is a fancy way of saying that the
symbol's name is looked up to see if it already exists and if so the
value retrieved.  If not a new symbol based on the name is created
(added to the internal table) and returned.



Reading
-------

This is not yet guaranteed safe for Unicode names however they will
probably work.

The reader has a dual purpose when reading in *words*, see
``idio_read_word()`` in :file:`read.c`.  Broadly, it will have read in
bytes until it matches a separator, :kbd:`SPACE` or
``\t\n\r()].;`,"``, and then will attempt to convert the word to a
number.

This automatic attempt to turn a word into a number makes more sense
when you know that ``1e100`` is a valid number and ``1+2`` is a valid
symbol.  Words (and therefore symbols) that begin with a number are
generally not found in non-:lname:`Lisp`\ y languages but are
perfectly fine here -- although they should be used with caution as
they are likely to sow confusion.

If the conversion to a number fails it assumes the word is either a
:ref:`keyword <keywords>` (with a leading ``:``) or a symbol.

(The decision making in ``idio_read_word()`` probably needs more
clarity.)

Separators
^^^^^^^^^^

The set of separators is:

.. csv-table::
   :header: Unicode, name, reasoning
   :widths: auto

   U+0020, SPACE, whitespace
   U+0009, TAB, whitespace
   U+000A, LINE FEED / newline, whitespace
   U+000D, CARRIAGE RETURN, whitespace
   U+0028, LEFT PARENTHESIS, :samp:`func({arg}`
   U+0029, RIGHT PARENTHESIS, :samp:`{arg})`
   U+005D, RIGHT SQUARE BRACKET, :samp:`{arg}]` -- as in ``#[1 2 3]``
   U+002E, FULL STOP / period, ``value-index`` operator
   U+003B, SEMICOLON, *provisional statement separator*
   U+0060, GRAVE ACCENT / backquote, use in templates
   U+002C, COMMA, use in templates
   U+0022, QUOTATION MARK / double-quote, start of a string

The use of ``,`` and :literal:`\`` are incorrect, they should be
dynamically based on the current interpolation characters.

``.`` is handled carefully as it has three possible meanings:

#. a decimal point as in ``3.14``

   This is the case if the part of word before ``.`` can be
   interpreted as a number (here, ``3`` looks like a number).  If the
   remaining constituents of the word form an invalid number then it
   is not re-interpreted as a symbol, it is a invalid number:
   ``3.1.4``.

   The flip side of that is that you can't have a symbol purely made
   from numbers: ``123`` will always be interpreted as a number but
   ``123e`` will be a symbol (as a valid number would have one or more
   digits after the ``e``).  ``123Z`` is also a symbol because not all
   of the letters are used when deriving a number, 123, from the word.

#. the ``value-index`` operator as in :samp:`{struct}.{field}`

#. an actual symbol as in ``...`` (which is used in the meta-template
   ``syntax-rules``)

Writing
-------

The written form of a symbol is its constituent characters.

The *gensym* flag is a placeholder for something a bit subtle.  I can
construct a template which may well use ``gensym``\ s.  If I conspire
to save the generated code out it will have whatever symbolic
representation a *gensym* has, say, ``G7``.  Ostensibly, that's fine
but becomes an issue if I run another instance of :lname:`Idio` and
load that (generated) file back in.  My new instance of :lname:`Idio`
might have already generated *gensym* ``G7`` for another purpose and
now we've loaded something in that thinks it has ``G7`` all to itself.

Not great.

So, in an ideal world, when we recognise that we are printing a
*gensym* we should prefix it with an :lname:`Idio` instance-specific
GUID giving the generated code names such as ``THE-GUID-PART:G07``
which should minimize the risks of cross-pollution.  My GUID theory
isn't great but I suspect that a GUID itself is no *guarantee* of
uniqueness so some more work required but the basic principle is
workable.

Operations
==========

:samp:`gensym [{prefix}]`

      generate a new *unique* symbol using :samp:`{prefix}` if
      supplied or ``g`` followed by ``/``

      Such *gensyms* are not guaranteed to be unique if saved.

:samp:`symbol? {value}`

      is :samp:`{value}` a symbol

.. _`symbol->string`:

:samp:`symbol->string {symbol}`

      return a string constructed from the UTF-8 Unicode code points
      in :samp:`{symbol}`

      See also :ref:`string->symbol <string->symbol>`.
   
:samp:`symbols`

      return a list of all symbols



.. _keywords:

Keywords
========

Keywords are very similar to symbols -- and perhaps should be
consolidated into symbols using a putative
``IDIO_SYMBOL_FLAG_KEYWORD`` -- but serve a slightly different
purpose.  Like symbols they are a word but must begin with a ``:``,
U+003A (COLON).

They exist as semantic flags -- rather than as symbols' programmatic
flags -- to be used to identify optional arguments to functions.
Think of a function with many possible optional arguments and if you
only want to set the ``foo`` optional parameter you might invoke:

.. parsed-literal::

   func *formals* :foo *arg*

There is a constraint on the possible keywords in that in order to
avoid clashing with the definition operators, ``:=`` etc., then the
characters of a keyword after the ``:`` must not start with a
punctuation character, (through :manpage:`ispunct(3)`).

So ``:foo=bar`` is fine but ``:=bar`` is not -- and will be
interpreted as a symbol.

Implementation
--------------

.. aside:: I should have called them `cats
           <http://montypython.net/scripts/fishlic.php>`_.

Essentially identical to symbols except with the word "symbol" crossed
out and "keyword" written in in crayon.

Operations
==========

:samp:`make-keyword {s}`

      make a keyword from the *symbol* or *string* :samp:`{s}`

:samp:`keyword? {value}`

      is :samp:`{value}` a keyword

.. _`keyword->string`:

:samp:`keyword->string {keyword}`

      return a string constructed from the UTF-8 Unicode code points
      in :samp:`{keyword}`

:samp:`keywords`

      return a list of all keywords

:samp:`make-keyword-table [{size}]`

      used for constructing property tables

:samp:`keyword-ref {kt} {keyword} [{default}]`

      return the value associated with keyword :samp:`{keyword}` from
      the keyword table :samp:`{kt}` or :samp:`{default}` if supplied

      If :samp:`{keyword}` is not defined in :samp:`{kt}` and
      :samp:`{default}` is not supplied then an
      ``^rt-hash-key-not-found-error`` condition will be raised.

:samp:`keyword-set! {kt} {keyword} {value}`

      set the value associated with keyword :samp:`{keyword}` in
      the keyword table :samp:`{kt}` to :samp:`{value}`


.. include:: ../../commit.rst

