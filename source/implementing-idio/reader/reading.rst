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
like, uh, the source code format.

So, ``(foo a b)``, being a list of three elements, that is, a linked
list of three *pairs*, has whatever internal format it has in
:lname:`C`, our implementation language.  If I use the :lname:`C`
debugger, say, :program:`gdb`, I can painfully work my way through the
cascading hierarchy of data structures and can eventually satisfy
myself that it is, indeed, a linked list of three pairs with the head
elements pointing at three different symbols (which themselves have
some internal format).

The obvious thing to do instead is to ask the :lname:`Idio` engine to
print out this internal format which will give us... ``(foo a b)`` --
which might leave us scratching our heads as to whether we've actually
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
unsettling as that's not the format I would have written it in.

Anyway the point of this diversion is that there's going to be a
degree of confusion when we talk about reading something in and then
describing the internal format using its printed representation which
is, usually, *exactly the same* as the source code format.

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
giving the values for the form we want to invoke:

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
invoking the addition function.

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
the time the naming scheme was "Tack something on the end to make it
different."  I think we've all been there....)

Quasiquotation Interpolation Characters
---------------------------------------

.. sidebox::

   There are moments when you think, "Yes!  *Genius!*"

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

The quasi-quotation characters are:

.. csv-table:: Quasi-quotation characters
   :widths: auto
   :align: left

   unquote, ``$``
   unquote-splicing, ``@`` -- as in ``$@``
   quote, ``'``
   escape, :literal:`\\`

In effect, ``#T{...}`` is really ``#T$@'\{...}``.

If you don't want to change one of the earlier ones, say you want to
change the *quotation* character but leave the *unquote* and
*unquote-splicing* characters alone, use ``.`` so that ``#T..!{...}``
changes the quotation character to ``!`` for the duration of the
expression.  This may be useful when you are an embedded template.

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

*That* bit is easy -- noting that we get results for tens of thousands
of expressions in the simplest startup and shutdown.  But how do we
get it back again?

Hmm.  One thing that is useful to remember is that every *pair* in the
system is unique -- the head and tail might refer to the same things
as other pairs (or arrays or hash tables or ...) but the pair *itself*
is a unique allocation in memory.  Throughout the following remember
that so long as we continue to *refer* to this (unique allocation in
memory) pair -- as opposed to *copying* it -- then we are always
referring [sic] to the same thing.

This being a :lname:`Lisp`\ y language, you can use pairs as the keys
into a hash table.  If you're thinking what I'm thinking then we can
put these two together.  For each expression we read in we can have
recorded the handle and line which, together with the expression
itself, can become a "lexical object."

In practice this lexical object is a regular :lname:`Idio` structure
with fields: (the handle's) ``name``, ``line``, (handle) ``pos`` and
``expr`` (again, just in case -- we're bound to lose it!).  Given that
we intend that the key to the "source properties" hash table be
``expr`` (at least the pair at the root of ``expr``) then it's not a
good idea to have ``expr`` somewhere in the value, meaning we will
have 1) a circular data structure and 2) therefore some difficulty
garbage collecting it.  To fix that the source properties hash table
is flagged as having weak keys.  When ``expr`` goes out of scope then
we can reap the value that was once associated with it.

So far, so good.  We can look up an expression in the source
properties hash and get back where we read it in from.  What we need
to do next with the expression is *remember it*.  Bah!  "Remember"
isn't quite the right word.  We want to ensure that, at any time, we
have access to the currently executing expression.  Easier said than
done.

The reader only needs to return the expression to the evaluator (not
the full lexical object) but the evaluator needs to ensure that the
expression is safely carried through all the processing such that it
can be embedded in the byte code.

The first part of that means that all the evaluator function calls
need to carry a ``src`` expression object and switch to a more
appropriate src expression when, say, processing the argument
expressions of a function call.

In other words, the original source code might say:

.. code-block:: idio

   (1 / a) + (1 / b)

but we want the VM to be aware that it is in either ``(1 / a)`` or
``(1 / b)`` when we inevitably discover that one of ``a`` or ``b`` is
zero.  Of course, in this instance, all (seven!) "evaluable
expressions" are on the same line but you get the idea.

The second part means that it has to pass the source expression onto
the code generator.  The code generator needs to install the
expression as a constant in order that it can subsequently embed a
``SRC-EXPR`` opcode and integer argument into the byte code which the
VM can process by assigning the integer into the *expr* register.

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
   calls, ie. statements, rather than the (atomic) elements of
   statements

   At the end of the day, the code is simply one long list [sic] of
   function calls so we've got the basics.

#. an error in *reading* an atom from the source code will trigger a
   ``^read-error`` from the reader -- no waiting for run-time -- and
   the reader will flag up the problem there and then -- including
   handle and line number

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

(I felt I had to add a third step just to give the process some
substance.)

Unicode
=======

By and large, the reader should be reading Unicode code points from
the UTF-8 encoded source file.

*Something* has to read bytes at a time in order to perform the UTF-8
decoding and that's handled in ``idio_read_character_int()`` -- where
``_int`` is for internal as it returns an ``idio_unicode_t``, a
:lname:`C` Unicode-ish type that also handles ``EOF`` as opposed to
something returning an :lname:`Idio` Unicode code point -- a kind of
constant.

Of interest, ``idio_read_string()`` -- which is called when the first
character is ``"``, U+0022 (QUOTATION MARK) -- also reads data in a
byte at a time.  Whether that's right or wrong partly relates to how
we handle UTF-8 decoding errors.

In the meanwhile, then, you can use Unicode code points in symbols and
therefore variable names, as interpolation characters and, obviously,
in strings.

UTF-8 Decoding Failure
----------------------

There's a general problem with UTF-8 in that someone will invariably
(or maliciously) get it wrong in which case your UTF-8 decoder needs
to handle the fault gracefully.  There are no rules about handling
faults.  :ref-author:`Markus Kuhn`'s `UTF-8 Test File
<https://www.cl.cam.ac.uk/~mgk25/ucs/examples/UTF-8-test.txt>`_
contains several examples of bad UTF-8 encodings which your UTF-8
decoder should survive.

In that document he also notes the possibilities of representing
decoding failure.  The decoder should mark the failure with ``�``,
U+FFFD (REPLACEMENT CHARACTER) but it's less clear about what to do
next.  Having found one decoding failure, should you display another
replacement character to represent each subsequent incorrect byte in
the input stream (until you can resynchronise) or leave it as one
replacement character representing the failed block?

The current :lname:`Idio` code generates a replacement character for
each failed byte.

Strings
^^^^^^^

The next question is for strings.  We're simultaneously decoding UTF-8
*and* looking for the end of string marker, another ``"`` character.

If all is well then the UTF-8 decoding proceeded smoothly and the
*next* byte or code point is ``"``.  Job done.

However, if we're reading a code point at a time and the input stream
contained a valid UTF-8 multi-byte sequence byte followed by ``"`` --
an invalid byte sequence as subsequent bytes in a UTF-8 multi-byte
sequence should have the top two bits of each byte set to ``10``,
clearly not true for 0x22 -- then the UTF-8 decoder will have consumed
the ``"`` and discarded it as part of an invalid sequence.

The string construction process will continue through the input stream
looking for a "true" ``"`` to end the string -- and probably find one
at the start of the next string and we'll find ourselves toggling the
classification of strings and code.

On the other hand if we read the input stream a byte at a time then
the string will be terminated when we hit a *byte* matching ``"``
irrespective of its position in any UTF-8 multi-byte sequence.  We
will then send the collected bytes off to the UTF-8 decoder which
will, presumably, find the start of a UTF-8 multi-byte sequence
followed by no more bytes and substitute in the replacement character.

We don't know if the ``"`` following the valid UTF-8 sequence byte was
incorrect or the, seemingly valid, UTF-8 prefix byte was incorrect.

I can't see that there's a *correct* choice between the two
mechanisms: reading code points or reading bytes.  Both are functional
although I'm in favour of the byte by byte matching because:

#. the error is identified sooner -- probably, there are always
   pathological cases

#. it's the way the code was originally written for an ASCII/Latin-1
   world

There's another issue with collecting code points: we'll need to store
them in a :lname:`C` ``uint32_t`` array as we can't predict how big
any of them are going to be.  Only when we've seen them all can we
correctly size the :lname:`Idio` 1, 2 or 4 byte array string.  Most of
the time collecting ``uint32_t`` code points in the first pass is
going to be pretty inefficient.

.. include:: ../../commit.rst

