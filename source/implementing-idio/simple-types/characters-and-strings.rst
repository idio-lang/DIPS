.. include:: ../../global.rst

**********************
Characters and Strings
**********************

*We're not in Kansas any more, Toto!*

.. sidebox:: Actually, I did the easy :lname:`C`-style strings and
             characters initially but went back and re-wrote it all
             and can now pretend I did it properly in the first place.

	     No-one will ever know!

There's no beating about the bush, we need to handle proper
multi-character set strings from the get-go.  We don't want a
:lname:`Python` 2 vs 3 debacle.

Not for strings, anyway.

Unicode
=======

.. aside::

   Plus the disadvantage of being a native English speaker is that in
   the further flung regions of the world people want to practice
   their English and certainly don't want to listen to me insist that
   my `hovercraft is full of eels`_.

I'm not a multi-lingual expert, indeed barely literate in one
language, so some of the nuance of multi-character set handling may be
lost on me.  We're choosing Unicode_ (arguably ISO10646_) because of
its name familiarity, even if the actual implementation is less
familiar to everyone.

The broad thrust of Unicode is to allocate a *code point*, an integer,
to the most common characters and support several *combining* code
points to create the rest.  From a Western Europe viewpoint, we might
have an "e acute" character, é, but also an "acute accent", ´, which
can be combined with a regular "e".

.. aside::

   Alarmingly, I see there *is* U+1E2F (LATIN SMALL LETTER I WITH
   DIAERESIS AND ACUTE), ḯ.  Looks like I guessed lucky as there's a
   whole range of (predefined) mark combinations in the Latin Extended
   Addition section.

Clearly, we don't need to combine the "acute accent" with a regular
"e" as we already have a specific "e acute" but it does allow us to
combine it with any other character in some rare combination not
specifically covered elsewhere.  There must be rules about how
combining characters are allowed to, er, combine, to prevent an "e
acute diaeresis" (unless that *is* allowed in which case I need to
pick a better example).

These combinations are known as *grapheme clusters* and edge towards
but do not become "characters" *per se*.  It's a grey area and you can
find plenty of discussion online as to what is and isn't a
"character".

Most texts fall back to calling code points characters in much the
same way we call all 128 ASCII characters, er, characters even though
most of the characters below 0x20 make no sense whatsoever as
characters that you or I might draw with a pen.

    0x03 is ``ETX``, *end of text*.  *Eh?* ``ETX`` is, of course, one
    of the `C0 control codes
    <https://en.wikipedia.org/wiki/C0_and_C1_control_codes>`_ used for
    message transmission.  Few of these retain any meaning or function
    and certainly never corresponded with a "character" as, in this
    case, by definition, it marked the end of characters.

    I nearly used 0x04, ``EOT``, *end of transmission*, as my example
    before realising that the *caret notation* for it is ``^D`` which
    might be confused with the usual keyboard generated ``EOF`` with
    :kbd:`Ctrl-D`, *end of file* which is clearly a very similar
    concept.

    They are completely unrelated, of course, as the terminal *line
    driver* determines what keystrokes generate what terminal events:

    .. code-block:: console

       % stty -a
       ...
       intr = ^C; quit = ^\; erase = ^?; kill = ^U;
       eof = ^D; eol = M-^?; eol2 = <undef>;
       swtch = <undef>; start = ^Q; stop = ^S; susp = ^Z;
       rprnt = ^R; werase = ^W; lnext = ^V; discard = ^O;

    Here, ``VEOF`` is :kbd:`Ctrl-D` -- see :manpage:`termios(3)` for
    more than you wanted to know.


Unicode isn't concerned with *glyphs*, the pictorial representation of
characters, either.  Even within the same *font* I can see three
different glyphs for U+0061 (LATIN SMALL LETTER A) -- even within the
constraints of ReStructuredText:

.. csv-table:: The same code point in different fonts
   :widths: 25, 25
   :align: left

   a, regular
   *a*, italic
   **a**, bold

as I pick out different visual styles.  They are all U+0061, though.

The inverse is also an issue.  There are around 150 thousand code
points defined (of the 1,114,112 possible code points) but the font
you are using might only cover a small fraction of those.  If a glyph
for a code point is missing the result isn't clearly defined.  The
rendering system may substitute a glyph indicating the code point in a
box or you may get a blank box.  The following is U+01FBF7 (SEGMENTED
DIGIT 7), 🯷.  (I see a little box with a barely readable ``01F`` on
one row and ``BF7`` on another.)

There's a much better description of some of the differences between
characters and glyphs -- and, indeed, characters and code points -- in
Unicode's `Character Encoding Model
<http://www.unicode.org/reports/tr17/#CharactersVsGlyphs>`_.

Unicode differs from ISO10646 in that although they maintain the same
set of code points the latter is effectively an extended ISO-8859,
meaning a simple list of characters except covering a lot more
character sets.  Unicode goes further and associates with each code
point any number of categories and properties and provides rules on
line-breaking, grapheme cluster boundaries, mark rendering and all
sorts of other things you didn't realise were an issue.

Don't let the simplistic nature of the Unicode_ home page concern you,
go straight to the `Unicode reports`_ and get stuck in.

.. sidebox::

   For those who haven't read the `history of UTF-8
   <http://doc.cat-v.org/bell_labs/utf-8_history>`_ with
   :ref-author:`Rob Pike`, :ref-author:`Ken Thompson` and a New Jersey
   diner placemat.

Actually, don't.  Here, in :lname:`Idio`-land, we **do not** "support"
Unicode.  We use the `Unicode Character Database`_ (UCD) and some
categories and properties related to that and UTF-8 encoding.  We will
use the "simple" lowercase and uppercase properties from the UCD to
help with corresponding character mapping functions, for example.

However, :lname:`Idio` is not concerned with correct, legal, security
or any other Unicode consideration.  :lname:`Idio` simply uses
whatever is passed to it and actions whatever the string manipulation
the user invokes.  If the result is non-conformant then so be it.
*User error.*

We *might* have to consider matters such as `Collation
<https://www.unicode.org/reports/tr10/>`_ of strings -- as we may not
be using any system-provided collation library (which you would hope
would have considered it).  But we really don't want to.  That
document is 29 thousand words long!

We can almost certainly ignore Unicode's view on `Regular Expressions
<https://www.unicode.org/reports/tr18/>`_ as their view has been
swayed by `Perl Regular Expressions
<https://perldoc.perl.org/perlre.html>`_.  In particular, their view
on what constitutes an identifier isn't going to help us where we can
include many punctuation characters and, hopefully, regular Unicode
identifier names.

.. rst-class:: center

---

As noted previously, the code point range is 2\ :sup:`21` integers but
not all of those are valid "characters".  A range of values in the
first 65,536 is excluded as a side-effect of handling the UTF-16_
encoding when Unicode finally recognised that 65,536 code points was
not, in fact, more than enough.

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
plane being 16 bits, ie. potentially 65,536 code points.  (NB. At
least two code points in every plane are reserved as byte-order
marks.)

Each plane is chunked up into varying sized blocks which are allocated
to various character set purposes.  Some very well known character
sets are historically fixed, for example ISO8859-1_, and the block is
full.  Other character sets have slots reserved within the block for
future refinements.

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
forms`_ -- effectively ｄｕｐｌｉｃａｔｉｎｇ ＡＳＣＩＩ．

.. rst-class:: center

---

The issue with handling Unicode is, um, everything.  We have an issue
about the *encoding* in use when we read Unicode in -- commonly,
UTF-8, UTF-16 or UTF-32.  We have an issue about *storing* code points
and strings (ie. arrays of code points) internally.  And we have to
decide which encoding to use when we emit code points and strings.

There's also a subtlety relating to the *meaning* of code points.  For
example, most of us are familiar with ASCII (and therefore Unicode)
decimal digits, 0-9 (U+0030 through to U+0039).  Unicode has *lots* of
decimal digits, though, some 650 code points have the ``Nd`` category
(meaning decimal number) alone.  In addition Unicode supports other
numeric code points such as Roman numerals .

In principle, then, we ought to support the use of any of those code
points as numeric inputs -- ie. there are 65 zeroes, 65 ones, 65 twos,
etc. -- because we can use a Unicode attribute, *Numeric_Value*,
associated with the code point to get its decimal value.

However, we then have to consider what it means to mix those Numeric
code points across groups in the same word: 1\ :raw-html:`&#x0662;`\
:raw-html:`&#x06F3;`\ :raw-html:`&#x07C4;`\ :raw-html:`&#x096B;` is
12345 with a code point from each of the first five of those groups
(Latin-1, Arabic-Indic, Extended Arabic-Indic, NKO, Devanagari).  Does
it make any sense to mix these character sets *in the same
expression*?

It becomes increasingly complex to reason about these things and the
inter-relationship between character sets at which point we start
laying down the law.

Or would do.  At the moment the code invokes the likes of
:manpage:`isdigit(3)` and friends which, in turn, use locale-specific
lookup tables.  Of interest, the only valid input values to those
functions are an ``unsigned char`` or ``EOF`` which rules out most CJK
character sets and, indeed, everything except Latin-1 in the above
example.

.. rst-class:: center

---

In some ways I think we could be quite pleased that the language
allows you to create variables using Unicode code points (outside of
Latin-1) and assign values to them using non-ASCII digits.  Many
people might then bemoan the unreadability of the resultant program
forgetting, presumably, that, say, novels are published in foreign
languages without much issue.

English *appears* to be the *lingua franca* of computing, for good or
ill, and I can't see how being flexible enough to support non-ASCII
programming changes that.

More work (and someone less Western-European-centric and not a
monoglot) required to sort this out.

In the meanwhile, let's try to break Unicode down.

Code Points
-----------

Code points are (very) distinct from strings (in any encoding).  For a
code point we want to indicate which of the 2\ :sup:`21`-ish integers
we mean.  We've previously said that the reader will use something
quite close to the Unicode consortium's own stylised version:
``#U+hhhh``.

Although ``hhhh`` represents a hexadecimal number so any number of
``h``\ s which return a suitable number are good.

As discussed in :ref:`constants`, we can then stuff that code point
into a specific constant type, here, ``ccc`` is ``100`` giving us:

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

Reading
^^^^^^^

As noted, there are three reader forms:

#. ``#\X`` for some UTF-8 encoding of ``X``

   ``#\ħ`` is U+0127 (LATIN SMALL LETTER H WITH STROKE)

#. ``#\{...}`` for some (very small set of) named characters

#. ``#U+hhhh`` for any code point

Writing
^^^^^^^

There are two forms of output depending on whether the character is
being printed (ie. a reader-ready representation is being generated)
or displayed (as part of a body of other output).

If printed, Unicode code points will be printed out in the standard
``#U+hhhh`` format with the exception of code points under 0x80 which
are :manpage:`isgraph(3)` which will take the ``#\X`` form.

If displayed, the Unicode code point is encoded in UTF-8.

.. _strings:

:lname:`Idio` Strings
=====================

By which we mean arrays of code points... *-ish*.

History
-------

If we start with, as I did, :lname:`C` strings we can get a handle on
what I was doing.

In :lname:`C` a string is an array of single byte characters
terminated by an ASCII NUL (0x0).  That's pretty reasonable and we can
do business with that.

However, I was thinking that a lot of what we might be doing in a
shell is splitting lines of text up into words (or fields if we have
an :program:`awk` hat on).  We don't *really* want to be re-allocating
memory for all these words when we are unlikely to be modifying them,
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
reference to the one byte substring.  I suspect that if that is really
a problem then maybe we can have the GC do some *re-imagining* under
the hood next time round.

I then thought that, partly for consistency and partly for any weird
cases where we didn't have a NUL-terminated string to start with, real
strings should have a length parameter as well.

If that meant we stored an extra byte (with a NUL in it) then so be it
(we've just casually added 4 or 8 bytes for a ``size_t`` for the
length so an extra byte for a NUL is but a sliver of a nothingness)
and it's quite handy for printing the value out.

That all worked a peach.

Current
-------

Along comes Unicode (primarily driven by the need to port some regular
expression handling as I hadn't mustered the enthusiasm to re-write
strings beforehand).

The moral equivalent of the 8-bit characters in :lname:`C` strings are
Unicode's code points.

However, we *don't actually want* an array of code points because
that's a bit dumb -- even we can spot that.  Code points are stored in
an ``IDIO`` "pointer" and so consume 4 or 8 bytes *each* which is way
more than most strings require.  We store code points in an ``IDIO``
pointer because they can then be handled like any other :lname:`Idio`
type, not because it is efficient.

Looking at most of the text that *I* type, I struggle to use all the
ASCII characters, let alone any of the exotic delights from cultures
further a-field.  I'm going to throw this out there that most of the
text that *you* type, dear reader, fits in the Unicode Basic
Multilingual Plane and is therefore encodable in 2 bytes.

I apologise to my Chinese, Japanese and Korean friends who throw 4
byte code points around with abandon.  At least you're covered and not
forgotten.

That blind use of an array of code points will chew up space viciously
-- even the four byte code points with 64-bit ``IDIO`` "pointers".
What we should be doing, as we read the string in, is to perform some
analysis as to which is the largest (widest?) code point in the string
and then construct an array where *all* the elements are that wide.
We already support the notion of a length so there's no need for
trailing NULs -- which don't make any sense in the context of 4 byte
wide "characters" anyway.

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

By and large, though, I sense that most strings are going to be
internally very consistent and be:

* ASCII/Latin-1 and therefore 1 byte code points *only*

* mostly BMP (2 byte) and some 1 byte code points

* using 4 byte code points regularly

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

I've no particular fix for the string modification issue.  In
principle it requires reworking the string under the feet of the
caller but we now have to ensure that all the associated substrings
are kept in sync.

A rotten workaround would be to prefix any string with a 4 byte letter
then only use indexes 1 and beyond.

A better workaround would be to allow the forcible creation of, say, 4
byte strings rather than using analysis of the constituent code
points.

Implementation
--------------

We can encode the string array's element width in type-specific flags
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

``s`` is a ``char *`` (and called ``s``) for the obvious historic
reasons although ``s`` is never used to access the elements of the
array directly.  We will figure out the element width from the flags
and then use a ``uint8_t *s8``, ``uint16_t *s16`` or ``uint32_t *s32``
cast from ``s`` as appropriate.  The array elements are then casually
accessed with ``s8[i]``, ``s16[i]`` or ``s32[i]``.  Easy.

There's something very similar for a substring which requires:

* the reference back to the parent string

* ``s`` becomes a pointer directly into the parent string for the
  start of the substring -- but is otherwise cast to something else in
  the same manner as above

* ``len`` is the substring's length

A substring can figure out the width of elements from its parent.

A substring of a substring is flattened to just being another
substring of the original parent.

.. rst-class:: center

\*

Amongst other possible reworks, I notice many other implementations
allocate the ``IDIO`` object and the memory required for the string
storage in one block.

It would save the two pointers used by :manpage:`malloc(3)` for its
accounting and the extra calls to
:manpage:`malloc(3)`/:manpage:`free(3)`.

.. rst-class:: center

\*

I did have an idea for a "short" string.  The nominal ``IDIO``
``union`` is three pointers worth -- to accommodate a pair, the most
common type -- could we re-work that as a container for short strings?

Three pointers worth is 12 or 24 bytes.  If we used an ``unsigned
char`` for the length then we could handle strings up to 11 or 23
bytes.

I think you'd need to do some "field analysis" to see if such short
strings occur often enough to make it worth the effort.

Encoding
--------

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

Reading
-------

The input form for a string is quite straightforward: ``"..."``.

The reader is, in one sense, quite naive and is strictly looking for a
non-escaped closing ``"`` to terminate the string, see
``idio_read_string()`` in :file:`read.c`.

Subsequently the collected bytes are assumed to be part of a valid
UTF-8 sequence.  If the byte sequence is invalid UTF-8 you will get
the (standard) U+FFFD (REPLACEMENT CHARACTER) and the decoding will
resume *with the next byte*.  This may result in several replacement
characters being generated.

There are a couple of notes:

#. ``\`` (backslash, reverse solidus) is the escape character.  The
   obvious character to escape is ``"`` itself allowing you to embed a
   double-quote symbol in a double-quoted string: ``"hello\"world"``.

   In the spirit of `C escape sequences
   <https://en.wikipedia.org/wiki/Escape_sequences_in_C>`_
   :lname:`Idio` also allows:

   .. csv-table:: Supported escape sequences in strings
      :header: sequence, (hex) ASCII, description
      :align: left

      ``\a``, 07, alert / bell
      ``\b``, 08, backspace
      ``\e``, 1B, escape character
      ``\f``, 0C, form feed
      ``\n``, 0A, newline
      ``\r``, 0D, carriage return
      ``\t``, 09, horizontal tab
      ``\v``, 0B, vertical tab
      ``\\``, 5C, backslash

   :lname:`Idio` ought to support some means of embedding Unicode code
   points -- perhaps using the :lname:`C`-like ``\uhhhh`` -- but it
   doesn't (yet).

#. :lname:`Idio` allows multi-line strings:

   .. code-block:: idio

      str1 := "Hello
      World"

      str2 := "Hello\nWorld"

   The string constructors for ``str1`` and ``str2`` are equivalent.

Interpolated Strings
^^^^^^^^^^^^^^^^^^^^

Sometimes we want to embed references to variables, usually, or
expressions in a string and have something figure out the current
value of the variable or result of the expression and replace the
reference with that result, something along the lines of:

.. code-block:: idio

   name := "Bob"

   "Hi, ${name}!"

I want double-quoted strings, the usual ``"..."``, to remain as fixed
entities, much like single-quoted strings in, say, :lname:`Bash` are.
That means we need another format, another ``#`` format!  Let's go for
``#S{ ... }`` and everything between the matching braces is our
putative string.

The ``${name}``\ -style format seems good to me, the only issue being
whether we want to change ``$`` for another sigil.  In the usual way,
we'd pass that in between the ``S`` and ``{``:

.. code-block:: idio

   #S{Hi, ${name}!}

   #S^{Hi, ^{name}!}

The second interpolation character is the escape character, defaulting
to ``\``, as usual.

You can use the usual matching bracketing characters, ``{}``, ``[]``
and ``()`` to delimit the main block:

.. code-block:: idio

   #S[${name} is ${string-length name} letters long.]

but only braces, ``{}`` for the references.

There is a subtlety here as the results of the expressions are not
necessarily themselves strings so, in practice, all of the elements of
the putative string, the non-expression strings and the results of the
expressions are ``map``\ ed against ``->string`` which leaves strings
alone and runs the "display" variant of the printer for the results of
the expressions.

``->string`` does not perform any splicing so if your expression
returns a list then you'll get a list in your string.  It might be
what you want!

Writing
-------

:lname:`Idio` strings will be UTF-8 encoded on output, see
``idio_utf8_string()`` in :file:`unicode.c` for the details.

There's a couple of qualification to that:

#. We can ask for the reader's :lname:`C` escape sequences to be
   reproduced in their ``\X`` format, eg. ``\a`` for alert / bell.

#. We can ask for the printed string to be quoted with double quotes.

   This latter option is a consequence of how we visualise printed
   entities.  The REPL will *print* values in a reader-ready format,
   so including leading and trailing ``"``\ s.

   .. code-block:: console

      Idio> str := "Hello\nWorld"
      "Hello\nWorld"

      Idio> str := "Hello
      World"
      "Hello\nWorld"

   By and large, though, most things will *display* a string value as
   part of a larger output:

   .. code-block:: console

      Idio> printf "'%s'\n" str
      'Hello
      World'

   (Actually, a trailing ``#<unspec>`` will also be printed which is
   the value that ``printf`` returned.)

Operations
==========

.. _`Unicode code point operations`:

Characters
----------

:samp:`unicode? {value}`

      is :samp:`{value}` a Unicode code point

:samp:`unicode->plane {cp}`

      return the Unicode plane of code point :samp:`{cp}`

      The result is a fixnum.

:samp:`unicode->plane-cp {cp}`

      return the lower 16-bits of the code point :samp:`{cp}`

:samp:`unicode->integer {cp}`

      convert code point :samp:`{cp}` to a fixnum

:samp:`unicode=? {cp1} {cp2} [...]`

      compare code points for equality

      A minimum of two code points are required.


Strings
-------

:samp:`string? {value}`

      is :samp:`{value}` a string (or substring)

:samp:`make-string {size} [{fill}]`

      create a string of length :samp:`{size}` filled with
      :samp:`{fill}` characters or U+0020 (SPACE)

.. _`string->list`:

:samp:`string->list {string}`

      return a list of the Unicode code points in :samp:`{string}`

      See also :ref:`list->string <list->string>`.

.. _`string->symbol`:

:samp:`string->symbol {string}`

      return a symbol constructed from the UTF-8 Unicode code points
      in :samp:`{string}`

      See also :ref:`symbol->string <symbol->string>`.
   
.. _`append-string`:

:samp:`append-string [{string} ...]`

      return a string constructed by appending the string arguments
      together

      If no strings are supplied the result is a zero-length string,
      cf. ``""``.
   
:samp:`concatenate-string {list}`

      return a string constructed by appending the strings in
      :samp:`{list}` together

      If no strings are supplied the result is a zero-length string,
      cf. ``""``.
   
:samp:`copy-string {string}`

      return a copy of string :samp:`{string}`
   
:samp:`string-length {string}`

      return the length of string :samp:`{string}`
   
:samp:`string-ref {string} {index}`

      return the Unicode code point at index :samp:`{index}` of string
      :samp:`{string}`

      Indexes start at zero.

:samp:`string-set! {string} {index} {cp}`

      set the Unicode code point at index :samp:`{index}` of string
      :samp:`{string}` to be the Unicode code point :samp:`{cp}`

      Indexes start at zero.

      If the number of bytes required to store :samp:`{cp}` is greater
      than the per-code point width of :samp:`{string}` a
      ``^string-error`` condition will be raised.

:samp:`string-fill! {string} {fill}`

      set all indexes of string :samp:`{string}` to be the Unicode
      code point :samp:`{fill}`

      If the number of bytes required to store :samp:`{fill}` is
      greater than the per-code point width of :samp:`{string}` a
      ``^string-error`` condition will be raised.

:samp:`substring {string} {pos-first} {pos-next}`

      return a substring of string :samp:`{string}` starting at index
      :samp:`{pos-first}` and ending *before* :samp:`{pos-next}`.

      Indexes start at zero.

      If :samp:`{pos-first}` and :samp:`{pos-next}` are inconsistent a
      ``^string-error`` condition will be raised.

:samp:`string<=? {s1} {s2} [...]`

:samp:`string<? {s1} {s2} [...]`

:samp:`string=? {s1} {s2} [...]`

:samp:`string>=? {s1} {s2} [...]`

:samp:`string>? {s1} {s2} [...]`

      .. warning::

	 Historic code for ASCII/Latin-1 :lname:`Scheme` strings
	 badgered into working at short notice.

	 These need to be replaced with something more Unicode-aware.

      perform :manpage:`strncmp(3)` comparisons of the UTF-8
      representations of the string arguments

:samp:`string-ci<=? {s1} {s2} [...]`

:samp:`string-ci<? {s1} {s2} [...]`

:samp:`string-ci=? {s1} {s2} [...]`

:samp:`string-ci>=? {s1} {s2} [...]`

:samp:`string-ci>? {s1} {s2} [...]`

      .. warning::

	 Historic code for ASCII/Latin-1 :lname:`Scheme` strings
	 badgered into working at short notice.

	 These need to be replaced with something more Unicode-aware.

      perform :manpage:`strncasecmp(3)` comparisons of the UTF-8
      representations of the string arguments

:samp:`split-string {string} {delim}`

      split string :samp:`{string}` into a list of string delimited by
      the code points in the string :samp:`{delim}`

      ``split-string`` is meant to act like the shell's or
      :program:`awk`'s word-splitting by ``IFS``.

      Clearly it does not act like a regular expression string
      delimitation in that multiple adjacent instances of delimiter
      characters only provoke one "split."

:samp:`split-string-exactly {string} {delim}`

      split string :samp:`{string}` into a list of string delimited by
      the code points in the string :samp:`{delim}`

      ``split-string-exactly`` is meant to act more like a regular
      expression matching system.

      It was required to split the contents of the Unicode Character
      Database file :file:`UnicodeData.txt` -- which has multiple
      ``;``-separated fields, often with no value in a field -- to
      help generate the code base for regular expression handling.

:samp:`join-string {delim} {list}`

      construct a string from the strings in :samp:`{list}` with the
      string :samp:`{delim}` placed in between each pair of strings

      :samp:`{list}` is a, uh, list, here, unlike, say,
      :ref:`append-string <append-string>` as it follows the
      :lname:`Scheme` form (albeit with arguments shifted about)
      which takes another parameter indicating the style in
      which the delimiter should be applied, such as: before or
      after every argument, infix (the default) and a strict
      infix for complaining about no arguments.

:samp:`strip-string {str} {discard} {ends}`

      return a string where the characters in :samp:`{discard}` have
      been removed from the :samp:`{ends}` of :samp:`{str}`

      :samp:`{ends}` can be one of ``'left``, ``'right``, ``'both`` or
      ``'none``.

.. include:: ../../commit.rst

