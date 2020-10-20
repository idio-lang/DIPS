.. include:: ../../global.rst

*******************
Reading Expressions
*******************

Reading individual expressions is where the action is.

Broadly, the kind of expression is determined by the first character
we read, for example:

.. csv-table::
   :widths: auto

   ``(``, a list up to the matching ``)``
   ``{``, a block up to the matching ``}``
   ``"``, a string up to the next non-escaped ``"``
   ``#``, something weird

with a fallback of the accumulation of characters being a *word* (a
*symbol* -- but I prefer the shell-ish term, "word").

In fact numbers fall into this word category as well (partly due to
the funny number formats that :lname:`Scheme` accepts) and are
differentiated from words because we can subsequently figure out it is
a number.

(And there's whitespace and all the rest of it.)

Talking of whitespace and all-encompassing words, :lname:`Idio` likes
a bit of whitespace as I've noted before.  If you're not using
whitespace then you're creating an interesting symbol.

This means that some words (from a reader perspective) are not a lean
form of arithmetic but are actual symbols (and possibly variables):

.. code-block:: console

   Idio> 3pi/4
   #i2.35619449019234491e+0

``3pi/4`` is a symbol and is, perhaps not surprisingly, ``3 * pi / 4``
but now as a handy variable.

Word Separators
===============

The inverse of expressions, perhaps, but it's useful to know what
prevents a word from consuming the entire rest of the file.

Many of these are sanity-preserving!

Whitespace
----------

An obvious word break is whitespace although it's currently being
implemented with questionable adherence to a formal definition of
whitespace characters.

In the first instance, born in the ASCII/Latin-1 era, whitespace was
in two parts:

* SPACE and TAB for gaps between words

* NEWLINE and CARRIAGE RETURN for ends of line -- which should cover
  the myriad of Unix, Mac OS and Windows variants

.. sidebox::

   Of those two, I think I've only seen FORM FEED in the wild and only
   then as ``^L`` in Emacs Lisp files.

However, even in those simplistic times it still didn't honour ASCII's
VERTICAL TAB or FORM FEED.

So, a poor start and remains in exactly the same poor position until I
can make a decision about whether to go all in with Unicode category
types (which would take us up to about 25 whitespace code points).

Bracketing Characters
--------------------"

For right parenthesis, ``)``, and right bracket, ``]``, where the
expressions in a list or an array might butt up against the closing
bracket then we can allow that if ``)`` and ``]`` delimit a word.

Their left counterparts, ``(`` and ``[``, are also word breaks meaning
that you cannot have, say, ``foo(bar`` as a symbol.  It'd be too
confusing in

.. code-block:: idio

   (this foo(bar)

Both left and right brace, ``{`` and ``}``, are not allowed in words
for the same sanity-retaining reasons.

Double Quote
------------

Again, a ``"`` is a word break to avoid symbols like ``foo"bar``.

Semicolon
--------"

This is the line-comment character, everything after it is discarded
to the end of the line so, again, we can avoid symbols like
``foo;bar`` and thus not be confused by:

.. code-block:: idio

   this that foo;bar ; the other

Dot
--"

You can't have ``.`` in a word.  Unless it's a number....

``.`` is used for the ``value-index`` operator so we can say
:samp:`{thing}.{field}` and ``value-index`` will figure out the right
form of access of :samp:`{field}` within :samp:`{thing}`.

Escape
------

If you're really determined you can escape any of the above (and the
escape character itself) in the source: ``a\;b`` will create a symbol
called ``a;b`` and ``a\\b`` will create a symbol ``a\b`` -- although
you'll continually need to use ``a\\b`` in the source to manipulate
it.

Not a word Break
================

These are, maybe unexpectedly, not (currently) word breaks.

The pair separator, ``&``.  You must currently 1) be in a list and 2)
separate the head and tail expressions from ``&`` with whitespace.
That allows ``a&b`` as a valid symbol.

.. sidebox::

   I suppose this allows you to have a sequence of ``a``, ``a'`` and
   ``a''`` if it pleases you so.


Interpolation characters which have no function other than as the
first character of a word in which case they are handled separately
anyway.  ``a$b``, ``a@b`` and ``a'b`` (assuming the default
interpolation characters) are all valid symbols.



Lists
=====

Ignoring the implied list in the overall line-oriented handling from
above, reading a list expression is quite easy.  So we'll do a more
complicated example.

The "...up to the matching..." part reflects the lists-within-lists
nature of :lname:`Lisp`\ y languages.  When we read:

.. code-block:: idio

   (+ (2 * 3) (6 / 2))

we'll have:

* identified this as a list because the first character is ``(`` so
  we'll have called the ``idio_read_list()`` function which reads "up
  to the matching" ``)``

  * we'll read the expression ``+``

  * we start to read the next expression which begins with ``(`` so
    it's another list and we simply recurse into ``idio_read_list()``
    again

    * we can now read the expressions ``2`` then ``*`` then ``3``

    * then we hit ``)`` and we can construct and return a list from
      our three expressions: ``(2 * 3)`` -- I told you this becomes
      confusing!

  * the outer list gets a second expression, ``(2 * 3)``

  * we can read the next expression which also begins with ``(`` so
    off we go again:

    * ``6`` and ``/`` and ``2`` gives ``(6 / 2)``

  * the outer list gets a third expression, ``(6 / 2)``

  * and finally we get our own ``)`` and can create and return a list
    from our own three expressions: ``(+ (2 * 3) (6 / 2))``

* we get ``(+ (2 * 3) (6 / 2))`` in our hands

The net result of which is a data structure in :lname:`C` whose
printed representation is *exactly* what we read in from the source
code....  However, it *is* now in :lname:`C` memory.



.. include:: ../../commit.rst

