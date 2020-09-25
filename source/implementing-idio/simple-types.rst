.. include:: ../global.rst

************
Simple Types
************

The simple types, ie. types that do not reference other types, are
actually far harder to deal with as they tend to break the GC
structure model or have some quite bespoke structure.

Integers and Constants
======================

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
That's a pretty big number, Â±536 million or so.

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

This is called a "tagged" type and, here, for integers, is called a
fixed width number or *fixnum*.

We don't want bit-fiddle ourselves all day so there's a couple of
macros to help:

.. code-block:: c

   int i1 = 1;
   IDIO o = IDIO_FIXNUM (i1);
   
   int i2 = IDIO_FIXNUM_VAL (o);


The elephant in the room for fixnums is what happens if I want... Â±53\
**7** million (*bwah hah hah!*)?  No problem, we'll use :ref:`bignums`
instead.  We need to handle fixnum to/from bignum conversions but
that's OK.

In the meanwhile we have a relatively simple mechanism for handling a
quite large range of numbers.  Plenty for most shell-ish purposes.

Back to other possible limited width simple types.  We know we have a
bunch of constants, in fact, it'll transpire we have half-a-dozen or
so groups of constants one of which, Unicode, we know uses 2\
:sup:`21` bits.

Quick bit of maths... 30 bits of space, minus 21 bits for Unicode,
say, gives us 9 bits worth of different constant types.  Hmm, I'm not
sure we have 512 different constant types or, rather more importantly,
even want to consider having 512 different types of constants.  Far
too many to remember!  Let's flip the maths around and suggest we have
3 bits of constant types (up to 8, then) meaning each constant type
could have up to 27 bits worth of space.  Definitely room for
Unicode's 21 bits and I fancy we could squeeze our trio of ``#t``,
``#f`` and ``#n`` into another.

Let's try that, then, with ``10`` as the distinguishing key and
``ccc`` being our 3 bits of "constant type differentiator":

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
  and it's certainly easier to pass then around as full ``IDIO``
  values.

* intermediate code tokens -- *stuff* -- we'll get there!

* characters -- historic :lname:`Scheme`-style characters which were
  essentially ASCII_/ISO8859_ or :lname:`C`-style bytes

* Unicode code points -- of course!
   
We've still room for a third type.  I've not settled on one, though.
I'm partial to a *flonum* type.  Yes, a floating point number squeezed
into 30 bits.  `IEEE 754`_, or something, with small mantissa and
exponent.  I don't use floating point enough to warrant the effort
especially when what little floating point I use is more than
adequately handled by :ref:`bignums`.  One day.

In the meanwhile, the space is reserved by the
``IDIO_PLACEHOLDER_TYPE``.

64-bit Virtual Address Space
----------------------------

Whilst we have flights of fancy with fake pointers no current CPU
architecture lets you address more than 48 bits of physical address
space regardless of whether you could afford that much RAM.  `Virtual
Address space
<https://en.wikipedia.org/wiki/X86-64#Virtual_address_space_details>`_
shows a large splodge of literally inaccessible memory.

In principle that could be :strike:`ab`\ used in a similar way.  The
advantage of which is that maths might be easier to manage as there's
no shifting required.

Reading
-------

Reading numbers is a bit more awkward so we'll leave that to :ref:`bignums`.

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
-------

Writing fixnums is quite easy as we know they are ``intptr_t`` (as
they fit inside an ``IDIO`` "pointer") so we can print them back out
with ``printf ("%td", IDIO_FIXNUM_VAL (o))``.

Except that's a bit too easy and a bit too restrictive.  In
particular, that will print out a decimal number.  What if we want a
hexadecimal or octal number?

Here, the code that converts :lname:`Idio` types to strings can query
the system as to whether the ``idio-print-conversion-format`` symbol
has been set and, assuming it is one of the usual suspects (``Xbdox``)
print it out.

``b``?  Yes, of course.  Generate the binary representation of our
fixnum:

.. code-block:: console

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

Characters and Strings
======================

*We're not in Kansas any more, Toto!*

.. sidebox:: Actually, I did the easy :lname:`C`-style strings and
             characters initially but went back and re-wrote it all
             and can now pretend I did it properly in the first place.

There's no beating about the bush, we need to handle proper
multi-character set strings from the get go.  We don't want a
:lname:`Python` 2 vs 3 debacle.

Not for strings, anyway.

Unicode
-------

.. aside::

   Plus the disadvantage of being a native English speaker is that in
   the far flung regions of the world people want to practice their
   English and certainly don't want to listen to me insist that my
   `hovercraft is full of eels`_.

I'm not multi-lingual expert, indeed barely competent in one language,
so some of the nuance may be lost on me.  We're choosing Unicode_
(arguably ISO10646_) because of its name familiarity, even if the
actual implementation is less familiar to everyone.

The broad thrust of Unicode is to allocate a *code point*, an integer,
to the most common characters and support several combining code
points to create the rest.  From a Western Europe viewpoint, we might
have an "e acute" character, é, but also an "acute accent", ´, which
can be combined with a regular "e".

Clearly, we don't need to combine the acute accent with a regular "e"
as we already have a specific "e acute" but it does allow us to
combine it with any other character in a rare combination not
specifically covered elsewhere.  There must be rules about how
combining characters are allowed to, er, combine, to prevent an "e
acute diaeresis" (unless that *is* allowed in which case pick a better
example).

These combinations are known as *grapheme clusters* and edge towards
but do not become "characters" *per se*.  It's a grey area and you can
find plenty of discussion online as to what is and isn't a
"character".

Unicode isn't concerned with *glyphs*, the pictorial representation of
characters, either.  Even within the same *font* I can see four
different glyphs for U+0061 (LATIN SMALL LETTER A):

.. csv-table::

   a, regular
   *a*, italic
   **a**, bold
   ``a``, monospaced
   
as I pick out different visual styles.  They are all U+0061, though.

There's a much better description of some of the differences between
characters and glyphs in Unicode's `Character Encoding Model
<http://www.unicode.org/reports/tr17/#CharactersVsGlyphs>`_.

Unicode differs from ISO10646 in that although they maintain the same
set of code points the latter is effectively an extended ISO-8859,
meaning a simple list of characters, covering a lot more character
sets.  Unicode goes further and associates with each code point any
number of categories and properties and provides rules on
line-breaking, grapheme cluster boundaries, mark rendering and all
sorts of other things you didn't realise were an issue.

Don't let the simplistic nature of the Unicode_ home page concern you,
go straight to the `Unicode reports`_ and get stuck in.

Actually, don't.  Here, in :lname:`Idio`-land, we do **not** "support"
Unicode.  We use the `Unicode Character Database`_ (UCD) and some
categories and properties related to that.  We will use the "simple"
lowercase and uppercase properties to help with corresponding
character mapping functions, for example.

However, :lname:`Idio` is not concerned with correct, legal, security
or any other Unicode consideration.  :lname:`Idio` simply uses
whatever is passed to it and actions whatever the string manipulation
the user invokes.  If the result is non-conformant then so be it.
*User error.*

We *might* have to consider matters such as `Collation
<https://www.unicode.org/reports/tr10/>`_ of strings -- as we may not
be using any system-provided collation library (which you would hope
would have considered it).

We can almost certainly ignore Unicode's view on `Regular Expressions
<https://www.unicode.org/reports/tr18/>`_ as their view has been
swayed by `Perl Regular Expressions
<https://perldoc.perl.org/perlre.html>`_.  In particular, their view
on what constitutes an identifier isn't going to help us where we can
include many punctuation characters and, hopefully, regular Unicode
identifier names.

.. rst-class:: center

---

As noted previously, the code point range covers 2\ :sup:`21` bits but
not all of those are valid.  A range of values in the first 65,536 is
excluded as a side-effect of handling the UTF-16_ encoding when
Unicode finally recognised that 65,536 code points was not, in fact,
more than enough.

    That's a slightly unfair comment as 16 bits was more than enough
    for the original Unicode premise of handling scripts and
    characters *in modern use*.  That premise has changed as Unicode
    now handles any number of ancient scripts and well as :abbr:`CJK
    (Chinese, Japanese and Korean)` ideographs.

    .. aside:: By sheer coincidence I recently watched `The Secret
               History of Writing`_ in which Chinese junior school
               children recognised Oracle bone script as they learned
               to write ideographs.

	       So whilst I was going to originally jest about the
	       weird and wonderful that Unicode now encompasses I am
	       in fact chided by the superior knowledge of a six-year
	       old on the other side of the world.

    Who else is looking forward to `Oracle bone script`_?

It doesn't affect treatment of code points but it it worth
understanding that Unicode is (now) defined as 17 *planes* with each
plane being 16 bits.  Each plane is chunked up into varying sized
blocks which are allocated to various purposes.  Some very well known
purposes are historically fixed, for example ISO8859-1_, and the block
is full.  Other character sets have slots reserved within the block
for future refinements.

The first plane, plane 0, is called the `Basic Multilingual Plane
<https://en.wikipedia.org/wiki/Plane_(Unicode)#Basic_Multilingual_Plane>`_
(BMP) and is pretty much full and covers most modern languages.

Planes 1, 2 and 3 are supplementary to BMP and are filled to various
degrees.

Planes 4 through 13 are *unassigned*!

Plane 14 contains a small number of special-purpose "characters".

Planes 15 and 16 are designated for private use.  Unlike, say,
RFC1918_ Private Networks which are (usually) prevented from being
routed on the Internet, these Private Use planes are ripe for
cross-organisational conflict.  Anyone wanting to publish `Klingon
plqaD <https://en.wikipedia.org/wiki/Klingon_pIqaD>`_, Tolkien's runic
`Cirth <https://en.wikipedia.org/wiki/Cirth>`_ or Medieval texts (see
`MUFI
<https://en.wikipedia.org/wiki/Medieval_Unicode_Font_Initiative>`_) on
the same page need to coordinate block usage.  See `Private Use Areas
<https://en.wikipedia.org/wiki/Private_Use_Areas>`_ for some
information on likely coordinating publishers.

Unicode isn't a clean room setup either.  They started by saying the
first 256 block would be a straight copy of ISO-8859-1 (Latin-1) which
is handy for users of such but it doesn't really follow that it was
the best choice in the round.  There's all sorts of compromises
floating about such as the continued use of `Japanese fullwidth
forms`_ -- effectively duplicating ASCII.

.. rst-class:: center

---

The issue with handling Unicode is, um, everything.  We have an issue
about the *encoding* in use when we read Unicode in -- commonly,
UTF-8, UTF-16 or UTF-32.  We have an issue about *storing* code points
and strings (of code points) internally.  And we have to decide which
encoding to use when we emit code points and strings.

Let's try to break things down.

Code Points
-----------

Code points are (very) distinct from strings (in any encoding).  For a
code point we want to indicate which of the 2\ :sup:`21`-ish integers
we mean.  We've previously said that the reader will use something
quite close to the Unicode consortium's own stylised version:
``#U+hhhh``.

Although ``hhhh`` represents a hexadecimal number so any number of
``h``\ s which return a suitable number are good.

As discussed above, we can then stuff that code point into a specific
constant type, here, ``ccc`` is ``100`` giving us:

.. code-block:: c
   
   int uc = 0x0127;	/* LATIN SMALL LETTER H WITH STROKE */
   IDIO cp = (uc << 5) | 0x10010;

obviously, there's a couple of macros to help with that:

.. code-block:: c
   
   int uc1 = 0x0127;
   IDIO cp = IDIO_UNICODE (uc1);

   int uc2 = IDIO_UNICODE_VAL (cp);

Code points in and of themselves don't do very much.  We can do some
comparisons between them as the ``IDIO`` value is a "pointer" so you
can perform pointer comparison.  But not much else.

One thing to be aware is that there are no computational operations
you can perform on a code point.  You can't "add one" and hope/expect
to get a viable code point.  Well, you can hope/expect but good luck
with that.

We have the "simple" upper/lower-case mappings from the :term:`UCD`
although you should remember that they constitute a directed acyclic
graph:

.. graphviz::

   digraph lower {
       node [ shape=box ]
       
       "0130;LATIN CAPITAL LETTER I WITH DOT ABOVE" -> "0069;LATIN SMALL LETTER I" [ label=" lower " ];
       "0069;LATIN SMALL LETTER I" -> "0049;LATIN CAPITAL LETTER I" [ label=" upper " ];
       "0049;LATIN CAPITAL LETTER I" ->  "0069;LATIN SMALL LETTER I" [ label=" lower " ];
   }

and

.. graphviz::
   
   digraph upper {
       node [ shape=box ]

       "01C8;LATIN CAPITAL LETTER L WITH SMALL LETTER J" -> "01C7;LATIN CAPITAL LETTER LJ" [ label=" upper " ];
       "01C7;LATIN CAPITAL LETTER LJ" -> "01C9;LATIN SMALL LETTER LJ" [ label=" lower " ];
       "01C9;LATIN SMALL LETTER LJ" -> "01C7;LATIN CAPITAL LETTER LJ" [ label=" upper " ];
   }

in both cases no mapping will return you to the starting code point.

:lname:`Idio` Strings
---------------------

By which we mean arrays of code points.  *-ish*

History
^^^^^^^

If we start with, as I did, :lname:`C` strings we can get a handle on
what I was doing.

In :lname:`C` a string is an array of characters terminated by an
ASCII NUL (0x0).  That's pretty reasonable and we can do business with
that.

However, I was thinking that a lot of what we might be doing in a
shell is splitting lines of text up into words (or fields if we have
an :program:`awk` hat on).  We don't *really* want to be re-allocating
space for all these words when we are unlikely to be modifying them,
we really just want a substring of the original.

To make that happen we'd need:

* a pointer to the original string -- so we can maintain a reference
  so that the parent isn't garbage collected under our feet.

* an offset into the parent (or just a pointer to the start within the
  parent string)

* a length

Which seems fine.  You can imagine there's a pathological case where
you might have a substring representing one byte of a 2GB monster you
read in from a file and you can't free the space up because of your
reference to the one byte substring.  I suspect that if that becomes a
problem then maybe we can have the GC do some *re-imagining* under the
hood next time round.

I then thought that, partly for consistency and partly for any weird
cases where we didn't have a NUL-terminated string, real strings
should have a length parameter as well.

If that meant we stored an extra byte (with a NUL in it) then so be it
(we've just casually added 4 or 8 bytes for a ``size_t`` for the
length so an extra byte for a NUL is but a sliver of a nothingness)
and it's quite handy for printing the value out.

That all worked a peach.

Current
^^^^^^^

Along comes Unicode (driven by the need to port some regular
expression handling).

The moral equivalent of the 8-bit characters in :lname:`C` strings are
Unicode's code points.

However, we *don't actually want* an array of code points because
that's a bit dumb -- even we can spot that.  Code points are stored in
an ``IDIO`` "pointer" and so consume 4 or 8 bytes *each* which is way
more than most strings require.  We store them in an ``IDIO`` pointer
because they can then be handled like any other :lname:`Idio` type,
not because it is efficient.

Looking at most of the text that *I* type, I struggle to use all the
ASCII characters, let alone any of the exotic delights from cultures
far a-field.  I'm going to throw this out there that most of the text
that *you* type, dear reader, fits in the Unicode Basic Multilingual
Plane and is therefore encodable in 2 bytes.

I apologise to my Chinese, Japanese and Korean readers who throw 4
byte code points around with abandon.  At least you're covered and not
forgotten.

That blind use of an array of code points will chew up space viciously
-- even the four byte code points with 64-bit ``IDIO`` "pointers".
What we should be doing, as we read the string in, is to perform some
analysis as to which is the largest (widest?) code point in the string
and then construct an array where *all* the elements are that wide.
We already support the notion of a length so there's no need for
trailing NULs -- which don't make any sense in the context of 4 byte
wide "characters".

.. code-block:: idio

   str = "hello"

should only require five bytes of storage as it is only using ASCII
characters.

.. code-block:: idio

   str = "ħello"

Where the first character is U+0127 (LATIN SMALL LETTER H WITH STROKE)
will now be ten bytes long as the first code point requires two bytes
and therefore so will all the rest, even though they are the same
ASCII characters as before.  *Dems da breaks.*

If we join two strings together we can upgrade/widen the one or the
other as required.  The only real problem is that anyone wanting to
*modify* an element in a string array might get caught out by trying
to stuff a 4 byte code point into a one byte string.  You *monster*!
Why are you trying to modify a string *at all*?

Feeling rather pleased with my thinking I then discovered that
:lname:`Python` had already encapsulated this idea in PEP393_ and I
can't believe others haven't done something similar.

I felt good for a bit, anyway.

So that's the deal.  Strings are arrays of elements with widths of 1,
2 or 4 bytes.  The string has a length.  We can have substrings of it.

Implementation
^^^^^^^^^^^^^^

We can encode the string array element width in type-specific flags
and then we need an array length and a pointer to the allocated memory
for it.

.. code-block:: c
   :caption: gc.h

   #define IDIO_STRING_FLAG_NONE		0
   #define IDIO_STRING_FLAG_1BYTE		(1<<0)
   #define IDIO_STRING_FLAG_2BYTE		(1<<1)
   #define IDIO_STRING_FLAG_4BYTE		(1<<2)

   struct idio_string_s {
       size_t len;		/* code points */
       char *s;
   };

   #define IDIO_STRING_LEN(S)	((S)->u.string.len)
   #define IDIO_STRING_S(S)	((S)->u.string.s)
   #define IDIO_STRING_FLAGS(S)	((S)->tflags)

There's something very similar for a substring which requires:

* the reference back to the parent string

* ``s`` becomes a pointer directly into the parent string for the start of the substring

* ``len`` is the substring's length

A substring can figure out the width of elements from its parent.

A substring of a substring is flattened to just being another
substring of the original parent.

Encoding
^^^^^^^^

One thing hidden from the above discourse is the thorny matter of
*encoding*.  All mechanisms to move data between entities need to
agree on a protocol to encode the data over the transport medium.

Unicode used to use UCS-2 and UCS-4 which have been deprecated in
favour of UTF-16 and UTF-32 which are 2 and four byte encodings.  I
get the impression they are popular in the Windows world and they
*might* appear as the "wide character" interfaces in Unix-land, see
:manpage:`fgetwc(3)`, for example.

However, almost everything I see is geared up for UTF-8_ so we'll not
buckle any trends.

Therefore, :lname:`Idio` expects its inputs to be encoded in UTF-8 and
it will generate UTF-8 on output.

To read in UTF-8 we use :ref-author:`Bjoern Hoehrmann`'s
:ref-title:`Flexible and Economical UTF-8 Decoder` :cite:`BH-UTF-8`, a
DFA-based decoder.

Symbols
=======

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

.. _bignum:

Bignum
======

Handles
=======

Bitsets
=======


