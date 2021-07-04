.. include:: ../../global.rst

.. _bignums:

*******
Bignums
*******

I mentioned before that I've taken :ref-author:`Nils M Holm`'s (2009)
:ref-title:`S9fES` (:cite:`S9fES`) bignum implementation and
re-written it for :lname:`Idio`.

Bignums are, um, big numbers.  *How big?* Quite big.  The goal is
ostensibly arbitrary precision numbers which use as many significant
digits as required.  Both integer and floating point maths.

You might want to ask, how many significant digits do I need to do
real-world maths?  I have two sobering examples:

* No modern treatise is complete without at least one relevant XKCD:

  .. image:: https://imgs.xkcd.com/comics/coordinate_precision.png
     :alt: XKCD: Coordinate Precision
     :target: https://xkcd.com/2170/

  .. aside:: `Angels on the head of a pin?
             <https://en.wikipedia.org/wiki/How_many_angels_can_dance_on_the_head_of_a_pin%3F>`_
             *We've got you now!*

  which, reading the bottom row suggests we need 17 significant digits
  to track the latitude and longitude of individual *atoms*.

* This 2016 question to NASA on `how many decimals of PI we really
  need
  <https://www.jpl.nasa.gov/edu/news/2016/3/16/how-many-decimals-of-pi-do-we-really-need/>`_.

  The upshot of which is that:

  #. 15 digits for the circumference a sphere of radius 12.5 billion
     miles (encompassing Voyager 1 at the time, now only Voyager 2 --
     check `where is Voyager
     <https://voyager.jpl.nasa.gov/mission/status/>`_ for their
     current whereabouts) to an accuracy of 1.5 *inches*

     The same 15 digits would have your odometer off by the size of a
     *molecule* (whose sizes vary, granted) had you cycled/kayaked
     around the Earth's equator.

  #. 40 digits to calculate the circumference of a circle the size of
     the visible universe (46 billion light years -- at the time) to
     an accuracy equal to the diameter of a hydrogen atom

So, not really very many required at all, I'm thinking.

As mentioned previously, many projects choose to use the GMP_ (GNU
Multi Precision Arithmetic Library) but my selfish need-to-know means
we *must* have one we've figured out for ourselves -- albeit by
re-implementing someone else's code.

(We must re-implement the :ref-title:`S9fES` version because the GCs
for :lname:`Idio` and :ref-title:`S9fES` are quite different.)

:ref-title:`S9fES` (and GMP) aren't the only implementations we could
look at.  I see that `Emacs <https://www.gnu.org/software/emacs/>`_
comes with a *mini-gmp* library though that is, so far as I can tell,
simply a port of the :file:`mini-gmp.c` code included in GMP.

:ref-author:`Fredrik Johansson`'s :ref-title:`mpmath` library for
:lname:`Python` is another alternative.

However, we are reasonably confident that the :ref-title:`S9fES` code
is targeting :lname:`Scheme` so is a decent place to start.

Implementation
==============

The broad thrust of the mechanics is long-hand arithmetic using arrays
of ``intptr_t``\ s for the digits in the *mantissa*/integer.  The
array elements are called segments, here.  We'll need an *exponent*
and some flags (integer, real, etc.) and the implementation uses the
top bit of the most significant segment as the sign bit for integers
-- all the other segments for an integer have the top bit ignored.

How many decimal digits can fit in a machine word?  log\
:sub:`2`\ (10) is 3.322, that is each decimal digit uses 3.322 binary
bits.  19 of those would be 63.12 bits which means we couldn't also
fit the sign bit in to a 64-bit word.  So, round that down and we can
fit 18 decimal digits in a 64-bit word.  Similarly 9 decimal digits in
a 32-bit word.

.. aside:: *And* keep an eye on those pesky angels.

Certainly, then, with a 64-bit system we can do decent *space maths*
with a single segment.  *Cool!*

That's the maximum number of decimal digits per word you could squeeze
in and the algorithm allows you to define a particular number of
digits per word (up to the maximum).

As mentioned previously there is a slight trick to the way numbers are
handled in that we don't attempt to pack data into our segments with
maximal efficiency.  Instead we take a step back and say, OK, we can
fit 18 decimal digits into our 64-bit word.  In other words, the
absolute decimal value 1,000,000,000,000,000,000 (19 digits) marks
overflow.  If we have overflowed we can account for *carry* in our
long-hand arithmetic and therefore avoid the undefined behaviour that
plagues integer maths in :lname:`C`.

.. sidebox::

   Obviously, ``pi`` (π) is a `transcendental number
   <https://en.wikipedia.org/wiki/Transcendental_number>`_ and any
   numeric representation of it should be inexact.

   Inexactness is transitive so any use of ``pi`` results in another
   inexact number.

:lname:`Scheme`'s number tower supports slightly more interesting
numbers than many programming languages in that it has the concept of
*exact* and *inexact* numbers.  Inexact numbers are where we've lost
precision because of rounding errors or, because we can, we were given
an inexact number in the first place.  *I* don't have any immediate
use for inexact numbers in their own right but someone might.

Summing that up:

* we need some flags which can be type-specific.  A bignum is going to
  be an integer or a real and if it is a real then we need a flag for
  being negative and another for being inexact.

  I've thrown in a not-a-number although it's not used.

  .. code-block:: c
     :caption: gc.h

     #define IDIO_BIGNUM_FLAG_NONE          (0)
     #define IDIO_BIGNUM_FLAG_INTEGER       (1<<0)
     #define IDIO_BIGNUM_FLAG_REAL          (1<<1)
     #define IDIO_BIGNUM_FLAG_REAL_NEGATIVE (1<<2)
     #define IDIO_BIGNUM_FLAG_REAL_INEXACT  (1<<3)
     #define IDIO_BIGNUM_FLAG_NAN           (1<<4)

* we need an exponent and mantissa.  We'll use an ``int32_t`` exponent
  because...

  .. sidebox::

     because *we can*.  So what if there are only 10\ :sup:`80` atoms
     in the universe?  You're obviously not including all the other
     universes!

  Well, from a practical perspective, because it is a separate field
  in the ``idio_bignum_s`` structure and we don't have any others
  meaning it **will** consume a machine word.  So, 32 bits for a
  machine word on a 32-bit system and we'll take the hit on a 64-bit
  system for consistency.

  .. code-block:: c
     :caption: gc.h

     typedef int32_t IDIO_BE_T;

     typedef struct idio_bignum_s {
         IDIO_BE_T exp;
	 IDIO_BSA sig;
     } idio_bignum_t;

     #define IDIO_BIGNUM_FLAGS(B)	((B)->tflags)
     #define IDIO_BIGNUM_EXP(B)		((B)->u.bignum.exp)
     #define IDIO_BIGNUM_SIG(B)		((B)->u.bignum.sig)

  where ``sig`` is our *significand array* of segments:

  .. code-block:: c
     :caption: gc.h

     typedef struct idio_bsa_s {
         size_t refs;
	 size_t avail;
	 size_t size;
	 IDIO_BS_T *ae;
     } idio_bsa_t;

     typedef idio_bsa_t* IDIO_BSA;

     #define IDIO_BSA_AVAIL(BSA)	((BSA)->avail)
     #define IDIO_BSA_SIZE(BSA)		((BSA)->size)

  From ``refs`` you can deduce that I had an intention to use
  reference counting for these significand arrays as the low-level
  mechanics of bignums didn't seem appropriate for the main GC to get
  involved in.  It turns out no reference counting occurs (other than
  creation and destruction).

  ``avail`` is the number of segments in the significand array and
  ``size`` is the number in use.  That might seem a bit odd but shift
  operations will reduce the number of significant digits in use which
  will trip over segment boundaries.

  Note that the significand array is not fixed in the sense that as
  the number is being constructed the array may grow.

  Here, our ``pi`` inexactness comment comes to the fore.  We
  (correctly) construct it with 61 significant figures (why not?) but,
  in normalising the constructed bignum back into the nominal 18
  digits we clearly truncated this four (or eight) segment number down
  to one (or two) and flagged it as inexact.  Job done!

  The definition should really start ``#i3.14159...`` to avoid any
  ne're-do-wells fiddling in :file:`src/bignum.h` and changing the
  defaults.

* we have the usual accessors seen above with the slightly more
  interesting array accessors:

  .. code-block:: c
     :caption: gc.h

     #define IDIO_BSA_AE(BSA,i)		((BSA)->ae[i])

     #define IDIO_BIGNUM_SIG_AE(B,i)	IDIO_BSA_AE((B)->u.bignum.sig,i)

* we have some bignum definitions:

  .. code-block:: c
     :caption: bignum.h

     #ifdef __LP64__
     #define IDIO_BIGNUM_MDPW          18
     #define IDIO_BIGNUM_DPW           18
     #define IDIO_BIGNUM_INT_SEG_LIMIT 1000000000000000000LL
     #define IDIO_BIGNUM_SIG_SEGMENTS  1
     #else
     #define IDIO_BIGNUM_MDPW          9
     #define IDIO_BIGNUM_DPW           9
     #define IDIO_BIGNUM_INT_SEG_LIMIT 1000000000L
     #define IDIO_BIGNUM_SIG_SEGMENTS  2
     #endif

Where ``IDIO_BIGNUM_SIG_SEGMENTS`` is the maximum number of segments
we will use.  Suffice it to say that whilst the results will be more
accurate calculations becomes exponentially longer the more segments
you use.  Here, 32-bit computers using two segments will be to some
degree slower than 64-bit machines using one segment.

Bignums are comparatively expensive to operate -- they require memory,
time to consume, time to operate with and time to print out -- so we
should avoid them if necessary.  Unfortunately the opportunities to
avoid them are slim.

Reading
=======

Reading is a two-step process.

#. In the reader, ``idio_read_number_C()`` in :file:`read.c` we are
   concerned with *recognising* a number, a syntactic check of sorts

   Actually, there's another number-recogniser/constructor,
   ``idio_read_bignum_radix()`` in :file:`read.c` (which I suppose
   should have a trailing ``_C`` to be consistent) for a particular
   input form.

#. In ``idio_bignum_C`` in :file:`bignum.c` we are concerned with
   *constructing* a number from the character-based representation

The Reader
----------

A generic number (in :lname:`Scheme`, here from `Numbers in Scheme
<http://docs.racket-lang.org/reference/reader.html#%28part._parse-number%29>`_)
is something like:

* ``[+-]?[0-9]+``

* ``[+-]?[0-9]+.[0-9]*``
  
* ``[+-]?[0-9]+.[0-9]*E[+-]?[0-9]+``

(There must be a numeric part before any ``.`` otherwise it will be
interpreted as the ``value-index`` operator.)

The exponent character, ``E`` in the last example, can be one of
several characters:

* for base-16 numbers (see below): ``e`` and ``E`` quite obviously
  clash with the possible digits of hexadecimal numbers so for base-16
  numbers you can use the exponent characters ``s``/``S`` or
  ``l``/``L`` -- I don't know what the history of those are.

* other exponent-able numbers can use ``d``/``D``, ``e``/``E``,
  ``f``/``F`` -- and ``s``/``S`` and ``l``/``L`` -- which seem to be
  the generally accepted set of exponent characters.

``+10``, ``1.``, ``-20.1``, ``0.3e1``, ``-4e-5``, ``6L7``

``idio_read_number_C()`` in :file:`read.c` will check the overall
format and make some decisions about the way forward:

* if the number is definitely not an integer, ie. it has:

  - a decimal point

  - an exponent

  - is inexact

  then it will call ``idio_bignum_C()``

* has a small number of digits then we can construct a fixnum
  directly.

  The guesstimate is based on that 3.32 bits per decimal digit --
  which we'll round up to four for safety.  With :samp:`{i}` digits
  we'll require :samp:`4{i}` bits.  The fixnum implementation can cope
  with 8 (technically, ``CHAR_BIT``) bits per byte of an ``intptr_t``
  less the number of tags bits.  If one is less than the other then
  we're good to go.

  (That should be more closely analysed for leading sign characters.)

  ``idio_fixnum_C()`` in :file:`fixnum.c` uses :manpage:`strtoll(3)`
  which I think is non-controversial and we shouldn't be pushing the
  boundaries of an ``intptr_t``.

* otherwise we call ``idio_bignum_C()`` for a full conversion to a
  bignum then attempt to convert the bignum back to a fixnum with
  ``idio_bignum_to_fixnum()`` in :file:`bignum.c`.

  (Some fixnums may not be realised by this conversion.  I need to
  (re-)\ *do the math*.)

Non-base-10 Numbers
^^^^^^^^^^^^^^^^^^^

There are several reader input forms for non-base-10 numbers all of
which call ``idio_read_bignum_radix()`` in :file:`read.c` with a
different *radix*:

.. csv-table:: Non-base-10 reader number formats
   :header: "form", "radix", "example", "decimal equivalent"
   :widths: auto
   :align: left

   ``#b``, 2,  ``#b101``, 5
   ``#o``, 8,  ``#o101``, 65
   ``#d``, 10, ``#d101``, 101
   ``#x``, 16, ``#x101``, 257

``idio_read_bignum_radix()`` supports bases up to 36 (using 0-9 then
a-z/A-Z) although there are no specific reader input forms.
:samp:`read-number {str} [{radix}]` can be used to read numbers in
your specialised base-23 number-system.

``idio_read_bignum_radix()`` is a slight hybrid recogniser/constructor
in that:

* it initialises an accumulated bignum value to zero

* as it walks through the input stream asserting that the next
  character is appropriate for the radix then

  * multiplies the accumulated value by the radix (base) then

  * adds to the accumulator the (decimalised) value of the character

bignum.c
--------

:file:`bignum.c` looks fearsomely complex but that's because there's:

* a sort of combinatorial explosion for handling integers and reals

* a variety of calls to create bignums from :lname:`C` integers and
  construct :lname:`C` integers from large (but not too large) bignums

* printing bignums is possibly complicated

* actual bignum operations (add, subtract etc.)

Bignums are normalized after most operations to provide some
consistency:

.. code-block:: idio-console

   Idio> 1234e-3
   1.234e+0
   Idio> 12340000e-7
   1.234e+0

there's a ``bignum-dump`` left in for debug.  On a 64-bit machine:

.. code-block:: idio-console

   Idio> pi
   #i3.14159265358979323e+0
   Idio> bigum-dump pi
   idio_bignum_dump:  Ri segs[ 1]: 314159265358979323 e-17

and on a 32-bit machine:

.. code-block:: idio-console

   Idio> pi
   #i3.14159265358979323e+0
   Idio> bigum-dump pi
   idio_bignum_dump:  Ri segs[ 2]: 314159265 358979323 e-17

What you can see is that ``pi`` is an *inexact* number, ``#i`` in its
normal printed form.  The ``bignum-dump`` output has some flags ``Ri``
for *real* number and *inexact*, that it use 1 or 2 segments
(machine-specific) and then each segment is printed in its decimal
form and finally the exponent is printed.

What you can readily see from the internal dumped format is that the
significand array is storing the significant digits as a (long-hand)
integer and the exponent is scaled appropriately.

Writing
=======

``idio_bignum_as_string()`` in :file:`bignum.c` is called from
``idio_as_string()`` in :file:`util.c`.

Integers
--------

Integer number bignums are printed by
``idio_bignum_integer_as_string()`` but the format is fixed to being
*decimal*.

    The problem relates to us having split the value of the bignum
    into DPW *decimal* segments.  If I've got the first of two
    segments in my hands and its value is 1, that won't guarantee to
    be 1 in any other format.

    For example, imagine we can store 3 digits per word then 1234 will
    be stored as 1 and 234.  Then the 1 in the first segment won't
    guarantee to be a 1 in the hex (#x4D2), octal (#o2322) or binary
    (#b10011010010) -- OK, a reasonable chance with the binary.

    To generate some other :samp:`{base}`, hexadecimal, say, we would
    have to do the reverse of the reader's input method for
    non-base-10 numbers.  We would need to calculate :samp:`1234 %
    {base}`, subtract that from 1234, divide the result by
    :samp:`{base}` and loop around again until the result was zero.

    So, *do-able*, but expensive.  I haven't found a need.

You can only usefully specify a precision which, for an integer, just
becomes a padding with leading zeroes.  You can get this through
:ref:`format <format>` or one of the *printf* functions.

Reals
-----

Real number bignums are printed by ``idio_bignum_real_as_string()``
which supports ``e`` and ``f`` :manpage:`printf(3)`-style formatting.
You can get either of these through :ref:`format <format>` or one of
the *printf* functions.

The default output format is still the :lname:`Scheme`-ish one -- or
rather the original :ref-title:`S9fES` format -- which is similar to
the :manpage:`printf(3)` ``e`` except prints full precision.

Operations
==========

:samp:`bignum? {value}`

      is :samp:`{value}` a bignum

:samp:`real? {bignum}`

      is bignum :samp:`{bignum}` a real (ie. not an integer)

:samp:`exact? {number}`

      is number :samp:`{number}` an exact number (ie. an integer or
      not inexact)

:samp:`inexact? {number}`

      is number :samp:`{number}` an inexact number (ie. not an integer
      or is inexact)

:samp:`exact->inexact {number}`

      an inexact version of :samp:`{number}` is returned

:samp:`inexact->exact {number}`

      an exact version of :samp:`{number}` is returned

:samp:`mantissa {number}`

      the mantissa of :samp:`{number}` is returned

:samp:`exponent {number}`

      the exponent of :samp:`{number}` is returned

:samp:`bignum-dump {bignum}`

      display some of the internal structure of :samp:`{bignum}`


.. include:: ../../commit.rst

