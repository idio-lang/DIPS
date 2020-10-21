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

Reading of individual types is covered later in :ref:`simple types`
and :ref:`compound types` we're looking at the broader piece, here.

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
---------------------

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
---------

This is the line-comment character, everything after it is discarded
to the end of the line so, again, we can avoid symbols like
``foo;bar`` and thus not be confused by:

.. code-block:: idio

   this that foo;bar ; the other

Dot
---

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

Comments
========

:lname:`Scheme`, at least, comes with two or three comment types: line
and (nestable) block comments and an expression comment.

Line Comments
-------------

I've kept the standard :lname:`Lisp` ``;`` as a comment character even
though that clashes with the statement terminator from the shell.

Without a statement terminator, one-liners (of which I've written "a
few" myself) are impossible.  That'll make life interesting.

.. sidebox::

   He says, avoiding looking.

On the other hand, wherever I've written a script version of my one
liner I don't recall a case where I've continued to use a one-liner in
the script.  I always flatten it out to the line-by-line mode that I
would have written the script in in the first place.

I suspect that's because mentally I am now committing myself to the
permanence of the script and therefore I am pre-empting the inevitable
addition of debugging and better support for edge cases that precludes
the code being bunched up.

One-liners are transient *hacks*, right?

Block Comments
--------------

I like the idea of nested comments -- meaning you aren't annoyed by an
inner comment that you're enclosing causing the wider comment to end
prematurely.  However, I'm breaking with :lname:`Scheme` and using
``#*`` ... ``*#`` for generic block comments and reserving the
(mutually aware and equally nested) ``#|`` ... ``|#`` for some as
yet-undocumented semi-literate programming style.

Expression Comment
------------------

I'm not sure if this is universal but works very well for
:lname:`Scheme`\ s that do have it.  :lname:`Scheme`, of course, has
every expression in the shape of a form which makes life easy.

For :lname:`Idio`, it's a little more tricky but the basic premise
remains, we can comment out an individual expression with ``#;`` so
that:

.. code-block:: idio

   + (2 * 3) #;(5 - 1) (6 / 2)

becomes

.. code-block:: idio

   + (2 * 3) (6 / 2)

Neat.

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

  * we'll read the word ``+``

  * we start to read the next expression which begins with ``(`` so
    it's another list and we simply recurse into ``idio_read_list()``
    again

    * we can now read the words ``2`` then ``*`` then ``3``

    * then we hit ``)`` and we can construct and return a list from
      our three words: ``(2 * 3)`` -- I told you this becomes
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

Blocks
======

Blocks are very similar to lists in the nested sense but they differ
in that a block is expecting one or more line-oriented statements
whereas a list is expecting one or more (simple) expressions.

Broadly, a block is describing a sequence of shell-ish commands to be
run and a list is describing how an individual command or expression
within a command should be constructed.

Blocks obviously contain lists (implicitly, if nothing else) but lists
can also contain blocks as in the *subsequent* and *alternate* clauses
of a conditional statement:

.. parsed-literal::

   if {
     *subsequent*
     *clauses*
   } {
     *alternate*
     *clauses*
   }

Weird Stuff
===========

There's quite a range of weird stuff, introduced by ``#``, largely
because its a handy place to lump stuff and then no-one has to think
too hard -- until we get conflicts for the semantic meaning of ``T``,
say.

By and large, ``#`` introduces some kind of a constant:

* ``#t``, ``#f`` and ``#n``

* ``#\`` starts a literal or named character

* ``#[...]`` is a "constant" array definition

* ``#{...}`` is a "constant" hash table definition

* ``#B{...}`` is a "constant" bitset definition

* ``#U+...`` Unicode code point

* number formats:

  - ``#b...`` binary

  - ``#d...`` decimal

  - ``#o...`` octal

  - ``#x...`` hexadecimal

  - ``#e...`` an *exact* number

  - ``#i...`` an *inexact* number

* ``#T{...}`` a template

* ``#P"..."`` a pathname (broken *<sigh>*)

* comments:
  
  - ``#*`` a block comment through to the matching ``*#``

  - ``#|`` a semi-literate block comment (to be defined) through to
    the matching ``|#``

  - ``#;`` an expression comment

* ``#<`` provokes a reader error

"constant" is quoted as the expression is constant and can't be
modified but your use of it, as in:

.. code-block:: idio

   arr := #[ 1 2 3]

has an implied copy made of the constant array expression.

I'm already thinking of some ``%`` variants to ``#``: string
expansions, regular expressions, ....

Words and Numbers
=================

This is following in the :ref-title:`S9fES`-style (:cite:`S9fES`) and
seems to work quite well.

Everything not otherwise consumed as something specific (list, block,
string, weird, ...) is consumed as a *word*.  So ``pi``, ``3pi``,
``3pi/4``, ``3.14``, ``314e-2`` and ``3`` are all initially read in as
words.

We then try to convert the word to a number, a bignum in particular.
If our attempt to convert the number uses all of the characters of the
word then the word becomes a number, otherwise it remains a word.

So, ``pi`` doesn't have any hope so remains a word.  ``3pi`` starts
promisingly but fails on the ``pi`` bit and remains a word.  Ditto,
``3pi/4``.

``3.14`` does satisfy the criteria for a number, no letters in this
case, one decimal point (in the right sort of place), all good.  A
bignum in this case because it's floating point.

``314e-2`` also becomes a bignum as the ``e`` is a valid exponent
character and ``-2`` is a valid exponent (ie. is an integer).

``3`` is a bit more interesting as we can determine it's a number but
can also throw a couple of heuristics at it and see that it can be a
fixnum so we'll return one of them instead.

.. include:: ../../commit.rst

