.. include:: ../../global.rst

******
Arrays
******

.. sidebox:: I had to look this up.

Traditionally, :lname:`Scheme`\ s support the notion of a fixed length
*vector* of values and *arrays* of multiple dimensions (quite possibly
implemented using vectors).

In :lname:`Idio` I wanted "arrays" (whatever they are) but in
particular I wanted them to be dynamic in size (presuming a single
dimension) so I could use them for *stacks* for the VM.  As a stack
they will have to take on any old value and, as I had no pressing
need, they are one dimensional.

I read about :lname:`Lua`'s *sparse arrays* which seemed like a neat
trick though I couldn't see any particular immediate use for them.
They are implemented, of course, as part regular array, being `yea
<https://en.wiktionary.org/wiki/yea>`_ big *[\*waves hands\*]*, and
part hash table.

What *is* interesting about that idea, going back to our shell arrays,
or, rather, :lname:`Bash` arrays, which are slightly magical
themselves or, numerically idiosyncratic, depending on your view.  In
the first instance we can remove entries and the missing entries
sort-of disappear:

.. code-block:: bash

   % a=( 1 2 3 )
   % unset a[1]
   % echo ${a[*]}
   1 3
   % echo ${#a[*]}
   2
   % echo ${a[1]}
   % echo ${a[2]}
   3


Operations on the array as a whole -- notably reporting the number of
elements in the array -- indicate the reduced number yet the deleted
element is "still there."

That counting result is slightly perverse.  I could understand that an
enumeration of an array with deleted elements might result in a
shortened list:

.. code-block:: bash

   r=( "${a[@]}" )

Giving me a true, two element list in ``r``.  But that the *count* of
the elements in ``a`` is short.  That's weird.  We *know* the last
indexable element is 2 (starting from 0) but the array length is 2.

I wonder if that's why the :samp:`$\\{!{name}[*]}` form of parameter
expansion -- to return the keys of the array -- was created?

Another, related, trick is that I can add another *non-contiguous*
element and the same whole-array view is maintained.  The missing
elements are ignored for whole-array operations:

.. code-block:: bash

   % a[4]=4
   % echo ${#a[*]}
   3
   % echo ${a[3]}

This got me thinking.  I use arrays quite a lot in the shell -- it
*is* the only data structure, after all -- and I have twirled and
twisted using the same "missing math" tricks which *I* know work,
because I've being doing it for years, but does anyone else know?  Is
it behaviour that a regular programming person is going to
:term:`grok`?

I don't think so.

That second variation has another, more pernicious possibility.

.. code-block:: bash

   % a[1234567890]=1
   % $echo ${!a[*]}
   0 2 4 1234567890


:lname:`Bash` is happy, obviously, with that but it nominally requires
that *we* create a 10\ :sup:`10` element array because our arrays are,
naïvely, actual contiguous blocks.

Does that lead us back towards the :lname:`Lua` (and, evidently,
:lname:`Bash`) sense of sparse arrays?  I don't want to go there.  It
looks like it's solving a problem I'm not sure exists in regular
programming fare.  One that a user can solve themselves in
:lname:`Idio`-land with a structure of *stuff*.

However, I think we can allow the growth of arrays by pushing an
element on the end (like a stack) and I've allowed for the
:lname:`Perl`-ish ``unshift`` to push an element on the front of an
array.  But I don't like the arbitrary index mechanism.

I suppose, in that sense, :lname:`Idio` arrays function much like a
mildly extended :lname:`Scheme` vector, a *vector+*.

Implementation
==============

How *big* an array?

C99 suggests that sizes should be ``size_t`` so we could create an
array with ``SIZE_MAX`` elements.  Even on non-segmented
architectures, such a memory allocation will almost certainly fail
but, sticking to principles, someone might want to create a
just-over-half-of-memory, :samp:`2**({n}-1) + 1`, element array.  (If
only to annoy the developers.)

The reason it will fail is that every Idio array element is a pointer,
ie 4 or 8 bytes, therefore we can't physically allocate nor address
either 2**32 * 4 bytes or 2**64 * 8 bytes just for the array as those
are 4 and 8 times larger than addressable memory.  So, in practice,
we're limited to arrays of length 2**30 or 2**61 -- with no room for
any other data (including the code doing the allocating)!

As a real-world example, on an OpenSolaris 4GB/32bit machine:

.. code-block:: idio
		
   make-array ((expt 2 29) - 1)

was successful.  :samp:`2**30 - 1` was not.

However, we accomodate negative array indices, eg. the nominal,
:samp:`array[-{i}]`, which we take to mean the *i*\ :sup:`th` last
index.  The means using a *signed type* even if we won't ever actually
use :samp:`a[-{i}]` -- as we'll convert it into :samp:`a[{size} -
{i}]`.

So, the type we use must be ``ptrdiff_t`` and therefore the largest
positive index is ``PTRDIFF_MAX``.

.. code-block:: c
   :caption: gc.h

   typedef ptrdiff_t idio_ai_t;

   #define IDIO_ARRAY_FLAG_NONE		0

   struct idio_array_s {
       struct idio_s *grey;
       idio_ai_t asize;
       idio_ai_t usize;
       struct idio_s *dv;
       struct idio_s* *ae;
   };

   typedef struct idio_array_s idio_array_t;

   #define IDIO_ARRAY_GREY(A)	((A)->u.array->grey)
   #define IDIO_ARRAY_ASIZE(A)	((A)->u.array->asize)
   #define IDIO_ARRAY_USIZE(A)	((A)->u.array->usize)
   #define IDIO_ARRAY_DV(A)	((A)->u.array->dv)
   #define IDIO_ARRAY_AE(A,i)	((A)->u.array->ae[i])
   #define IDIO_ARRAY_FLAGS(A)	((A)->tflags)

where we have:

* ``asize`` being the allocated size

* ``usize`` being the used size, or user-visible size

* ``dv`` is the default value

* ``ae`` are the array elements

The default value is used to reset an element when the index is
"deleted."  Clearly, it isn't really deleted so this is the effective
action.

Depending on how an array is created it will have an allocated size
but the initial used size can vary.  If the array is created from
:lname:`C` then it will most likely have an initial used size of zero.
The only way to *add* elements is to push (or unshift) them onto the
array.

If the array is create from :lname:`Idio` primitives then the used
size will match the allocation size (which may be the number of
arguments passed).

Reading
-------

A useful reader format for static arrays uses the tradition square
brackets syntax common to many programming languages.

``#[ ... ]``

Writing
-------

Arrays will use the ``#[ ... ]`` reader format.

Operations
----------

:samp:`array? {value}`

      is :samp:`{value}` an array?

:samp:`array {list}`

      create an array from the element in :samp:`{list}`

:samp:`make-array {size} [{default}]`

      create a :samp:`{size}` element array initialised with
      :samp:`{default}` if supplied or ``#f`` otherwise

:samp:`copy-array {arr} [{depth} [{extra}]]`

      copy array :samp:`{arr}`

      :samp:`{depth}` can be the symbol ``'deep`` or ``'shallow``
      where ``'deep`` will recursively copy the elements of
      :samp:`{arr}` whereas ``'shallow`` will just reference the same
      values as in :samp:`{arr}`

      :samp:`{extra}` is the number of additional elements to add to
      the allocated size when copying :samp:`{arr}` which can be used
      to prevent the auto-doubling in allocated size if you can
      predict the number of :samp:`{extra}` elements you might be
      about to use.

:samp:`array-fill! {arr} {fill}`

      set all the elements of :samp:`{arr}` to :samp:`{fill}`

:samp:`array-length {arr}`

      notionally: return the number of elements of array :samp:`{arr}`

      In practice it is the highest used index plus one.

:samp:`array-ref {arr} {index}`

      return the value at index :samp:`{index}` of array :samp:`{arr}`

      :samp:`{index}` can be negative in which case the determined
      value is :samp:`{used size} + {index}`.  Hence ``-1`` is the
      last element, ``-2`` is the penultimate element, etc..

:samp:`array-set! {arr} {index} {value}`

      set the value at index :samp:`{index}` of array :samp:`{arr}` to
      :samp:`{value}`

:samp:`array-push! {arr} {value}`

      append :samp:`{value}` to array :samp:`{arr}`

      This will increase the used size of :samp:`{arr}` by one.
      
:samp:`array-pop! {arr}`

      return the last accessible value in array :samp:`{arr}`

      It will return ``#n`` if the array has no elements.
      
      Otherwise this will decrease the used size of :samp:`{arr}` by
      one.
      
:samp:`array-unshift! {arr} {value}`

      prepend :samp:`{value}` to array :samp:`{arr}`

      This will increase the used size of :samp:`{arr}` by one.
      
:samp:`array-shift! {arr}`

      return the first value in array :samp:`{arr}`

      It will return ``#n`` if the array has no elements.
      
      Otherwise this will decrease the used size of :samp:`{arr}` by
      one.
      
:samp:`array->list {arr}`

      return the elements of array :samp:`{arr}` as a list

Conditions
----------

``^rt-array-bounds-error``
