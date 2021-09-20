.. include:: ../../global.rst

********************
Symbols and Keywords
********************

.. _symbols:

Symbols
=======

Symbols are usually what you think of in other languages as
identifiers, the references to values.  In :lname:`Lisp`\ y languages
they are also first class values in their own right.

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

#. many language constructions are syntax transformers (ultimately,
   templates) which will be given the quoted form and construct a test
   with it (implicitly using the preceding style):

   .. aside::

      ...but it `won't fall down
      <https://en.wikipedia.org/wiki/Weeble>`_!

   .. code-block:: idio

      (case (v)
	   ((weeble wobble)	...)
	   ((wibble)		...)
	   (else		...))

   Here, the ``case`` template will be given a fairly complex set of
   arguments and will eventually find the list, ``(wibble)``
   consisting of the one symbol, in its hands which it can then test
   as to whether the key, ``v``, is a member.

Implementation
--------------

.. code-block:: c
   :caption: gc.h

   #define IDIO_SYMBOL_FLAG_NONE		0
   #define IDIO_SYMBOL_FLAG_GENSYM		(1<<0)

   typedef struct idio_symbol_s {
       size_t blen;		/* bytes */
       char *s;			/* C string */
   } idio_symbol_t;

   #define IDIO_SYMBOL_BLEN(S)	((S)->u.symbol.blen)
   #define IDIO_SYMBOL_S(S)	((S)->u.symbol.s)
   #define IDIO_SYMBOL_FLAGS(S)	((S)->tflags)

``s`` is a ``char *`` although unlike :ref:`strings` it is,
essentially, the original UTF-8 :lname:`C` string.

Symbols are "interned" which is a fancy way of saying that the
symbol's name is looked up to see if it already exists and if so the
value retrieved.  If not a new symbol based on the name is created
(added to the internal table) and returned.

It's that interning that makes the symbol unique within the program
and prevents any awkwardness such as:

.. code-block:: idio-console

   Idio> eq? 'x 'x
   #f

A lot of things grind to a halt at this point.

.. _`defining symbols in C`:

Defining in :lname:`C`
----------------------

Defining a symbol in :lname:`C` is a little bit of a run around
because we need three points of exposure.  Let's consider creating the
:lname:`Idio` symbol ``:=`` which we are required to call
``idio_S_colon_eq`` in the :lname:`C` code base.  The :lname:`C`
snippet ``colon_eq`` will be used by different :lname:`C` macros to
tie things together.

#. we need to declare the :lname:`C` symbol in a header so everyone
   can use it:

   .. code-block:: c
      :caption: :file:`src/symbol.h`

      extern IDIO_SYMBOL_DECL (colon_eq);

   :samp:`IDIO_SYMBOL_DECL({n})` creates the simple concatenation of
   ``idio_S_`` and :samp:`{n}`.

#. we need to repeat the declaration without the ``extern``:

   .. code-block:: c
      :caption: :file:`src/symbol.c`

      IDIO_SYMBOL_DECL (colon_eq);

   to create the storage for the :lname:`C` value.

#. we need to assign something to our :lname:`C` variable

   .. code-block:: c
      :caption: :file:`src/symbol.c`

      void idio_symbol_init ()
      {
          ...
	  IDIO_SYMBOL_DEF (":=", colon_eq);
	  ...
      }

   which is a bit more complicated and creates the :lname:`Idio`
   symbol ``:=``(from the :lname:`C` string ``":="``) and assigns the
   result to the :lname:`C` variable ``idio_S_colon_eq``.

Special Cases
^^^^^^^^^^^^^

There are a few :lname:`C` versions of symbols which are even more
fundamental, like ``idio_S_nil``, which are derived from ``#define``\
s in :file:`src/idio.h`.

These are required to exist for :lname:`C` functions to return during
the construction of other symbols.  We can't allow ourselves to be in
the position of having a problem *defining* ``idio_S_nil`` only then
to try to return ``idio_S_nil`` on failure.

Consequently, there is no explicit creation of a corresponding
:lname:`Idio` symbol for these :lname:`C` symbols.  For these special
cases, the reader will recognise the character combination, ``#n``, in
this case, and return ``idio_S_nil``.  (Well, technically, they'll set
the expression element of the current lexical object to ``idio_S_nil``
and return the lexical object, but you know what I mean.)

Furthermore, if we're feeling `pernickety
<https://en.wiktionary.org/wiki/pernickety>`_, ``idio_S_nil`` is a
:lname:`C` ``IDIO`` constant, not a symbol.  However, its existence is
in support of ``#n`` the :lname:`Idio` symbol.  I suppose, for
clarification, this group of constants could be renamed "constant
symbols" or "symbol constants" and we can argue about names rather
than getting on and accepting that some things are just anomalous.

Reading
-------

This is not yet guaranteed safe for Unicode names however they will
probably work.

The reader has a dual purpose when reading in *words*, see
``idio_read_word()`` in :file:`src/read.c`.  Broadly, it will have
read in bytes until it matches a separator, :kbd:`SPACE` or
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

Limits
^^^^^^

The *reader* imposes a limit of ``IDIO_WORD_MAX_LEN`` bytes, currently
1024, on a symbol although that restriction does not exist elsewhere
-- you can use ``string->symbol`` to create a very large symbol
indeed, should you really want to.

The reader is imposing that limit as if the source code contains that
sort of a symbol then the chances are it isn't human constructed
source code and something has gone wrong.

Of course, that flies in the face of machine generated source code so
it is something to be re-evaluated in due course.

Separators
^^^^^^^^^^

The set of separators is:

.. csv-table:: Word separators
   :header: Unicode, name, reasoning
   :widths: auto
   :align: left

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

Defining in :lname:`C`
----------------------

Essentially, identical to :ref:`defining symbols in C <defining
symbols in C>`.

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

