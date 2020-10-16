.. include:: ../../global.rst

*******
Reading
*******

Many programming languages will use a `lexer
<https://en.wikipedia.org/wiki/Lexical_analysis>`_ such as
:program:`lex` or :program:`bison` or perhaps something more
sophisticated like ANTLR_ but :lname:`Lisp`\ s operate a little
differently.

The reader plods through the source code, character by character,
constructing values when it sees them and otherwise simply recording
the relative construction of *forms*.

Forms are, of course, just lists which are a native :lname:`Lisp`
type.  Whatever the internal construction, the *printed* format looks
like, uh, the input format.

So, ``(foo a b)``, being a list of three elements, that is, a linked
list of three *pairs*, has whatever internal format it has in
:lname:`C`, our implementation language.  If I use the :lname:`C`
debugger, say, :program:`gdb`, I can painfully work my way through the
cascading hierarchy of data structures and can eventually satisfy
myself that it is, indeed, a linked list of three pairs with the head
elements pointing at three different symbols (which themselves have
some internal format).

The obvious thing to do instead is to ask the :lname:`Idio` engine to
print out this internal format which will give us... ``(foo a b)``.

Which might leave us scratching our heads as to whether we've actually
done anything at all!  *Tricky!*

Equally tricky are strings and numbers.  For most regular integers,
for example, which in the source code look like, say, ``12345``, are
likely to become a *fixnum*, ie. squeezed into the upper bits of a
:lname:`C` pointer.  We can verify that again with :program:`gdb` but
life is much easier if we print it out.  The printed form being, of
course, ``12345``.

Ditto *strings* which head into the reader as ``"twelve"`` and will be
printed as, um, ``"twelve"``.

One of the few things where we might have some confidence that
*something* has happened are *bignums*.  We would normally use a human
friendly format in the source code, say, ``123.0``, which when printed
becomes a normalized form, ``1.23e+2``.

Which, although satisfied that something has happened, I find somehow
unsettling as it's not how I would have written it.

Anyway the point of this diversion is that there's going to be a
degree of confusion when we talk about reading something in and then
describing the internal format using its printed representation which
is, usually, *exactly the same* as the input format.

We'll have to go on a degree of trust.  You'll be glad, by and large,
that you **don't** have to go and inspect the internal :lname:`C` data
structures with :program:`gdb` as it becomes increasingly painful.

Line Orientation
================

I've made an executive decision that it is a requirement that we be
able to construct shell-like sequences of commands in a line-oriented
fashion:

.. code-block:: idio

   ls -l file

This line-orientation *does* create an exception to the reader's input
and (printed) output form being the same.  The *absence* of opening
and closing parenthesis is no hindrance to the reader constructing a
list so that line is treated as though it was:

.. code-block:: idio

   (ls -l file)

In that sense, the :lname:`Idio` reader is normalising the source code
into standard :lname:`Lisp`\ y forms.

As it stands there is no statement separator so one line is one
command.  This leads to the slightly unexpected failure of:

.. code-block:: idio

   (ls) (echo 3)

which you might think is two commands but in practice this will be
interpreted as:

.. parsed-literal::

   *func* *arg*

and the fact that both :samp:`{func}` and :samp:`{arg}` are Unix
commands makes no difference.

In the first instance, the ``ls`` will print the current directory
listing to *stdout* and the value returned from the successful
execution of an external command will be ``#t``.  Then we'll run the
second command ``echo 3`` which will similarly print ``3`` to *stdout*
and again the value returned from the successful execution will be
``#t``.

We have now successfully evaluated :samp:`{func}` and :samp:`{arg}`
giving the form we want to invoke as:

.. parsed-literal::

   (*#t* *#t*)

and we'll get some words of admonition about failing to invoke the
value in functional position, ``#t``.

Remember, the reason this is happening is firstly, because we're
taking the whole line as one command and secondly, the evaluator is
dutifully evaluating all the elements of the form to get the values to
pass to the function.  Just like we'd expect:

.. code-block:: idio

   (+ ( 2 * 3) (6 / 2))
   
to have its arguments evaluated into :samp:`({+} {6} {3})` before
invoking the (presumably) addition function.

Supplementary Processing
========================

The actual reading of source code is a little bit more complicated
than it needs to be because of a few things:

#. we need to read a *line* at a time -- not an expression at a time
   like regular :lname:`Lisp`\ s

#. we need to handle (potentially) changing quasiquoting characters in
   templates

#. we want to record the source code expression (and handle and line
   number)

A Line at a Time
----------------

Normal :lname:`Lisp`\ s will read an expression at a time: an atom
(number, symbol, string, etc.) or a list (meaning that they/we(!) will
need to recurse to read the individual atoms in the list).  And, to be
honest, that's about all the reading you need to do for a
:lname:`Lisp`.  It's *really* easy (for limited values of easy).

However, we want to read a line at a time which means going back for
more until we hit the end of the line (or the end of the file).  Hmm,
how do we signal *that*?  Well, the obvious thing to do is have a set
of :lname:`Idio` values which cover those bases.  We can return an
*eol* or an *eof* :lname:`Idio` value as the expression we've just
"read" and the next guy up the chain can make a decision themselves.

The "guy up the chain" needs to maintain a list of the expressions
read so far but check the expression just read for *eol* or *eof*.  In
this way we get an implicit list generated from :samp:`{this} {that}
{the-other}` rather than having to explicitly delimit it with
parentheses as in :samp:`({this} {that} {the-other})`.

Of course, if we really *did* delimit with parentheses, :samp:`({this}
{that} {the-other})`, then we've just read in a list.  *Boom!* Job
done.

    Had we been in regular :lname:`Lisp`-mode then the previous
    example of ``(ls) (echo 3)`` would have done what you probably
    expected, to first read then execute the first expression, the
    list ``(ls)`` (resulting in a directory listing being printed)
    then it would have read and executed the second expression, the
    list ``(echo 3)`` (dutifully printing 3 to *stdout*).

The implementation of this is not *Art*, I have to say and my
:lname:`C` naming scheme has let me down.  It needs revisiting.  (At
the time it was "Tack something on the end to make it different."
We've all been there....)

Quasiquotation Interpolation Characters
---------------------------------------

.. sidebox::

   There are moments when you think... "Yes!  *Genius!*"

   ...before realising how crushingly obvious it was.

This is surprisingly easy, instead of the reader presuming to use
``$``, ``@`` (for ``$@``) and ``'`` in their various roles we simply
pass an array of said characters and check the current characters
against a slot in the array.

When we reach the start of a template, say, ``#T{...}``, we can scan
the characters after the ``T`` and before the ``{`` and update a copy
of the incoming interpolation character array as appropriate before
recursing into reading the block (between the ``{`` and the
corresponding ``}``) with the (possibly new) set of interpolation
characters.

A minor fault is that anything printing a template doesn't know what
the interpolation characters used were so it defaults to the standard
:lname:`Idio` ones.

Source Code Expressions
-----------------------

I confess I have found no insight into how other systems handle this
so I've cobbled together something of my own which has, um, slowed
things down a bit.

The essence is simple, the reader reads from a handle and the handle
is aware of its own name and the current line number in the handle so,
at the start of reading an expression, why don't we stash that away?

*That* bit is easy -- noting that we get results for over a hundred
thousand expressions in the simplest startup and shutdown.  But how do
we get it back again?

Hmm.  One thing that is useful to remember is that every *pair* in the
system is unique -- the head and tail might refer to the same things
as other pairs (or arrays or hash tables or ...) but the pair *itself*
is a unique allocation in memory.  Throughout the following remember
that so long as we continue to *refer* to this (unique allocation in
memory) pair -- as opposed to *copying* it -- then we are always
referring [sic] to the same thing.

This being a :lname:`Lisp`\ y language, you can use pairs as the keys
into a hash table.  If you're thinking what I'm thinking (*hey, I*
have *just given you the two clues*) then we can put these two
together.  For each expression we read in we can have recorded the
handle and line which, together with the expression itself, can become
a "lexical object."

In practice this is a regular :lname:`Idio` structure with fields:
(the handle's) ``name``, ``line``, (handle) ``pos`` and ``expr``
(again, just in case).  Given that we intend that the key to the
"source properties" hash table be ``expr`` then it's not a good idea
to have ``expr`` somewhere in the value meaning we will have 1) a
circular data structure and 2) therefore some difficulty garbage
collecting it.  To fix that the source properties hash table is
flagged as having weak keys.  When ``expr`` goes out of scope then we
can reap the value that was once associated with it.

So far, so good.  We can look up an expression in the source
properties hash and get back where we read it in from.  What we need
to do next with the expression is *remember it*.  Easier said than
done.

The reader only needs to return the expression to the evaluator (not
the full lexical object) but the evaluator needs to ensure that the
expression is safely carried through all the processing such that it
can be embedded in the byte code.

The first part of that means that all the evaluator function calls
need to carry a ``src`` expression object and switch to a more
appropriate src expression when, say, processing the argument
expressions of a function call.

The second part means that it has to pass the source expression onto
the code generator.  The code generator needs to install the
expression as a constant in order that it can subsequently embed a
``SRC-EXPR`` and integer argument into the byte code which the VM can
process by assigning the integer into the *expr* register.

Should the code generate a failure when running then it is possible to
use the expression register to look up the expression in the constants
tables and then use the expression to look up the "lexical object" in
the source properties hash table.  Which sounds a bit of a run-around
but you only do it when your code crashes.  Which is never, right?

In the meanwhile, my ``(ls) (echo 3)`` code generated a message:

.. code-block:: console

   '((ls) (echo 3))' at *stdin*:line 5: ^rt-function-error: cannot invoke constant type: '(#t)'

which gives me some clues as to where to look.

You may have noticed that this works for expressions that are pairs
(lists!) but not non-pairs, ie. strings, numbers etc..  There's two
things here:

#. only working for lists means that we're only tagging function
   calls, ie. statements, rather than the elements of statements

   At the end of the day, the code is simply one long list [sic] of
   function calls so we've got the basics.

#. an error in *reading* an atom from the source code will trigger a
   ``^read-error`` and the reader will flag up the problem there and
   then -- including handle and line number

The point about stashing the source code's source location away is for
when we come to *run* the code, potentially a long time later, we can
indicate to the user where in the source the fault lies.

General Process
===============

By and large the general process to read a line is quite simple:

#. we read a number of individual expressions until we get an
   end-of-line or an end-of-file signal

#. we can process the list for operators

#. done

(I felt I had to add a third step just to give it some credibility.)

Expressions
-----------

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
a bit of whitespace as I've noted before.  If you're not using it then
you're creating an interesting symbol.

This means that some words (from a reader perspective) are not a lean
form of arithmetic but are actual symbols (and possibly variables):

.. code-block:: console

   Idio> 3pi/4
   #i2.35619449019234491e+0

``3pi/4`` is a symbol and is, perhaps not surprisingly, ``3 * pi / 4``
but now as a handy variable.

Word Separators
^^^^^^^^^^^^^^^

The inverse of expressions, perhaps, but it's useful to know what
prevents as word consuming the entire rest of the file.

Whitespace
""""""""""

An obvious word break is whitespace although it's currently being
implemented with questionable adherence to whitespace.

In the first instance, born in the ASCII/Latin-1 era, whitespace was
in two parts:

* SPACE and TAB for gaps between words

* NEWLINE and CARRIAGE RETURN for ends of line -- which should cover
  the myriad of Unix, Mac OS and Windows variants

.. sidebox::

   I think I've only seen FORM FEED of those two in the wild and only
   then as ``^L`` in Emacs Lisp files.

However, even in those simplistic times it still didn't honour ASCII's
VERTICAL TAB or FORM FEED.

So, a poor start and remains in exactly the same poor position until I
can make a decision about whether to go all in with Unicode category
types.

Bracketing Characters
"""""""""""""""""""""

For parentheses, I would normally go with just a right parenthesis,
``)``, causing a word break so that the last expressing in a list can
butt up it: ``(this that)``.

However, I have also (followed others and) used left parenthesis,
``(`` as a word break meaning that you cannot have ``foo(bar`` as a
symbol.  It'll be too confusing in ``(this foo(bar)``.

Similarly, for the array constructor ``#[...]`` the right bracket,
``]``, is a word break allowing the words inside to butt up against
it.

Currently, left bracket, ``[`` *is* allowed in symbols.  Maybe I
should revisit that.

Currently, both left and right brace, ``{`` and ``}``, are allowed in
words.  Hmm.

Double Quote
""""""""""""

I must have has a reason for this.  Perhaps sanity to avoid symbols
like ``foo"bar``.

Semicolon
"""""""""

This is the line-comment character, everything after it is discarded
to the end of the line.

If you're really determined you can escape the semicolon in the
source: ``a\;b`` will create a symbol called ``a;b``.

Dot
"""

You can't have ``.`` in a word.  Unless it's a number....

``.`` is used for the ``value-index`` operator so we can say
:samp:`{thing}.{field}` and ``value-index`` will figure out the right
form of access of :samp:`{field}` within :samp:`{thing}`.

Not a word Break
^^^^^^^^^^^^^^^^

These are, maybe unexpectedly, not (currently) word breaks.

The pair separator, ``&``.  You must currently separate the head and
tail expressions from ``&`` with whitespace.  That allows ``a&b`` as a
valid symbol.

.. sidebox::

   I suppose this allows you to have a sequence of ``a``, ``a'`` and
   ``a''`` if it pleases you so.


Interpolation characters which have no function other than as the
first character of a word in which case they are handled separately
anyway.  ``a$b``, ``a@b`` and ``a'b`` (assuming the default
interpolation characters) are all valid symbols.



Lists
^^^^^

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

