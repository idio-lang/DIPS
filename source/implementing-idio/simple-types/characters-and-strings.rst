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

.. _`idio unicode`:

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

Clearly, *we* don't need to combine the "acute accent" with a regular
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

.. sidebox::

   Interestingly, :program:`emacs` is showing the underlined variant
   of the ordinal indicator in the source where, at least, you can
   easily see that the glyphs and therefore the code points are
   different.

The glyph in your font might also cause some entertainment for the
ages were you to mistake 20º with 20°.  Here, we have (*foolishly!*)
crossed U+00BA (MASCULINE ORDINAL INDICATOR) with U+00B0 (DEGREE SIGN)
-- and that's `not the only confusion possible
<https://en.wikipedia.org/wiki/Ordinal_indicator>`_.

This is not just an issue with squirrelly superscripted characters but
also where `Punycode <https://en.wikipedia.org/wiki/Punycode>`_ is
used in domain names to use non-ASCII characters with similar glyphs
to ASCII characters to masquerade one domain as another.  The example
in the `Homoglyph <https://en.wikipedia.org/wiki/Homoglyph>`_ page is
the near identical expressions of a, U+0061 (LATIN SMALL LETTER A),
and а, U+0430 (CYRILLIC SMALL LETTER A).  Browsers, hopefully, have
gotten better at alerting users to the duplicitous ``bаnk.com``.

Your choice of font introduces another issue.  There are around 150
thousand code points defined (of the 1,114,112 possible code points)
but the font you are using might only cover a small fraction of those.
If a glyph for a code point is missing the result isn't clearly
defined.  The rendering system may substitute a glyph indicating the
code point in a box or you may get a blank box.  The following is
U+01FBF7 (SEGMENTED DIGIT 7), 🯷.  (I see a little box with a barely
legible ``01F`` on one row and ``BF7`` on another.)

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

   Do read the `history of UTF-8
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
plane being 16 bits, ie. potentially 65,536 code points.  Note that
there are several code points which are in some senses invalid in any
encoding including the last two code points in every plane.

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
to get a viable code point.  Well, you *can* hope/expect but good luck
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
other as required.

.. aside::

   You *monster*!  Why are you trying to modify a string *at all*?

The only real problem is that anyone wanting to *modify* an element in
a string array might get caught out by trying to stuff a 4 byte code
point into a one byte string.

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
allocate the equivalent of the ``IDIO`` object and the memory required
for the string storage in one block.

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

The input form for a string is quite straightforward: ``"..."``, that
is a U+022 (QUOTATION MARK) delimited value.

The reader is, in one sense, quite naive and is strictly looking for a
non-escaped closing ``"`` to terminate the string, see
``idio_read_string()`` in :file:`read.c`.

Subsequently the collected bytes are assumed to be part of a valid
UTF-8 sequence.  If the byte sequence is invalid UTF-8 you will get
the (standard) U+FFFD (REPLACEMENT CHARACTER) and the decoding will
resume *with the next byte*.  This may result in several replacement
characters being generated.

There are a couple of notes:

#. ``\``, U+005C (REVERSE SOLIDUS -- backslash) is the escape
   character.  The obvious character to escape is ``"`` itself
   allowing you to embed a double-quote symbol in a double-quoted
   string: ``"hello\"world"``.

   In the spirit of `C escape sequences
   <https://en.wikipedia.org/wiki/Escape_sequences_in_C>`_
   :lname:`Idio` also allows:

   .. csv-table:: Supported escape sequences in strings
      :header: sequence, (hex) ASCII, description
      :align: left
      :widths: auto

      ``\a``, 07, alert / bell
      ``\b``, 08, backspace
      ``\e``, 1B, escape character
      ``\f``, 0C, form feed
      ``\n``, 0A, newline
      ``\r``, 0D, carriage return
      ``\t``, 09, horizontal tab
      ``\v``, 0B, vertical tab
      ``\\``, 5C, backslash
      ``\x...``, , up to 2 hex digits representing any byte
      ``\u...``, , up to 4 hex digits representing a Unicode code point
      ``\U...``, , up to 8 hex digits representing a Unicode code point

   For ``\x``, ``\u`` and ``\U`` the code will stop consuming code
   points if it sees one of the usual delimiters or a code point that
   is not a hex digit: ``"\Ua9 2021"`` silently stops at the SPACE
   character giving ``"© 2021"`` and, correspondingly,
   ``"\u00a92021"`` gives ``"©2021"`` as only 4 hex digits are
   consumed by ``\u``.

   ``\x`` is unrestricted (other than between 0x0 and 0xff) and ``\u``
   and ``\U`` will have the hex digits converted into UTF-8.

   Adding ``\x`` bytes into a string is an exercise in due diligence.

#. :lname:`Idio` allows multi-line strings:

   .. code-block:: idio

      str1 := "Hello
      World"

      str2 := "Hello\nWorld"

   The string constructors for ``str1`` and ``str2`` are equivalent.

Pathnames
^^^^^^^^^

.. aside::

   I'm not sure there is a proper nomenclature for pathnames and
   filenames.  I suspect most people will use them interchangeably
   most of the time (I do) though there is a suggestion of pathnames
   being filenames joined with ``/``.

The reason the ``\x`` escape exists is to allow more convenient
creation of "awkward" pathnames.  As noted previously \*nix pathnames
do not have any *encoding* associated with them.

Now, that's not to say you can't *use* an encoding and, indeed, we are
probably *encouraged* to use UTF-8 as an encoding for pathnames.
However, the problem with the filesystem having no encoding is that
both you and I have to agree on what the encoding we have used is.
You say potato, I say `solanum tuberosum
<https://en.wikipedia.org/wiki/Potato>`_.

In general :lname:`Idio` uses the (UTF-8) encoded strings in the
source code as pathnames and, as the :lname:`Idio` string to
:lname:`C` string converted uses a UTF-8 generator, by and large,
every pathname you create will be UTF-8 encoded.

However, any pathname already in the filesystem is of an unknown
encoding of which the only thing we know is that it won't contain an
ASCII NUL and it won't have U+0027 (SOLIDUS -- forward slash) in a
directory entry.  It's a :lname:`C` string.

.. aside::

   Which is the vast majority of humans.  Ever.  *Who knew?*

Of course we "get away with" an implicit UTF-8 encoding because the
vast majority of \*nix filenames are regular ASCII ones.  Only those
users outside of North America and islands off the coast of North
Western Europe have suffered.

So what we really need is to handle such pathnames correctly which
means, *not* interpret them.

Technically, then, the :lname:`Idio` string ``"hello"`` and the
filename :file:`hello` are *different*.  Which is going to be a bit
annoying from time to time.

.. note::

   Of interest, it is possible to manipulate strings such that you
   have a 1-byte width encoding for ``"hello"`` and a 2 or 4-byte
   encoding for ``"hello"``.  However, those strings will be
   considered ``equal?`` because they have the same length and the
   same code points.

As it so happens, for general file access and creation, the
:lname:`Idio` strings, converted into UTF-8 encoded :lname:`C` strings
will do the right thing.  However, if you consume filenames from the
filesystem they will be treated as pathnames and will not be
``equal?`` to the nominally equivalent :lname:`Idio` string.

So we need to be able to create \*nix pathnames ourselves for these
sorts of comparisons and we have a formatted string style to do that:
``%P"..."`` (or ``%P(...)`` or ``%P{...}`` or ``%P[...]``) where the
``...`` is a regular string as above.

That's where the ``\x`` escape for strings comes into its own.  If we
know that a filename starts with ISO8859-1_'s 0xA9 (the same
"character" as ©, U+00A9 (COPYRIGHT SIGN)), as in a literal byte,
0xA9, and not the UTF-8 sequence 0xC2 0xA9, then we can create such a
string: ``%P"\xa9..."``.

The ``%P`` formatted string is fine if we hand-craft our pathname for
comparison but if we already have an :lname:`Idio` string in our hands
we need a converter, ``string->pathname``, which will, return a
pathname from the UTF-8 encoding of your string.  Which sounds
slightly pointless but gets us round the problem of matching against
pathnames in the filesystem which have no encoding.

.. code-block:: idio-console

   Idio> string->pathname "hello"
   %P"hello"

Notice the leading ``%P`` indicating it is a pathname.

Pathname Expansion
""""""""""""""""""

As if pathnames as an unencoded string aren't complicated enough we
want *wildcards*!

:lname:`Bash` has a reasonably pragmatic approach to wildcards.  From
:manpage:`bash(1)`, **Pathname Expansion**:

    After word splitting, unless the **-f** option has been set,
    **bash** scans each word for the characters **\***, **?**, and
    **[**.  If one of these characters appears, and is not quoted,
    then the word is regarded as a pattern, and replaced with an
    alphabetically sorted list of filenames matching the pattern

Unfortunately, our free hand with the code points allowed in symbols
means that ``*`` and ``?`` are not just possible but entirely probable
and, certainly, to be expected.  That makes wildcards a bit tricky.

Hmm.  I've noted before that Murex_ constrains globbing to
:samp:`@\\{g {*.c}}` and extends the mechanism to regexps,
:samp:`@\\{rx {\\.c$}}`, and file modes, :samp:`@\\{f {+d}}`.

Although I think we want a mechanism to do globbing which is distinct
from any sorting and filtering you might perform on the list.

We've mention :ref:`pathname templates` before although they are a
little bit magical.

.. sidebox::

   Obviously, ``%P...`` and ``#P...`` are ripe for confusion.  I try
   to think of the ``%`` suggesting a :manpage:`printf(3)` *format*
   whereas the ``#`` is suggesting the construction of a weird thing.

I want ``#P{...}`` (or ``#P(...)`` or ``#P[...]`` or ``#P"..."``) to
create a pathname template but not *exercise* it yet.  This is akin to
creating a regular expression in advance, the :ref:`regcomp
<libc/regcomp>` before the :ref:`regexec <libc/regexec>` of POSIX
regexs.

Only when it is *used* do we :manpage:`glob(3)` the expression.  This
does lead to a little confusion:

.. code-block:: idio-console

   Idio> p := #P"x.*"
   #<SI ~path pattern:%P"x.*">
   Idio> p
   (%P"x.idio")
   Idio> printf "%s\n" p
   (%P"x.idio")
   #<unspec>

which feels OK but

.. code-block:: idio-console

   Idio> printf "%s\n" #P"x.*"
   #<SI ~path pattern:%P"x.*">
   #<unspec>
   Idio> ls #P"x.*"
   x.idio
   #t

Feels wrong.  Why does the expansion occur for :program:`ls` and not
for ``printf``?  Technically, for both, the arguments are constructed
as you would expect giving both of them the *struct instance* of a
``~path`` (mnemonically, a dynamic path).  However, because we need to
convert all of the arguments to strings for :manpage:`execve(2)`, the
*use* of a ``~path`` struct instance is expanded into a list of
pathnames.

It's not great.

In the meanwhile, we can do the right sorts of things creating and
matching files with non-UTF-8 characters in them:

.. code-block:: idio-console

   Idio> close-handle (open-output-file %P"\xa9 2021")
   #unspec
   Idio> p := #P"\xa9*"
   #<SI ~path pattern:%P"\xA9*">
   Idio> p
   (%P"\xA9 2021")
   Idio> ls -1f
    ...
   ''$'\251'' 2021'
   ...

.. aside::

   Rummaging around in the :program:`info` pages I see this is the
   default "shell-escape" quoting style using the POSIX proposed
   ``$''`` syntax.

   *Times have changed since SunOS 4!*

I see, here, that :program:`ls` is using a :lname:`Bash`-style
``$'...'`` quoting such that ``''$'\251'' 2021'`` is the concatenation
of ``''``, ``$'\251'`` and ``' 2021'`` with ``\251`` being the octal
for 0xA9.

For :lname:`Idio`, specifically when printing strings in a "use
escapes" context, here, at the REPL, a pathname string will have
non-:manpage:`isprint(3)` characters converted to a ``\x`` form,
hence, ``%P"\xA9 2021"``.  Similarly, a pathname with a newline in it
would be, say, ``%P"hello\nworld"``.

When *not* printing strings in a "use escapes" context, notably when
preparing arguments for :manpage:`execve(2)` then we just get the raw
\*nix pathname characters meaning something like :program:`ls` won't
get in a tizzy:

.. code-block:: idio-console

   Idio> close-handle (open-output-file %P"\xa9 2021")
   #<unspec>
   Idio> ls %P"\xa9 2021"
   ''$'\251'' 2021'
   #t

compare with the variations for when 0xA9 is an invalid UTF-8 encoding
in a regular string and when the Unicode code point U+00A9 is used:

.. code-block:: idio-console

   Idio> ls "\xa9 2021"
   /usr/bin/ls: cannot access ''$'\357\277\275'' 2021': No such file or directory
   #f
   job 327830: (ls "� 2021"): completed: (exit 2)
   Idio> ls "\ua9 2021"
   /usr/bin/ls: cannot access ''$'\302\251'' 2021': No such file or directory
   #f
   job 327834: (ls "© 2021"): completed: (exit 2)

The first is completely garbled and you can see the copyright sign in
the notification about the command failure in the second with
:program:`ls` complaining that it can't access something beginning
with (*\*quickly translates\**) 0xC2 0xA9, the UTF-8 encoding of 0xA9.

.. rst-class:: center

\*

That said, regex and, by extension pattern matching, are not affected
by this distinction as they aren't concerned about the *equality* of
the strings and/or pathnames so much as whether they conform to a
(regular expression) pattern:

.. code-block:: idio

   pt := #P{\xA9*}

   map (function (p) {
	  printf "%s: " p
	  (pattern-case p
			("*2021" {
			  printf "2021!\n"
			})
			(else {
			  printf "nope!\n"
			}))
   }) pt


.. _`interpolated strings`:

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
necessarily themselves strings.  The ``${string-length name}``
expression, for example, will result in an integer and the implied
``append-string`` constructing the result of the interpolated string
will get upset.

So, in practice, all of the elements of the putative string, the
non-expression strings and the results of the expressions are ``map``\
ed against ``->string`` which leaves strings alone and runs the
"display" variant of the printer for the results of the expressions.

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

   .. code-block:: idio-console

      Idio> str := "Hello\nWorld"
      "Hello\nWorld"

      Idio> str := "Hello
      World"
      "Hello\nWorld"

   By and large, though, most things will *display* a string value as
   part of a larger output:

   .. code-block:: idio-console

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

