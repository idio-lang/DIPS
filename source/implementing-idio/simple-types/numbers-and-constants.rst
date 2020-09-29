.. include:: ../../global.rst

**********************
Integers and Constants
**********************

We will be using integers and constants quite a bit in :lname:`Idio`.
Do we really want to create a (relatively) enormous data structure to
house a 32-bit integer?  Or for ``#t``, ``#f`` and ``#n`` -- the only
constants I can think of?  Seems a bit wasteful.

Do we need 32-bit integers anyway?  I suppose I've written scripts
that have looped around several thousand times.  I keep reading that
there's a million or so Unicode code points -- 2\ :sup:`21` to be
precise -- if we can handle that "cheaply" then we might be onto
something.

We can, of course, albeit we rely on an observation about modern
:lname:`C` compilers in that they allocate memory on the heap on
machine word boundaries.  A 32-bit machine will allocate memory on a 4
byte boundary and a 64-bit machine on an 8 byte boundary.

(We'll generally deal with 32-bit examples and reference 64-bit
systems where they differ.)

If everything is allocated on a 4 byte boundary then the last two bits
(three bits for 64-bit) are *always* zero:

.. code-block:: console

   xxxxxxxx xxxxxxxx xxxxxxxx xxxxxx00

A properly allocated value's pointer (ie. an ``IDIO``) will always end
``00``.  That suggests there's room for us to be a bit sneaky for some
kinds of types.

Suppose we were to artificially craft a "pointer" that used one of the
other three bit combinations then we could use the remaining 30 bits
for our value.

It would require that everywhere where we previously performed some
test against a value's ``o->type`` we would now have to test those
bottom two bits first, handle the three special cases and otherwise
fall back to the generic ``o->type``.

Let's try an example.  Suppose we were to use ``01`` for integers,
hold that, for signed integers.  This gives us 30 bits for the
integer, less one bit for the sign, leaving us with 2\ :sup:`29` bits.
That's a pretty big number, ±536 million or so.

Assuming two-complement, 1 and -1 would be:

.. code-block:: console

   00000000 00000000 00000000 00000101

   11111111 11111111 11111111 11111101

from which we could squish an integer, ``i`` into an ``IDIO``
"pointer":

.. code-block:: c

   int i = 1;
   IDIO o = (i << 2) | 0x01;

and retrieve it with:

.. code-block:: c

   IDIO o = ...;
   int i = ((intptr_t) o) >> 2;

Actually, that ``>> 2`` will extract a complaint about ``arithmetic
right shift`` from some :lname:`C` compilers as it makes an assumption
that the top (sign) bit will remain the same (rather than be set to 0,
say).  It still works, mind.

This is called a "tagged" type -- we're using the bottom two bits as a
tag -- and, here, the whole thing for integers, is called a fixed
width number or *fixnum*.

We don't want bit-fiddle ourselves all day so there's a couple of
:lname:`C` macros to help:

.. code-block:: c

   int i1 = 1;
   IDIO o = IDIO_FIXNUM (i1);
   
   int i2 = IDIO_FIXNUM_VAL (o);


The elephant in the room for fixnums is what happens if I want... ±53\
**7** million (*bwah hah hah!*)?  No problem, we'll use :ref:`bignums`
instead.  We need to handle fixnum to/from bignum conversions but
that's OK.

In the meanwhile we have a relatively simple mechanism for handling a
quite large range of numbers.  Plenty for most shell-ish purposes.

.. rst-class:: center

---

Back to other possible limited width simple types.  We know we have a
bunch of constants, in fact, it'll transpire we have half-a-dozen or
so groups of constants (think: enumerated values) one of which,
Unicode, we know uses 21 bits.

Quick bit of maths... 30 bits of space, minus 21 bits for Unicode,
say, gives us 9 bits worth of different constant types.  Hmm, I'm not
sure we have 512 different constant types or, rather more importantly,
even want to consider having 512 different types of constants.  Far
too many to remember!

Let's flip the maths around and suggest we have 3 bits of constant
types (up to 8, then) meaning each constant type could have up to 27
bits worth of space.  Definitely room for Unicode's 21 bits in one and
I fancy we could squeeze our trio of ``#t``, ``#f`` and ``#n`` into
another.

Let's try that, then, with ``10`` as the tag and ``ccc`` being our 3
bits of "constant type differentiator":

.. code-block:: console

   xxxxxxxx xxxxxxxx xxxxxxxx xxxccc10

In practice, for :lname:`Idio` constants, being the first out of the
block, we'll use ``000`` for ``ccc`` giving us a combined suffix of
``00010``.  That leaves us to define some :lname:`Idio` constants:

.. code-block:: c
   :caption: idio.h
   
   #define idio_S_nil		(0 << 5) | 0x00010
   #define idio_S_true		(4 << 5) | 0x00010
   #define idio_S_false		(5 << 5) | 0x00010

The other constant types are:

* reader tokens -- like lexer tokens, they're for flagging up states
  and it's certainly easier to pass them around as full ``IDIO``
  values.

* intermediate code tokens -- *stuff* -- we'll get there!

* characters -- historic :lname:`Scheme`-style characters which were
  essentially ASCII_/ISO8859_ or :lname:`C`-style bytes

* Unicode code points -- of course!

There are some macros for the above but they've become slightly
involved as I've abstracted out the number of bits and the shifts and
so on.

.. rst-class:: center

---

We've still room for a third type.  I've not settled on one, though.
I'm partial to a *flonum* type.  Yes, a floating point number squeezed
into 30 bits.  `IEEE 754`_, or something, with small mantissa and
exponent.  I don't use floating point enough to warrant the effort
especially when what little floating point I use is more than
adequately handled by :ref:`bignums`.  One day.

In the meanwhile, the space is reserved by the
``IDIO_PLACEHOLDER_TYPE``.

64-bit Virtual Address Space
============================

Whilst we are having flights of fancy with fake pointers, no current
CPU architecture lets you address more than 48 bits of physical
address space regardless of whether you could afford that much RAM.
`Virtual Address space
<https://en.wikipedia.org/wiki/X86-64#Virtual_address_space_details>`_
shows a large splodge of literally inaccessible memory.

In principle that could be :strike:`ab`\ used in a similar way.  The
advantage of which is that maths might be easier to manage as there's
no shifting required when you mask-off the tag.

Reading
=======

Reading numbers is a bit more awkward so we'll leave that to
:ref:`bignums` -- imagine that we can't differentiate between ``3``
and ``3.14`` based on the ``3`` until we've read it in completely in
which case *all* numbers are read as bignums and "downgraded" as
appropriate.

We don't read in many constants -- most of them are internally
generated by the reader or evaluator etc..  We do read in a few though
and they all start with ``#``.

The reader has a large ``switch`` statement which, having found a
``#``, can ``case`` the next byte read:

.. csv-table::
   :header: "byte", "result"

   ``n``, ``idio_S_nil``
   ``t``, ``idio_S_true``
   ``f``, ``idio_S_false``
   ``\``, ``idio_read_character(... IDIO_READ_CHARACTER_EXTENDED)``
   ``U``, ``idio_read_unicode(...)``

``idio_read_character(..., int kind)`` can now do some decision making
of its own.  It reads the next (UTF-8) character (don't forget ASCII
characters are valid UTF-8 characters):

* If ``kind`` was ``IDIO_READ_CHARACTER_SIMPLE`` then ``#\X`` has
  ``X`` converted into a Unicode code point: ``#\ħ`` will result in
  the Unicode code point U+0127 (LATIN SMALL LETTER H WITH STROKE).

* Otherwise if the character was ``{`` then we go on to read in a
  :lname:`Scheme`-ish *named character*, eg. ``#\{newline}`` -- aka
  U+000A or :lname:`C`'s ``'\n'``.

  There isn't a particularly comprehensive set of named characters
  (think: a few test cases) but since we construct our Unicode tables
  from Unicode source material there's nothing to stop us creating the
  complete set of named Unicode characters such that ``#\{LATIN SMALL
  LETTER H WITH STROKE}`` gets us U+0127.

* else it was a Unicode code point (again)

  (Reading that back it could do with some refactoring!)

``idio_read_unicode()`` checks that the next character is ``+`` then
reads hexadecimal characters (technically it calls the same generic
hexadecimal number reading code as ``#xhhhh`` does) and creates a
Unicode code point from the number: ``#U+0127`` creates the same
U+0127 Unicode code point as ``#\ħ`` above.

Writing
=======

Writing fixnums is quite easy as we know they are ``intptr_t`` (as
they fit inside an ``IDIO`` "pointer") so we can print them back out
with ``printf ("%td", IDIO_FIXNUM_VAL (o))``.

Except that's a bit too easy and a bit too restrictive.  In
particular, that will print out a decimal number.  What if we want a
hexadecimal or octal number?

Here, the code that converts :lname:`Idio` types to strings can query
the system as to whether the ``idio-print-conversion-format`` symbol
has been set and, assuming it is one of the usual suspects
(``Xbdox``), print it out.

``b``?  Yes, of course.  Generate the binary representation of our
fixnum:

.. code-block:: console

   Idio> n := 17
   Idio> format "%b\n" n
   "10001\n"

That turns out to be quite handy for :ref:`bitsets`.

For the constants we can capture the individual values and return
specific strings:

.. code-block:: c
   :caption: util.c

   case IDIO_TYPE_CONSTANT_IDIO_MARK:
   {
       intptr_t v = IDIO_CONSTANT_TOKEN_VAL (o);

       switch (v) {
           case IDIO_CONSTANT_NIL:    t = "#n";        break;
	   case IDIO_CONSTANT_UNDEF:  t = "#<undef>";  break;
	   case IDIO_CONSTANT_UNSPEC: t = "#<unspec>"; break;
	   case IDIO_CONSTANT_EOF:    t = "#<eof>";    break;
	   case IDIO_CONSTANT_TRUE:   t = "#t";        break;
	   case IDIO_CONSTANT_FALSE:  t = "#f";        break;
	   case IDIO_CONSTANT_VOID:   t = "#<void>";   break;
	   case IDIO_CONSTANT_NAN:    t = "#<NaN>";    break;

where ``t`` is a temporary variable to help calculate the final result
(which is complicated by Unicode).  You can also see other internal
values getting a rendering that is quite readable to us programmers
but "impossible" for the reader to consume (``#<`` is specifically
invalid for this reason).

