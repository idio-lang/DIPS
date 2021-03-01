.. include:: ../../global.rst

****************
:lname:`C` Types
****************

Overview
========

In principle we don't want to deal with :lname:`C` `data types
<https://en.wikipedia.org/wiki/C_data_types#Main_types>`_ as they are
don't come across as well-defined, for example, an ``int`` could be
16, 32 or 64 bits wide.

On top of that are the numeric promotion rules meaning I can pass a
short where a long is expected and the right thing will happen.  I can
compare almost anything to ``0``.

Someone obviously knows what's going on there but it isn't me.

However, internally, :lname:`Idio` needs to poke about with the system
even just for reading and writing but much more comprehensively for
job control and it needs to transport those results around.

Initially, I wrote all of those system interfaces by hand although I
became increasingly annoyed (with myself) for not handling types
correctly.  Particularly for structures.

Eventually I started the :ref:`c_api` work which required a overhaul
of the handling of :lname:`C` types.

Of course, once that's done it is available for use elsewhere.

C Types
=======

There are fourteen base types, ``int``, etc., plus pointers and
``void``.

``void`` is a little unusual in that it, correctly, is the absence of
a type.  I've stumbled across one ``void`` in a structure (in a
``FILE``) although I avoided that becoming an issue by stopping using
``FILE`` as the underlying type for handling files when I added
*pipe-handles*.

More commonly, you'll see references to pointers to ``void`` (which,
arguably, still doesn't make any sense), in practice meaning a pointer
to an unknown type.

C Base Types
------------

The :lname:`C` base types have a fluid set of possible names which
I've normalised to:

.. sidebox::

   At this point I finally realised after all these years that a
   :lname:`C` ``char`` is neither signed nor unsigned but is the:

       Smallest addressable unit of the machine that can contain basic
       character set.

       --- Wikipedia

   and is therefore, technically, not a numeric type.

   *Who knew?*

.. csv-table:: C types
   :header: :lname:`C`, :lname:`Idio`
   :widths: auto
   :align: left

   ``char``, ``char``
   ``signed char``, ``schar``
   ``unsigned char``, ``uchar``
   ``short``, ``short``
   ``unsigned short``, ``ushort``
   ``int``, ``int``
   ``unsigned int``, ``uint``
   ``long``, ``long``
   ``unsigned long``, ``ulong``
   ``long long``, ``longlong``
   ``unsigned long long``, ``ulonglong``
   ``float``, ``float``
   ``double``, ``double``
   ``long double``, ``longdouble``

There's a separate :lname:`Idio` type for each :lname:`C` type which
we store in a union (of :lname:`C` base types) in the ``struct
idio_s``/``IDIO`` value type:

.. code-block:: c

   #define IDIO_TYPE_C_CHAR        	29
   #define IDIO_TYPE_C_SCHAR       	30
   #define IDIO_TYPE_C_UCHAR       	31
   #define IDIO_TYPE_C_SHORT       	32
   #define IDIO_TYPE_C_USHORT      	33
   #define IDIO_TYPE_C_INT         	34
   #define IDIO_TYPE_C_UINT        	35
   #define IDIO_TYPE_C_LONG         	36
   #define IDIO_TYPE_C_ULONG        	37
   #define IDIO_TYPE_C_LONGLONG        	38
   #define IDIO_TYPE_C_ULONGLONG       	39
   #define IDIO_TYPE_C_FLOAT       	40
   #define IDIO_TYPE_C_DOUBLE      	41
   #define IDIO_TYPE_C_LONGDOUBLE      	42
   #define IDIO_TYPE_C_POINTER     	43

   typedef struct idio_C_type_s {
       union {
	   char			C_char;
	   signed char		C_schar;
	   unsigned char	C_uchar;
	   ...
	   float		C_float;
	   double		C_double;
	   long double		C_longdouble;
	   idio_C_pointer_t    *C_pointer;
       } u;
   } idio_C_type_t;

   struct idio_s {
       ...
       union idio_s_u {
	   ...
	   idio_C_type_t          C_type;
	   ...
       } u;
   };

So, accessing :lname:`C` types involves an extra indirection (more for
a pointer) but otherwise all good.  It all could have been dragged up
a level but no-one's looking closely.

.. rst-class:: center

----

Based on these we can define some basic:

* constructors, eg. :samp:`idio_C_{int}`

* accessors, eg. :samp:`IDIO_C_TYPE_{int}`

* predicates, eg. :samp:`C/{int}?`

  The predicates exist in a ``C`` namespace which is not importable.
  You simply have to use the direct name.

Numeric Operations
^^^^^^^^^^^^^^^^^^

With the best will in the world we can't escape needing to provide
some numeric operations for :lname:`C` types.

All of these pose some problems for us.  By and large we can do
*stuff* on things of the same :lname:`C` type.  Stepping away from
identical types takes us into a combinatorial explosion of
possibilities that the :lname:`C` compiler hides from us.

So I haven't bothered.

C Equality
""""""""""

Integral equality is straightforward but floating point equality, it
turns out, is quite hard.  There is a trick we can use for ``float``
and ``double`` types wherein, the fact that they are fixed-format
32-bit and 64-bit values means, we can convert into a integer and test
the component bits.  This is referred to as :abbr:`Units in Last Place
(ULP)` comparisons and you can read `much
<https://floating-point-gui.de/errors/comparison/>`_ `more
<https://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/>`_
about it.

On the other hand, ``long double``\ s are `not clearly defined
<https://en.wikipedia.org/wiki/Long_double>`_.  They might be 80-bit,
96-bit or 128-bit implementations or even just an alias for
``double``.

I gave up and throw an error if you're trying to compare ``long
double``\ s from :lname:`Idio`.

Arithmetic
""""""""""

I've added ``+``, ``-``, ``*`` and ``/`` variants which get invoked if
the *first* argument in a binary arithmetic operation is a :lname:`C`
type and then throw a condition if the other argument is not the same
:lname:`C` type.

Similarly, there are the usual comparators, ``<``, ``<=``, ``==``,
``>=`` and ``>`` for the ``C`` domain.

These, clearly, differ from the nominal :lname:`Idio` numeric
comparison functions (``lt``, ``le``, ``eq``, ``ge`` and ``gt``) which
exist to avoid clashing with the shell-like ``<`` and ``>`` IO
redirection operators.  I've stuck with the "minimal changes from
:lname:`C`" principle for the :lname:`C` comparators.

Names for things, eh?  Who'd have thought it would be hard?

Conversions
"""""""""""

.. sidebox::

   Semantically, in the ``C`` namespace convert an (:lname:`Idio`)
   integer into a :lname:`C` one.

   It started life just creating :lname:`C` ``int``\ s -- the
   limitation of my interest at the time.

In ``C/integer->``, as we have now been given the precise :lname:`C`
type of the result we can also perform some range tests on the
supplied integer.

``C/->integer`` does what you'd expect except won't work for floating
point :lname:`C` types for which you want ``C/->number`` -- which is
ultimately a superset.

You cannot convert a :lname:`C` ``long double`` type into an
:lname:`Idio` floating point type (ie. a bignum) this way for similar
uncertainty of encoding issues.

The problem is less the conversion, as all of them are implemented
"lazily" by having :manpage:`sprintf(3)` print them out and the reader
read them back in again, but rather capturing the special forms
(``NaN`` etc.) without requiring to include the entirety of the maths
library, :file:`libm`.

How "lazy" you consider that conversion is moot.  Any radix conversion
routine will have to loop performing division by the new radix and
store of the remainder followed by some reworking of the exponent.
The people writing :manpage:`sprintf(3)` have had some considerable
head-start in making their algorithms efficient.  Feel free to `have a
gander <https://www.dictionary.com/browse/take-a-gander-at>`_ at
`print_fp.c
<https://github.com/lattera/glibc/blob/master/stdio-common/printf_fp.c>`_
if you are interested.

Printing
""""""""

There's a small amount of flexibility for printing a :lname:`C` type:

.. csv-table:: C Type Printing
   :header: :lname:`Idio`, format specifiers
   :widths: auto
   :align: left

   ``char``, c
   ``schar``, d
   ``uchar``, X o u* x b
   ``short``, d
   ``ushort``, X o u* x b
   ``int``, d
   ``uint``, X o u* x b
   ``long``, d
   ``ulong``, X o u* x b
   ``longlong``, d
   ``ulonglong``, X o u* x b
   ``float``, e f g*
   ``double``, e f g*
   ``longdouble``, e f g*

\* denotes the default where more than one format is possible

b is a binary output format

:manpage:`printf(3)`\ -style conversion precisions are supported, eg.
``"%.1f"``.  This only really affects floating point numbers for which
the precision affects the number of significant or decimal
places. Otherwise, the string returned by simply printing the value
will have any conversion precision applied in :ref:`format <format>`.

C Pointers
----------

:lname:`C` pointers are a little more interesting.  In the first
instance we need to store a "free me" flag as a few :lname:`C`
pointers we pass around are not ours to :manpage:`free(3)`.

In writing the :ref:`c_api` I needed a mechanism to associate some
arbitrary blob of memory allocated for some ``struct`` with a
primitive that knew how to access the members of the struct.

This :abbr:`C Struct Identification (CSI)` replaces a limited
mechanism to print a :lname:`C` ``struct`` and provides considerably
more functionality.

.. sidebox::

   Actually, we only need a unique totem as everything else can be in
   lookup tables.  However, whilst a ``pair`` is (always) a unique
   totem, we might as well stick something in it and save two of those
   lookup tables!

An :samp:`idio_CSI_{module}_struct_{something}` is a simple list that
has the struct's name, :samp:`"struct {something}"` and the primitive
for accessing the members of that struct, probably,
:samp:`{module}/struct-{something}-ref`.

The struct modifier, probably,
:samp:`{module}/struct-{something}-set!` can be invoked through the
:ref:`setters` mechanisms and we can associate a printer for the
struct through the ``add-as-string`` mechanism.

.. include:: ../../commit.rst

