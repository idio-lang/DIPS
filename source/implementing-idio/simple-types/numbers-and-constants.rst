.. include:: ../../global.rst

*********************
Numbers and Constants
*********************

We will be using numbers and constants quite a bit in :lname:`Idio`.
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

.. code-block:: idio-console

   xxxxxxxx xxxxxxxx xxxxxxxx xxxxxx00

A pointer to properly allocated value (ie. an ``IDIO``) will always
end ``00``.  That suggests there's room for us to be a bit sneaky for
some kinds of types.

Suppose we were to artificially craft a "pointer" that used one of the
other three bit combinations, other than ``00``, then we could use the
remaining 30 bits for our value.

It would require that everywhere where we previously performed some
test against a value's ``o->type`` we would now have to test those
bottom two bits first, handle the three special cases and otherwise
fall back to the generic ``o->type``.

Numbers
=======

Let's try an example.  Suppose we were to use ``01`` for integers,
hold that, for signed integers.  This gives us 30 bits for the
integer, less one bit for the sign, leaving us with 2\ :sup:`29` bits.
That's a pretty big number, ±536 million or so.

Assuming twos-complement, 1 and -1 would be:

.. code-block:: idio-console

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

.. aside::

   It still works, mind, they must be used to people abusing the
   system.

Actually, that ``>> 2`` will extract a complaint about ``arithmetic
right shift`` from some :lname:`C` compilers as it makes an assumption
that the top (sign) bit will remain the same (rather than be set to 0,
say).

This is called a "tagged" type -- we're using the bottom two bits as a
tag -- and, here, the whole thing for integers, is called a fixed
width number or *fixnum*.

We don't want bit-twiddle ourselves all day so there's a couple of
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

fixnum.c
--------

:file:`fixnum.c` hosts not just the basic fixnum arithmetic but also
is the front end for most arithmetic meaning it has to decide whether
any of the numbers being processed are bignums and promote all the
fixnums to bignums if that is the case.

There is also the :lname:`Scheme`-ish arithmetic style that, say,
``+`` for addition is not a binary function as in :lname:`C`,
:samp:`a + b`, but is an :term:`n-ary` function, here, meaning it
takes zero or more arguments.

Fixnum arithmetic can overflow the limits of a fixnum,
:samp:`FIXNUM-MAX + 1` is an obvious case, resulting in a shift to
bignum arithmetic.

.. code-block:: idio-console

   Idio> bignum? (FIXNUM-MAX + 1)
   #t

Implementation
^^^^^^^^^^^^^^

Most of the arithmetic operations can be grouped and take a similar
structure which can be abstracted into (rather large) :lname:`C`
macros.

For *fixnum* comparisons there is a
``IDIO_DEFINE_FIXNUM_CMP_PRIMITIVE_(cname,cmp)`` which takes a
:lname:`C` name snippet, :samp:`{cname}`, and a :lname:`C` comparison
operator, :samp:`{cmp}` and generates a function.

``IDIO_DEFINE_FIXNUM_CMP_PRIMITIVE_(le,<=)`` will generate a
less-than-or-equal-to function called :samp:`idio_fixnum_primitive_le`
wielding the :lname:`C` ``<=`` operator.

These are called in the next group of macros to provide fixnum
variants of the bignum hand-coded :samp:`idio_bignum_primitive_le` and
friends.

.. rst-class:: center

\*

For general arithmetic or comparisons we need to check for any bignums
in the argument list and call either the fixnum or the bignum variant
of the arithmetic implementation.  These checks are generic(-ish) and
so are encapsulated in :lname:`C` macros.

Division is *always* converted to bignums -- let's not waste any time!

In all cases we are creating the (front-end) *primitive* and
correspondingly we need to specific the :lname:`Idio` name, a
:lname:`C` name snippet, an arity and varargs.  In fact our arithmetic
macro is simply generating a regular :samp:`IDIO_DEFINE_PRIMITIVE{x}`
macro.

We've just said that our :lname:`Scheme`-ish arithmetic is n-ary but
there is a subtle twist in that addition and multiplication can work
with no arguments (resulting in 0 and 1, respectively) but subtraction
and division require at least one argument.

There's a bit more subtlety still in that:

* for one argument there is an implied default value: :samp:`(+ {n})`
  is implicitly :samp:`0 + {n}`, ditto subtraction, and :samp:`(/
  {n})` is implicitly :samp:`1 / {n}`, ditto multiplication

* for subtraction and division with more than one argument the first
  is operated on by the rest: :samp:`(- {m} {n})` is :samp:`{m} - {n}`
  and :samp:`(/ {m} {n})` is :samp:`{m} / {n}`

  In other words, the implied default value is not used.

``IDIO_DEFINE_ARITHMETIC_PRIMITIVE0V(name,cname)`` is used as
``IDIO_DEFINE_ARITHMETIC_PRIMITIVE0V ("+", add)`` creating an
:lname:`Idio` primitive called ``+`` which will call
``idio_defprimitive_add()``.

Similarly ``IDIO_DEFINE_ARITHMETIC_CMP_PRIMITIVE1V(name,cname)`` is
used as ``IDIO_DEFINE_ARITHMETIC_CMP_PRIMITIVE1V ("le", le)`` for an
:lname:`Idio` primitive ``le`` calling ``idio_defprimitive_le``.

.. _constants:

Constants
=========

Back to other possible limited width simple types.  We know we have a
bunch of constants, in fact, it'll transpire we have half-a-dozen or
so groups of constants (think: enumerated values) one of which,
Unicode, we know uses 21 bits.

Quick bit of maths... 30 bits of space on a 32-bit system, minus 21
bits for Unicode, say, gives us 9 bits worth of different constant
types.  Hmm, I'm not sure we have 512 different constant types or,
rather more importantly, even want to consider having 512 different
types of constants.  Far too many to remember!

Let's flip the maths around and suggest we have 3 bits of constant
types (up to 8, then) meaning each constant type could have up to 27
bits worth of space.  Definitely room for Unicode's 21 bits in one and
I fancy we could squeeze our trio of regular constants, ``#t``, ``#f``
and ``#n`` into another.

And if it turns out that 8 different constant types isn't enough then
we can revisit this and make it 16 or 32 or ... and still have room
for what is almost certainly our biggest group of constants, Unicode.

Let's try that, then, with ``10`` as the tag and ``ccc`` being our 3
bits of "constant type differentiator":

.. code-block:: idio-console

   xxxxxxxx xxxxxxxx xxxxxxxx xxxccc10

In practice, for :lname:`Idio` constants, being the first out of the
block, we'll use ``000`` for ``ccc`` giving us a combined suffix of
``00010``.  That leaves us to define some :lname:`Idio` constants:

.. code-block:: c
   :caption: idio.h
   
   #define idio_S_nil		(0 << 5) | 0x00010
   #define idio_S_true		(4 << 5) | 0x00010
   #define idio_S_false		(5 << 5) | 0x00010

The other constant types are (``ccc``):

* (``001``) reader tokens -- like lexer tokens, they're for flagging
  up states and it's certainly easier to pass them around as full
  ``IDIO`` values.

* (``010``) intermediate code tokens -- *stuff* -- we'll get there!

* (``011``) characters -- historic :lname:`Scheme`-style characters
  which were essentially ASCII_/ISO8859_ or :lname:`C`-style bytes,
  now deprecated

* (``100``) Unicode code points -- of course!

There are some macros for the above but they've become slightly
involved as I've abstracted out the number of bits and the shifts and
so on.

.. rst-class:: center

---

We've still room for a third tagged type.  I've not settled on one,
though.  I'm partial to a *flonum* type.  Yes, a floating point number
squeezed into 30 bits.  `IEEE 754`_, or something, with small mantissa
and exponent.  I don't use floating point enough to warrant the effort
especially when what little floating point I use is more than
adequately handled by :ref:`bignums`.  One day.

In the meanwhile, the tag is reserved by the
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
:ref:`bignums` -- consider that we can't differentiate between ``3``
and ``3.14`` based on the ``3`` until we've read the whole number in
completely.  Therefore *all* numbers are read as bignums and
"downgraded" as appropriate.

We don't read in many constants -- most of them are internally
generated by the reader or evaluator etc..  We do read in a few though
and they all start with ``#``.

The reader has a large ``switch`` statement which, having found a
``#``, can ``case`` the next byte read:

.. csv-table:: Reading constants and characters
   :header: "byte", "result"
   :widths: auto
   :align: left

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
hexadecimal number reading code as ``#xhhhh`` does, see `Non-base-10
numbers
<http://dips.office.soho/implementing-idio/simple-types/bignums.html#non-base-10-numbers>`_)
and creates a Unicode code point from the number: ``#U+0127`` creates
the same U+0127 Unicode code point as ``#\ħ`` above.

Writing
=======

Writing *fixnums* is quite easy as we know they are ``intptr_t`` (as
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

.. code-block:: idio-console

   Idio> n := 17
   Idio> format "%b\n" n
   "10001\n"

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

Operations
==========

Numbers
-------

:samp:`fixnum? {value}`

      is :samp:`{value}` a fixnum

:samp:`integer? {value}`

      is :samp:`{value}` a fixnum or an integer bignum

:samp:`number? {value}`

      is :samp:`{value}` a fixnum or a bignum

:samp:`floor {number}`

      the `floor
      <https://en.wikipedia.org/wiki/Floor_and_ceiling_functions>`_ of
      a number is the integral value less than or equal to the number

:samp:`remainder {number}`

      the remainder of a number is the value minus the floor of the
      number

:samp:`quotient {a} {b}`

      the quotient of :samp:`{a}` and :samp:`{b}` is :samp:`{a} / {b}`

:samp:`le {n} [...]`
      
:samp:`lt {n} [...]`

:samp:`eq {n} [...]`
      
:samp:`ge {n} [...]`
      
:samp:`gt {n} [...]`

      perform numeric comparisons between the arguments (a minimum of
      one) and return ``#f`` if any adjacent pair of arguments fails
      the comparison

      :samp:`lt {n1} {n2} {n3} {n4}` is equivalent to:

      .. code-block:: idio

	 (and (lt n1 n2)
	      (lt n2 n3)
	      (lt n3 n4))

      The default result is ``#t``.

      Notice that the function names are alphabetic rather than the
      traditional arithmetic symbols, ``<=``, ``<``, ``==``, ``>=``
      and ``>``.  This is to maintain consistency and avoid semantic
      clashes with our (preferred) use of angle brackets for IO
      redirection.

      You may recall that :lname:`Bash`'s ``[[`` builtin command uses
      the same operators: ``-le``, ``-lt``, ``-eq``, ``-ge`` and
      ``-gt``.

      ``eq``, this numeric comparison, adds to the naming confusion
      with ``eq?``, ``eqv?`` and ``equal?``.

:samp:`+ {n} [...]`
      
:samp:`- {n} [...]`

:samp:`* {n} [...]`
      
:samp:`/ {n} [...]`

      perform the usual arithmetic functions of add, subtract,
      multiply and divide

:samp:`integer->char {integer}`

      [deprecated]

      convert an integer to a character -- limited to the range of fixnums

:samp:`integer->unicode {integer}`

      convert an integer to a Unicode code point      


Constants
---------

By and large there are no specific operations that you can perform on
a constant.

However, see :ref:`Unicode code point operations` for special cases.

.. include:: ../../commit.rst

