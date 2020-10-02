.. include:: ../../global.rst

.. _bitsets:

*******
Bitsets
*******

Bitsets exist because regular expression handling required Unicode
support and that in turn meant we needed something to handle yes/no
state information for a set 2\ :sup:`21` bits wide.  *Is this a
lowercase letter?*

That code doesn't actually use bitsets blindly as it a) uses
*charsets* which b) take advantage of several Unicode planes being
unassigned to create a sparse array of bitsets.

Of course, now bitsets exist you can use them for any set of on/off
flags.

I've lost my reference for where I got the inspiration for the
implementation from -- an answer on `Stack Overflow`_, no doubt -- but
the implementation is entirely self-inflicted.

In :lname:`C` we can *bit-twiddle* to our hearts content on things up
to a machine word in size, after that we're out of luck.  Even a
single Unicode plane of 2\ :sup:`16` bits is a bit more than our
32-bit or 64-bit machine word will cope with.

The answer is, of course, an array of machine words with some suitable
indexing to get us to the right word and then we *bit-twiddle* with
the best of them.

Far more effort goes into reading and writing bitsets in a
reader-friendly format, though.  The need for a reader format derives
from the observation that Unicode isn't fixed -- there'll be another
version along soon -- and as good language implementers we should be
using the latest and greatest and we'd rather auto-generate these
tables than fix them into :lname:`C`.

Implementation
--------------

As noted above, the implementation is an array of ``unsigned long
int``\ s:

.. code-block:: c
   :caption: gc.h

    typedef struct idio_bitset_s {
	size_t size;
	unsigned long *bits;
    } idio_bitset_t;

    #define IDIO_BITSET_SIZE(BS)	((BS)->u.bitset.size)
    #define IDIO_BITSET_BITS(BS,i)	((BS)->u.bitset.bits[i])

We want a handy macro:

.. code-block:: c
   :caption: bitset.h

    #define IDIO_BITS_PER_LONG (CHAR_BIT * sizeof (unsigned long))

and then we're off.  The constructor has the basic trick of
determining the number of ``unsigned long``\ s in the array by using
our handy ``IDIO_BITS_PER_LONG`` and adding one:

.. code-block:: c
   :caption: bitset.c

    IDIO idio_bitset (size_t size)
    {
	IDIO bs = idio_gc_get (IDIO_TYPE_BITSET);

	IDIO_BITSET_SIZE (bs) = size;
	bs->u.bitset.bits = NULL;

	if (size) {
	    size_t n = size / IDIO_BITS_PER_LONG + 1;
	    IDIO_GC_ALLOC (bs->u.bitset.bits, n * sizeof (unsigned long));
	    memset (bs->u.bitset.bits, 0UL, n * sizeof (unsigned long));
	}

	return bs;
    }

We then have the broad swathe of expected operations on a bitset all
of which use a simple index, :samp:`{bit}`:

.. code-block:: c
   :caption: bitset.c

   IDIO idio_bitset_set (IDIO bs, size_t bit)
   IDIO idio_bitset_clear (IDIO bs, size_t bit)
   IDIO idio_bitset_ref (IDIO bs, size_t bit)

These will all use the same trick to get the correct ``unsigned long``
in the array and then the bit within that ``unsigned long`` is simply
:samp:`{bit} % IDIO_BITS_PER_LONG`.

Of course they have their :lname:`Idio` equivalents:
:samp:`bitset-set! {bs} {bit}` etc..

The regular expression code wants to perform some operations on
bitsets as a whole and so there's various: ``merge-bitset``,
``and-bitset``, ``ior-bitset``, ``xor-bitset`` and ``not-bitset`` (to
toggle the entire bitset) all of which iterate over the ``unsigned
long``\ s performing the operation as required.

There's another interesting operation, ``subtract-bitset``.  Here, in
Unicode terms, you might imagine having some derived charset and then
removing all the letters from it.

Equality for bitsets (beyond ``eq?``) is just as involved as you have
to iterate through comparing each ``unsigned long``.

A final, much more *functional* operation is
:samp:`bitset-for-each-set {bs} {func}` which, reflecting on the name,
is a slightly clumsy way of asking for a function to be run for each
bit that is set in the bitset.  The function will be called with the
(integer) value of the bit that is set.

Given a 3-bit bitset with the first and last bits set, then by
calling:

.. code-block:: idio

   bitset-for-each-set bs f

we would expect the following calls to be invoked:

.. code-block:: idio

   f 0
   f 2

Reading and Writing
-------------------

I'm combining these sections into one as the implementations are
relatively complex and we're only really concerned about the format.

The basic reader format is:

.. parsed-literal::

   #B{ *size* ... }

:samp:`{size}` is a decimal number.  The other indexing numbers coming
are all hexadecimal.  I decided to keep the *size* as decimal as it is
a bit more human friendly.  It's a moot point.

The bits are displayed as ``0``\ s and ``1``\ s in blocks of eight (or
less if we're at the end of the bitset) to help casual human scanning.

So our 3-bit bitset might look like ``#B{ 3 101 }``.

The bits' order is left-to-right and are indexed starting at zero.  So
``#B{ 3 100 }`` means the first bit (with index 0) is set and the
other two are not.  ``#B{ 3 001 }`` means the last bit (with index 2)
is set and the other two are not.

So, you can imagine, the first pass for Unicode printed out several
lines with *at least* a million characters per line -- I guess it
would be 2\ :sup:`21` ``0``\ s and ``1``\ s plus another 2\ :sup:`18`
spaces between the blocks of 8.

Even :program:`less` didn't like that and would lock up (going
backwards).  Not... *great*.

Careful analysis revealed *quite a lot* of consecutive zeroes, so we
can eliminate those so long as we prefix the *next* block of
not-all-zeroes with an offset which, given we're chunking into groups
of 8, is a hexadecimal number.  Once we've picked up the current
offset then the next block's offset is implicitly 8 further on.

If we take our 3-bit example and insert 8 leading zeroes, instead of
``#B{ 11 00000000 101 }``, we might have: ``#B{ 11 8:101 }``.

Which is good and :program:`less` is a bit happier.

Now we notice long ranges of consecutive ones which we can chunk
together with a range identifier (hex, again): :samp:`{first
block}-{last block}` where we are saying that it is all ones from the
start of the :samp:`{first}` block to the end of the :samp:`{last}`
block.  If the range is only one block you end up with the curious
looking ``80-80``, say, which means bits are all ones from index 0x80
through to 0x87.

Another 11-bit example might be, then, ``#B{ 11 0-0 8:101 }`` which
says that all 11 bits *except* the 10\ :sup:`th` (index 9, of course!)
are set.

So the variations are:

* :samp:`{first}-{last}` is saying all-ones from the start of
  :samp:`{first}` to the end of :samp:`{last}`.

  The next offset is implicitly :samp:`{last} + 8`

* :samp:`{offset}:...` where the offset of the first ``0`` or ``1`` in
  ``...`` is :samp:`{offset}`

  The next offset is implicitly :samp:`{offset} + 8`

* :samp:`...` where the offset is implied based on one of the above or
  simply incremented from the previous block.

ASCII
^^^^^

By way of example, we can use the familiar ASCII character set to
illustrate the variations.  ASCII is 128 characters so we need 128-bit
bitsets to represent various categories.

The *lowercase* letters would be ``#B{ 128 60:01111111 68-70
11100000 }`` which reads as the seven starting at 0x61 plus 0x68-0x77
and then the next three: 0x78, 0x79, 0x7A.  Which looks about right
(he says, carefully checking :manpage:`ascii(7)`).

Similarly:

* *digits* is ``#B{ 128 30-30 11000000 }``

* *hex-digits* is ``#B{ 128 30-30 11000000 01111110 60:01111110 }``
  which should be 0-9 and a-f and A-F

* *whitespace* is ``#B{ 128 8:01111100 20:10000000 }`` which looks
  like horizontal tab, newline, vertical tab, form feed, carriage
  return and space.
  
* *punctuation* is ``#B{ 128 20:01110111 11101111 38:00110001 10000000
  58:00011101 78:00010100 }``

  Notice a couple of gaps in the first two blocks:

  * U+0024 (DOLLAR SIGN) is not marked as punctuation.  It is in the
    ``Sc`` category, ie. a *Currency Symbol*.

  * U+002B (PLUS SIGN) is in the ``Sm`` category, *Math Symbol*.

The problem, here, in terms of the definitions of constituents of sets
is that these are Unicode's definitions of categories which may vary
from expectations.

Unicode Char-sets
^^^^^^^^^^^^^^^^^

A quick digression while we're here.

Unicode produces a wealth of character set data in its `UCD
<http://www.unicode.org/Public/UCD/latest/>`_ (from which you usually
want the :file:`ucd` subdirectory).

This is a *ton* of information.  Following :ref-author:`John Cowan`'s
`note
<https://srfi.schemers.org/srfi-14/contrib/unicode-2019/CharsetDefs.html>`_
relating to :lname:`Scheme`'s `SRFI-14`_ (Character-set library) there
are three useful documents (which are duplicated within the
:lname:`Idio` source code).

The breakdown of each field of each file is documented under `Property
Definitions
<http://www.unicode.org/reports/tr44/#Property_Definitions>`_ --
you'll need to search down for each file.


#. :file:`.../utils/Unicode/UnicodeData.txt` is the main list of all
   allocated Unicode code points.

   It uses ranges in case you're wondering why it isn't 150k lines
   long.

   This is the primary source and for us has some key fields:

   * (field 2) *General_Category*: letter, digit, punctuation etc. see
     `General Category Values
     <https://www.unicode.org/reports/tr44/#General_Category_Values>`_

     Note that the category is specific: ``Lu`` is *letter uppercase*
     and ``Ll`` is *letter lowercase* but that first character, ``L``
     of the category is also used for further classification in the
     form of ``L*`` meaning *any kind of letter*.

   * (field 12) *Simple_Uppercase_Mapping*

   * (field 13) *Simple_Lowercase_Mapping*

   If you're wondering about *Titlecase*, Unicode's FAQ entry `Q: What
   is titlecase? How is it different from uppercase?
   <https://unicode.org/faq/casemap_charprop.html#4>`_ and `Grammar
   Monster
   <https://www.grammar-monster.com/lessons/capital_letters_title_case.htm>`_
   might help explain.

#. :file:`.../utils/Unicode/PropList.txt` puts more characters into
   categories where their *General_Category* was something else.

   For example, U+0009 through U+000D are nominally ASCII Control
   characters, in the Category ``Cc`` but are in :file:`PropList.txt`
   tagged as *White_Space*.

#. :file:`.../utils/Unicode/DerivedCoreProperties.txt` is similar to
   :file:`PropList.txt`

If we parse all of that (see
:file:`.../utils/extract-unicode-char-sets.idio`) we can build up some
tables (of tables ...).

As noted, the sparse char sets are an array of 17 Unicode planes where
each plane is represented by a bitset or ``#f``.

A bitset for a plane is 2\ :sup:`16` (65,536) entries -- meaning an
underlying array of 2\ :sup:`11` or 2\ :sup:`10` ``unsigned long``\ s!
That's partly why we're keen to make the array sparse.  Why would we
have planes 4 through 13 waste 8kB *each* when we know there's nothing
in them.

ASCII, BMP0, full
"""""""""""""""""

Loading in the full Unicode set is a lot of data.  For *each*
character set (lowercase, uppercase, etc. -- there are 39 in total!)
we are using 56kB of memory in bitsets to do the mapping.

I mused with the idea of allowing the user to use only ASCII or only
the Basic Multilingual Plane (plane 0) or the full Unicode set and
added unnecessary complexity to
:file:`.../utils/extract-unicode-char-sets.idio` to do so.

The various outputs are in :file:`.../lib/unicode.*.idio`.

At the moment we're stuck with full Unicode only.
