.. include:: ../../global.rst

.. _USI:

***************************
Unicode Summary Information
***************************

I hit upon Simon Schoenenberger's `Unicode character lookup table
<https://github.com/detomon/unicode-table>`_ work whilst chasing
around a JSON5_ library and have re-imagined it.

The basic premise is that you can walk through
:file:`utils/Unicode/UnicodeData.txt` and extract:

* the General Category

* the *relative* Uppercase, Lowercase and Titlecase mappings
  
* and Numeric Value

.. sidebox::

   430 will increase by several tens or so when we start getting picky
   about Properties etc..  For example, the ``ASCII_Hex_Digit``
   Property affects ASCII a-f and ASCII A-F and therefore makes them
   unlike the remaining ASCII lowercase and uppercase letters.

and discover that, instead of ~34k entries in
:file:`utils/Unicode/UnicodeData.txt` (representing 150k valid code
points), there are just 430 variations.

For example, the usual ASCII uppercase code points all become: ``Lu 0
32 0 0`` where the 32 means the corresponding lowercase code point can
be derived from this by adding 32.  Similarly, the ASCII lowercase
code points all become ``Ll -32 0 -32 0``.

The trailing zero is the numeric value which, as the ASCII uppercase
and lowercase letters are not classed as numeric, will not be used.
The C static structure initialisation needs something, though!

In fact, there are 194 such ``Lu`` Unicode code points and 204 such
``Ll`` Unicode code points if we're just using
:file:`utils/Unicode/UnicodeData.txt`.  Similarly, there are 76 ``Lu``
and ``Ll`` code points where the uppercase and lowercase character
differ by 40 rather than 32.

Whilst 430 variations sounds good, we still have to get from a code
point to there -- and we don't want a 1114112 (#x110000) entry lookup
table.

At this point Schoenenberger splits the code points into pages of 256
code points and does a double indirection from a ``PageIndex[cp >>
8]`` into an ``InfoIndex[page][cp & 0xff]`` to reference one of the
430 (529 in his case) variations.  Those two tables come to some 43k
words, which is a fraction of the nominal size.

The trick he's pulling here is that when you divide the entire code
point table up into groups of 256 code points then even those groups
of 256, of what you might think were fairly random collection of
references to the 430 unique variations, end up with duplicates.  And
this isn't talking about Planes 4 through 13 which will all map to an
Unassigned variation.

Unicode Character Database
==========================

For everything, see http://www.unicode.org/reports/tr44/.  The
relevant files have been copied into :file:`utils/Unicode`.

Broadly, Unicode have defined 17 Planes each with a potential for
65,536 code points.  That makes any mapping be at least 1114109
entries long.  Blocks within those Planes are assigned for groups of
code points with a common ancestry.  For example, code points
``U+0000`` through ``U+007F`` are ASCII.  Some of those blocks are
complete because the group is well defined, eg. ASCII, whereas others
include unassigned code points leaving room for later additions.  The
order in which those blocks are assigned is (probably) an editorial
whim.

Note: even though Unicode Planes 4-13 are currently unassigned, see
`Unicode Planes <https://en.wikipedia.org/wiki/Plane_(Unicode)>`_, it
isn't clear that Unicode will stick to 17 planes.  Given that we have
to read the Unicode UCD files we might as well leave the actual number
of Unicode code points/Planes dynamic based on reading the files.

Further note: given that those 10 planes are unassigned, perhaps we
should invent a sparse char-set format for char-sets saving at least
650k bits per char-set.  Now defined as an array of seventeen
:ref:`bitsets`.

UnicodeData.txt
---------------

:file:`utils/Unicode/UnicodeData.txt` is a long list (34k entries as
of Unicode 13.0.0) of individual code points and code point ranges
(whose individual code point Properties are derivable within the
range).  Each code point has a *General Category*: Letter lowercase,
``Ll``, Letter uppercase, ``Lu``, Number digit, ``Nd``, Symbol Math,
``Sm`` etc..

The set of code points is not contiguous and the current highest
numbered code point is ``U+10FFFD``, Plane 16 Private Use, Last.

DerivedCoreProperties.txt
-------------------------

:file:`utils/Unicode/DerivedCoreProperties.txt` is a fairly long list
(12k lines) which summaries collections of code points which share a
common *Property*: ``Alphabetic``, ``Math``, etc..  For example, the
*Property* ``Lowercase`` is the collection of the *Category* ``Ll``
plus the *Property* ``Other_Lowercase``.

``Other_Lowercase``, in case you were wondering, includes the likes of
``U+00AA, FEMININE ORDINAL INDICATOR`` and ``U+00BA, MASCULINE ORDINAL
INDICATOR``, for example.

:file:`utils/Unicode/DerivedCoreProperties.txt` defines other
Properties such as ``ID_Start`` (the first code point of an
identifier) and ``ID_Continue`` (subsequent code points for
identifiers).  I'm not sure where they get their information from as
surely such a set is language-specific?  You are welcome to read
`UNICODE IDENTIFIER AND PATTERN SYNTAX
<http://www.unicode.org/reports/tr31/>`_ to understand their thinking.

PropList.txt
------------

:file:`utils/Unicode/PropList.txt` is a fairly short file with more
Properties.  Here we're specifically looking to pick up on the
``White_Space`` Property.

If you did trust their ``ID_Start`` then you might want to be aware of
their ``Other_ID_Start``, defined in this file, too.

Again, it's hard to see how they can clearly define a
``Pattern_White_Space`` and ``Pattern_Syntax`` Properties.

GraphemeBreakProperty.txt
-------------------------

:file:`utils/Unicode/GraphemeBreakProperty.txt` is a fairly short file
with more breaks-between-things Properties.

Reserved
--------

Reserved code points are a feature.  In particular they are not listed
in :file:`utils/Unicode/UnicodeData.txt` but are referenced in the
three properties files.  That might not be an issue except
:file:`utils/Unicode/GraphemeBreakProperty.txt` lists them as
*Property* ``Control`` -- which is a Property we are interested in.

Of course, so long as we only create summary information for code
points in :file:`utils/Unicode/UnicodeData.txt` then we're good.

Summarising
===========

Across these four files there are 65 Properties: 

  ``ASCII_Hex_Digit`` ``Alphabetic`` ``Bidi_Control`` ``CR``
  ``Case_Ignorable`` ``Cased`` ``Changes_When_Casefolded``
  ``Changes_When_Casemapped`` ``Changes_When_Lowercased``
  ``Changes_When_Titlecased`` ``Changes_When_Uppercased`` ``Control``
  ``Dash`` ``Default_Ignorable_Code_Point`` ``Deprecated``
  ``Diacritic`` ``Extend`` ``Extender`` ``Grapheme_Base``
  ``Grapheme_Extend`` ``Grapheme_Link`` ``Hex_Digit`` ``Hyphen``
  ``IDS_Binary_Operator`` ``IDS_Trinary_Operator`` ``ID_Continue``
  ``ID_Start`` ``Ideographic`` ``Join_Control`` ``L`` ``LF`` ``LV``
  ``LVT`` ``Logical_Order_Exception`` ``Lowercase`` ``Math``
  ``Noncharacter_Code_Point`` ``Other_Alphabetic``
  ``Other_Default_Ignorable_Code_Point`` ``Other_Grapheme_Extend``
  ``Other_ID_Continue`` ``Other_ID_Start`` ``Other_Lowercase``
  ``Other_Math`` ``Other_Uppercase`` ``Pattern_Syntax``
  ``Pattern_White_Space`` ``Prepend`` ``Prepended_Concatenation_Mark``
  ``Quotation_Mark`` ``Radical`` ``Regional_Indicator``
  ``Sentence_Terminal`` ``Soft_Dotted`` ``SpacingMark`` ``T``
  ``Terminal_Punctuation`` ``Unified_Ideograph`` ``Uppercase`` ``V``
  ``Variation_Selector`` ``White_Space`` ``XID_Continue``
  ``XID_Start`` ``ZWJ``

and (the) 29 `General Category Values
<https://www.unicode.org/reports/tr44/#General_Category_Values>`_
covering Letters, Marks, Numbers, Punctuation, Symbols, Separators and
Others.

The 65 Properties is vexing.  Firstly, they wouldn't fit as bit-fields
in a 64-bit integer but also we need to take care as the *groupings of
Categories*, such as ``Letter``, are, presumably, slightly disjoint
from the *Property* ``Alphabetic`` (in
:file:`utils/Unicode/DerivedCoreProperties.txt`) which is defined as
``Uppercase + Lowercase + Lt + Lm + Lo + Nl + Other_Alphabetic``.

Ultimately, we're looking to define a set of testable C bitfields for
*our* various purposes, not necessarily serving any Unicode question.

SRFI-14 asks for quite a lot of char-sets which are derived as (with P
for Property, C for Category):

.. csv-table:: SRFI-14 char-set definitions
   :widths: auto
   :align: left

   lower-case,			P Lowercase
   upper-case,			P Uppercase
   title-case,			C Lt
   letter,			P Alphabetic
   digit,			C Nd
   graphic,			C L* + C N* + C M* + C S* + C P*
   white-space,			P White_Space
   punctuation,			C P*
   symbol,			C S*
   hex-digit,			P ASCII_Hex_Digit
   blank,			C Zs + 0009
   control,			P Control
   regional-indicator,		P Regional_Indicator
   extend-or-spacing-mark,	P Extend + P SpacingMark
   hangul-l,			P L
   hangul-v,			P V
   hangul-t,			P T
   hangul-lv,			P LV
   hangul-lvt,			P LVT

JSON5 through ECMAScript and, in particular, the definition of
`Identifier <https://262.ecma-international.org/5.1/#sec-7.6>`_, wants
to know *Categories* ``Lu`` ``Ll`` ``Lt`` ``Lm`` ``Lo`` ``Nl`` ``Mn``
``Mc`` ``Nd`` ``Pc`` and *Property* ``ZWJ`` (and ``ZWNJ``) although it
defines those last two as fixed values.

Schoenenberger also distingushes:

* between decimal and fractional numeric values as the fractional part
  is to be represented by a string, say, "1/4"

  That's useful.

  `Note that <http://www.unicode.org/reports/tr44/#Numeric_Type>`_:

    (8) If the character has the property value Numeric_Type=Numeric,
    then the ``Numeric_Value`` of that character is represented with a
    positive or negative integer or rational number in this field

  and that, as of 13.0.0, there are no negative integers and a single
  negative rational.

* where the upper/lower/title case causes an expansion in the number
  of code points

  We'll skip that, today.

Across the needs of SRFI-14 and JSON5 we have 24 or so distinguishable
flags (27 if we included the "expands" cases) with zero (flags)
meaning "Unassigned".  Plenty of room in a 32-bit flags bit-field.

----

We can create nominal C bit-field flags for those and then create
our (originally 430) variations by generating the stringified static C
structure elements:

.. code-block:: c

   { flags, Category, UC offset, LC offset, TC offset, Numeric Value }

to get 465 "summary" code points.

As there's more than 256, references to these must be two bytes, that
is the entire page table must be ``uint16_t``.  Even without the flags
field we still had the original 430 which, again, is more than 256.

We now need a page indirection table to get us from a code point (one
of #x110000) to a page in the page table and this indirection table
will be :samp:`#x110000 / {page size}` entries.

When we generate page tables (of 256 references to the 465 variants)
we get some duplication of the "used" pages -- used by valid code
points -- sometimes dramatically different (see the **#pg** vs **used
pg** columns below).

Again, depending on how many unique pages we have, determines whether
one or two bytes is required for the page indirection table references
into the page table.

We can calculate the number of entries in the page table (:samp:`{unique pages}
* {bytes per page ref} * {page size}`).

The total number of bytes we require in the C code point to variation
implementation is the sum of those two tables.

----

The next question comes about that choice of a page size of 256.  What
if we vary it a bit?  Let's try some numbers:

(these numbers are approximate as the code evolves)

.. csv-table:: effects of varying page size
   :header: pgsz,  pages, #pg, used pg,  bytes, (bytes formula)
   :widths: auto
   :align: left

   1024, 1088, 55, 62, 113728, (  1088 * 1 +  55 * 2 * 1024)
   512, 2176, 89, 104, 93312, (  2176 * 1 +  89 * 2 *  512)
   256, 4352, 146, 183, 79104, (  4352 * 1 + 146 * 2 *  256)
   128, 8704, 242, 329, 70656, (  8704 * 1 + 242 * 2 *  128)
   64, 17408, 398, 616, 85760, ( 17408 * 2 + 398 * 2 *   64)
   32, 34816, 595, 1175, 107712, ( 34816 * 2 + 595 * 2 *   32)
   16, 69632, 745, 2286, 163104, ( 69632 * 2 + 745 * 2 *   16)

Here,

* **pgsz** is our variable page size

* **pages** is how many **pgsz** pages there are for #x110000 code
  points

* **#pg** the number of *unique* **used pg**

  Notice how for smaller and smaller page sizes the chances of you
  seeing duplicates increases dramatically.

  The downside is the increase in the number of pages because of the
  small page size.

* **used pg** are pages with valid code points in them

* **bytes** and formula

  As noted, if the number of pages you need (**#pg**) is less than 256
  you only need to use one byte offsets in the initial page
  indirection table (for Schoenenberger, ``PageIndex[cp >> 8]``).

  The second indirection table (for Schoenenberger,
  ``InfoIndex[page][cp & 0xff]``) is always a two byte offset (into
  the 465 entry summary information table) multiplied by the number of
  pages you require (**#pg**) and the size of the pages (**pgsz**).

From which we can see a sweet spot, for this arrangement of flags
etc., around a page size of 128 requiring 70656 bytes in C static
tables.  Schoenenberger used a page size of 256 for his arrangement.

The final sizing element is fairly fixed as it is 465 times the size
of an ``idio_USI_t`` holding the summarised code point information.
For the upper/lower/title case offsets, some of the relative numbers
are over 32k meaning we can't use an ``int16_t``, therefore it must be
an ``int32_t`` which wastes a bit of space as the vast majority are 0
or small offsets.

An ``idio_USI_t``, then, is 32 bytes, and therefore the variants
tables is 465 times that, 14880 bytes.

So a grand total of 85536 bytes (70656 + 14880) to store everything
*we* need to know about Unicode.

C Tables
========

With this information generated by :file:`bin/gen-usi-c` as
:file:`src/usi.[ch]` we can now do a number of useful things:

#. we could create authentic Unicode equivalents to
   :manpage:`isdigit(3)` and friends -- although we don't -- assuming
   the Categories and Properties we have chosen are enough to answer
   all the questions we have

#. we can have :file:`src/usi-wrap.c` generate the SRFI-14 char-sets
   on the fly during startup.

   This saves a huge amount of time as :program:`idio` doesn't have to
   read and parse (and then still have to generate) the SRFI-14
   char-sets from :file:`lib/unicode.full.idio` -- which, in turn, no
   longer needs to exist.

.. include:: ../../commit.rst

