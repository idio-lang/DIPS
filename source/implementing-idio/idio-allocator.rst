.. include:: ../global.rst

***************************
The :lname:`Idio` Allocator
***************************

Let's have a little digression into (memory) `allocators
<https://en.wikipedia.org/wiki/C_dynamic_memory_allocation>`_ rather
than garbage collectors *per se*.  This becomes a very complicated
field.

We're partly here because I thought that things could be done with an
allocator to improve *stuff*.  Which might be true but, it transpires,
not obviously by me.  However, having been through the process, a)
we're no worse off (always a good thing), b) it *is* interesting
and c) I've left it turned on by default.

Variations
==========

Hiding in the :lname:`Bash` codebase is :file:`lib/malloc/malloc.c`
which is derived from some :lname:`Emacs` improvements to
:ref-author:`Chris Kingsley`'s 1982 fast storage allocator.  In fact,
an Internet search for "malloc.c Chris Kingsley" will show derivations
appearing in many places.  Annoyingly, I can't find a definitive
source for the original so something like the FreeBSD
`libexec/rtld-elf/malloc.c
<http://web.mit.edu/freebsd/head/libexec/rtld-elf/malloc.c>`_ might
have to do.  That version is under 500 lines of code.

Another scheme is :ref-author:`Doug Lea`'s 1987 `dlmalloc
<http://gee.cs.oswego.edu/dl/html/malloc.html>`_ and the code at
`http://gee.cs.oswego.edu/pub/misc/malloc.c
<http://gee.cs.oswego.edu/pub/misc/malloc.c>`_ -- the site itself
seems to use an old link.  :lname:`dlmalloc` is over 6000 lines of
code.

A "pthreads malloc" (ptmalloc) was derived from that and GNU_'s
:lname:`libc` malloc `derived from that
<https://www.gnu.org/software/libc/manual/html_node/The-GNU-Allocator.html>`_
in turn.

.. aside::   Wait!  *What?*

These can start getting a bit complicated with :ref-author:`Jason
Evans`' `http://jemalloc.net <jemalloc>`_ powering FreeBSD and
Facebook.  It is almost 100k lines of code across 400 files.

I think we want something better than naïve, digestible and, sorry,
Jason, not doubling the size of the code base.

There's a comment in a :file:`vxmalloc.c` online from :ref-author:`Hwa
Jin Bae` which says:

    ...contains two different algorithms. One is the BSD based
    Kingsley "bucket" allocator which has some unique fragmentation
    behavior.  The other is Doug Lea's well tested allocator that
    tries to minimize fragmentation while keeping the speed/space
    requirements.

That sounds like a fair compromise (not that I've read the code -- it
seemed too long!).

There's another feature we need to be aware of which appears in that
:lname:`Emacs`/:lname:`Bash` variant in that a POSIX requirement is
that an allocator be re-entrant.  In the absence of threading we *are*
still at risk of reentrancy as we support signal interrupts and we
could trip over ourselves that way -- although we shouldn't as we only
interrupt the :lname:`Idio` code (not the :lname:`C` code).  Besides
it would be nice to be ready for threading should we ever get there.

Design
======

So :file:`malloc.c` is a :lname:`Bash` inspired variation on the
Kingsley fast storage allocator.

The basic mechanism is that you assign allocation requests into chains
of buckets where a bucket (chain) handles allocations sized up to 2\
:sup:`n`.

That said, the actual allocation is extended to include some
accounting overhead and some space for "range markers" which can be
used to verify that users haven't been poking around outside their
allotment.  Not that there's much you can do, at the time you check
(re-allocation or freeing) the damage has been done.  That's the
:lname:`C` way!

In the FreeBSD variant the range marker is a duplicate of the range
magic number in the :samp:`{overhead}` structure.  The :lname:`Bash`
variant uses a slightly cleverer memory guard which encodes the number
of allocated bytes as the terminal marker.  Slightly cleverer as
continuing to locate it at the end of the user's allocation means it
is just as likely to be stomped over as anything else.

Of course, if you know how the :samp:`{overhead}` and memory guards
work and recognising that they are immediately before and after your
allocated memory (broadly, ``a[-2]`` and ``a[n+1]``) you can probably
"adjust" both for fun and profit.

As a partial mitigation, the :lname:`Bash` code supports a malloc
"register" which remembers the allocation separately from the
allocation itself.

So if you request 20 bytes, say, you'll get passed into the 64 byte
bucket chain (your 20 bytes plus another 16-odd of overhead etc. takes
you beyond a 32 byte bucket), 200 bytes into the 256 bucket chain (as
the added overhead bytes don't bump us into the next bucket).

The overhead is a bit vague as it is a fixed size header, a fixed
sized range marker and some padding.

One thing to note is that only one user allocation request goes into
each bucket.  We don't try to squeeze a small thing in on the end of a
quite large but not quite filling a bucket.  We've made an effort to
find the smallest bucket that is at least as big as the request (plus
overheads) and we leave it at that.

However, you can see that any bucket allocation is going to waste
increasingly large amounts of memory as any 2\ :sup:`n` request by you
is going to go into a 2\ :sup:`n+1` bucket.  Although there are some
potential positives if you :manpage:`realloc(3)` and keep within the
2\ :sup:`n` (minus overheads) limits as the code only need tweak the
allocated size field.

The buckets have to live somewhere and so they are tacked onto a
chain.  We need a chain per bucket size and so there's a
:samp:`{nextf}` ("next free"?) pointer per bucket size.  The obvious
implementation, then, is an array of pointers acting as the heads of
the chains.

Buckets
-------

The set of buckets is more interesting than it should be.  How many
should we have?  For example, with a 32-bit counter for our bucket
size, ``ovu_size``, we'd have, uh, 32 buckets, right?

Of course not.  I wouldn't be mentioning it if it was that easy.
There's a couple of things to think about.  In the first instance, our
:samp:`{overhead}` is eight bytes, in this case, so there's no point
in having a bucket size less than that.

In fact you might think that as the :samp:`{overhead}` has to fit into
the bucket as well then there's no point in having an eight byte
bucket either as it wouldn't leave any room for user-data.  However,
we hit our second issue in that the our algorithm for washing about
references :samp:`{bucket} - 1` which means any actually-in-use bucket
chain needs to have a previous bucket to be referenced, if not
actually used.

Hence the buckets start with the 0\ :sup:`th` bucket chain being size
eight bytes -- albeit it is not used, it's just a placeholder.  The
first usable bucket chain, #1, is for sixteen byte allocations which,
given our :samp:`{overhead}` and (two byte) range marker means it's
for small single digit allocations!

That said, I see it gets used about a thousand times during a test run
so it's not to be sniffed at!

At the other end of the scale, given we're starting at 2\ :sup:`3`
(eight bytes in chain #0) and we're limited to 32-bit allocations,
then we can only usefully use 29 more chains with the last, #29 being
allocations of 2\ :sup:`32` which...doesn't work on 32 bit systems.
Your calculation of 2\ :sup:`32` might well be 0 anyway.

Hmm, :lname:`Bash` uses a fixed array of ``binsizes`` with the last
bin size being 2\ :sup:`32` - 1.

I didn't like that fixed array and so dynamically set these values
which requires a small consideration for bucket #29's size.

In fact that last bucket size is set as an ``unsigned long`` value but
*used* as a ``long``, ie. a ``signed long``.  This means the last
bucket's "size" is -1 and is used as a flag to denote failure.

That itself means the largest allocatable size is 2\ :sup:`31` minus
overheads.

Bootstrap
---------

The :lname:`FreeBSD` code requires genuine bootstrap in that the
caller has to initialise the ``pagesizes[]`` array and
``pagepool_start``/``pagepool_end`` pointers.  To what, for the latter
two, isn't especially clear.

The :lname:`Bash` code is a little more dynamic and allocates memory
on demand.

We look at the user's requested allocation and add in the various
overheads.  We then look for the smallest bucket chain capable of
holding this request.

If we've no free buckets in the chain then we grab a minimum of one
page of memory (using a *morecore* function), this :lname:`Idio` code
uses :manpage:`mmap(2)`, and divvy it up into however many 2\ :sup:`n`
buckets.

In *morecore* we only care enough about overhead etc. to stamp in a
"free" flag and "next" pointer into each bucket such that the chain
will now have some free buckets on it.

Obviously, if the requested amount is more than one page then we grab
enough pages to cover the requested allocation (plus overheads)
rounded up to the 2\ :sup:`n` bucket size and a single bucket is added
to the chain.

Accounting
----------

The nominal :samp:`{overhead}` "structure" is actually a union with
the :samp:`{overhead}` structure a member:

.. code-block:: c
   :caption: :file:`malloc.c`

   union idio_malloc_overhead_u {
       uint64_t o_align;	/* 					8 bytes */
       struct {
	   uint8_t ovu_magic;	/* magic number				1 */
	   uint8_t ovu_bucket;	/* bucket #				1 */
	   uint16_t ovu_rmagic;	/* range magic number			2 */
	   uint32_t ovu_size;	/* actual block size			4 */
       } ovu;
   };

which is word-aligned (for large words).  The interesting bit is the
``struct ovu``:

* the ``ovu_magic`` number records whether the block has been
  allocated or freed

* the ``ovu_bucket`` records the bucket (*duh!*) which gives us a
  quick way back to the chain of buckets for when the bucket is freed

* the ``ovu_rmagic`` is one end of the range marker

* the ``ovu_size`` is the requested allocation (by the user)

  Of interest, here, is that

  #. the whole union is 64-bit aligned

  #. but only allows for 32-bit allocations

  This means the :samp:`{overhead}` is 8 bytes or one pointer on a
  64-bit system.  If we allowed for 64-bit allocations then the
  block's size (``ovu_size``) would consume a word on its own and the
  rest of the :samp:`{overhead}` would fill out to two words.
  Matching regular :manpage:`malloc(3)`.

64-bit
^^^^^^

.. aside:: *And don't call me Shirley!*

I went back and looked at this 32-bit allocation limit.  We can do
better, surely?

If we toggle based on the platform's word length (there must be a
better test than ``PTRDIFF_MAX`` -- or other integer) and parameterise
a few things:

.. code-block:: c
   :caption: :file:`malloc.c`

   #if PTRDIFF_MAX == 2147483647L
   #define idio_alloc_t			uint32_t
   #define IDIO_PRIa			PRIu32
   #define IDIO_MALLOC_NBUCKETS		30
   #define IDIO_MALLOC_FIRST_Po2	3
   #else
   #define idio_alloc_t			uint64_t
   #define IDIO_PRIa			PRIu64
   #define IDIO_MALLOC_NBUCKETS		62
   #define IDIO_MALLOC_FIRST_Po2	4
   #endif

where ``IDIO_MALLOC_FIRST_Po2`` ("Power-of-2") is used to set the size
of the first bucket, 2\ :sup:`3` or 2\ :sup:`4`, and is used elsewhere
in the stats gathering if ``IDIO_DEBUG`` is set.

We can then change ``ovu_size`` to the normalised ``idio_alloc_t``:

.. code-block:: c
   :caption: :file:`malloc.c`

   union idio_malloc_overhead_u {
       uint64_t o_align;		/* 					8 bytes */
       struct {
	   uint8_t ovu_magic;		/* magic number				1 */
	   uint8_t ovu_bucket;		/* bucket #				1 */
	   uint16_t ovu_rmagic;		/* range magic number			2 */
	   idio_alloc_t ovu_size;	/* actual block size			4/8 */
       } ovu;
   };

and adjust any relevant size-referencing variable/:manpage:`printf(3)`
statement to use ``idio_alloc_t``/``IDIO_PRIa`` then we appear to
cover our bases.

Testing
"""""""

In the modern age of host machines with a decent amount of RAM and
easily built VMs we should have easy enough access to a 64-bit machine
with more than 4GB of RAM and a 32-bit machine with 4GB of RAM.

.. warning::

   If you're keen to play around then I advise you to do this test on
   machines with those quantities of **RAM**.  They should work with
   those amounts of virtual memory but all you will do is impress
   yourself that Unix based operating systems can (eventually) recover
   from extended periods of *thrashing*.

   The problem is that in creating an :lname:`Idio` array, we *will*
   write a default value (``#f``) into every slot making every
   (virtual memory) page dirty.  If you don't have enough RAM the OS
   will swap those dirty pages out in order that it can do exactly the
   same with a new page.

To test this we'll create an :lname:`Idio` array.  We need to keep
ourselves aware of what's happening under the hood, though, otherwise
we'll have sad faces.

In the first instance, the :lname:`Idio` array is made from a
:lname:`C` array of pointers -- which are going to be four or eight
bytes each, thus bumping up our actual allocation.

On top of that we have the tricksy problem that a 2\ :sup:`n`
allocation will (have to) go into a 2\ :sup:`n+1` bucket and it's the
bucket that we need allocated.

On a 64-bit machine pointer are eight bytes, 2\ :sup:`3`, so if we are
targeting a 16GB allocation, 2\ :sup:`34` bytes, on a machine with
16GB of RAM we want to create an array of 2\ :sup:`31` elements.  The
2\ :sup:`31` :lname:`Idio` elements becomes a 2\ :sup:`34` :lname:`C`
byte allocation which will go into a 2\ :sup:`35` bucket.

Or, rather, it won't because that's more than the virtual memory
available to us.

.. sidebox::

   Remembering, of course, that no current x86 CPU architecture lets
   you address more than 48 bits of physical address space anyway:
   `Virtual Address space
   <https://en.wikipedia.org/wiki/X86-64#Virtual_address_space_details>`_.

Other processes are using memory, including us, so we'll aim a bit
lower.  Any number which generates an allocation over 4GB is good
enough as it demonstrates 64-bit handling and we're in no position to
properly test a full (nearly) 2\ :sup:`64` byte allocation.

We've a couple of options here.

#. We can reduce the number of elements in the array by a bit, keeping
   us below any next-bucket triggering:

   .. code-block:: console

      Idio> make-array ((expt 2 31) - 1000000)
      Killed

   *Eh?*

   Oh, the Linux *Out Of Memory* killer has, er, "helped" us out.

#. We can go down a power of two and look to get bumped up into the
   next bucket...

   .. code-block:: console

      Idio> make-array (expt 2 30)
      #[ #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f ..[1073741804] #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f ]

   Cool.  Probably.  :socrates:`What have we done, exactly?` We've
   created an array of a billion elements (the printer, thankfully,
   omits some in the middle).  A billion elements means eight billion
   bytes and therefore in the sixteen billion byte bucket.

   We should be able to get another 50% in there:

   .. code-block:: console

      Idio> make-array ((expt 2 30) + (expt 2 29))
      #[ #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f ..[1610612716] #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f ]

   which looks very much like we've created (and immediately thrown
   away) a 12GB array.

   It looks plausible.

On a 32-bit machine, targeting the maximum 2\ :sup:`32` byte
allocation with four byte pointers we need to play the same games with
an exception for the very trick we're trying to pull.

.. sidebox::

   In fact, I seem to get an issue with :manpage:`mmap(2)` and
   anything over half of memory.

On a 32-bit machine we *can* feasibly allocate all of memory so we
have to handle the largest cases carefully.

A 2\ :sup:`30` element array will become a 4GB allocation and is too
much.  A 2\ :sup:`29` element array is "only" half of RAM although I
hit the :manpage:`mmap(2)` limit so we should aim for a 2\ :sup:`29` -
10 element array for just under half of RAM:

.. code-block:: console

   Idio> make-array ((expt 2 29) - 10)
   #[ #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f ..[536870882] #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f #f ]

The :lname:`libc` allocator is different still.  On a 32-bit CentOS 6
VM I can ``make-array`` 2\ :sup:`29` + 2\ :sup:`27` but not 2\
:sup:`29` + 2\ :sup:`28`.  Maybe some
:manpage:`sbrk(2)`/:manpage:`mmap(2)` features.


next pointers
^^^^^^^^^^^^^

The :samp:`{overhead}` structure is potentially/partially re-purposed,
here, to be the "next" in the chain pointer.  This creates its own
problems as we need to ensure that a bucket in the free list (stamping
a pointer in the :samp:`{overhead}`) doesn't conflict with a bucket in
use with magic numbers and sizes etc..

In the :lname:`FreeBSD` code, there is a ``next`` pointer in the
overhead union which directly impacts the :samp:`{overhead}`
structure.

To mitigate this it plays a similar trick to Idio itself and
recognises that a pointer will always have the trailing two bits as 0
and so long as the corresponding :samp:`{overhead}` field
(``ovu_rmagic``) does not have trailing 0s there we can differentiate
between the two.  The code assumes we have a big-endian machine and we
can set the range magic number to be an odd number (and thus not
ending in two zeros).

In the :lname:`Bash` code the ``CHAIN`` macro uses a pointer a ``char
*`` inside the block.  That ``sizeof (char *)`` offset means we skip
over the ``ovu_magic``, ``ovu_bucket`` and ``ovu_rmagic`` fields on
all platforms.

Given the block is 64-bit aligned that means on a 64-bit platform
you're setting the ``next`` pointer in the (nominally) user-allocated
section and on a 32-bit platform you're overwriting some part of the
:samp:`{overhead}` structure -- it should be the ``ovu_size`` field.

It's not clear why the (nominally) user-allocated section isn't used
all the time for the ``next`` pointer.  Maybe it's some heinous
combination of the :lname:`C` macros on obscure systems.

The nearest I can think is that for bucket #0 (eight bytes) there is
no user-data section so we'd be in trouble.  But bucket #0 is a
placeholder, we don't actually use it.

I've set the :lname:`Idio` code so it always uses the user-data
portion...and we're still here!

mmap/sbrk
^^^^^^^^^

I've only used :manpage:`mmap(2)` in this implementation but the
:lname:`Bash` code goes a bit further and uses :manpage:`sbrk(2)` for
allocations under a page size.

I don't know if that makes this implementation good or bad in
relation.  Obviously the :lname:`Bash` (née :lname:`Emacs`) code has
both some considerable history and wider (operating system)
distribution and so has to cover more bases.

All I can say is that...it works for me!  I fancy there may be bridges
to be crossed.

I also notice that :manpage:`sbrk(2)` is deprecated in Mac OS X/Big
Sur with the following commentary:

    **The brk and sbrk functions are historical curiosities left over
    from earlier days before the advent of virtual memory
    management.**

Implementation
==============

The implementation of ``malloc``, ``calloc``, ``realloc`` and ``free``
works pretty much as you might expect with having to rummage around
finding buckets etc..

If you have a debug build then :file:`vm-perf.log` will have some
allocator stats for you.

This is where I thought there might be some improvements to be had.
If you look at the stats you can see that one of two of the chains are
far more popular than others.  Perhaps not surprisingly, the smaller
sized ones.

Pulling some numbers out:

.. csv-table::

   bucket:, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096*, 8192, ...
   free:, 0, 868K, 1447K, 41K, 142K, 2487, 1592, 181, 0, 0, ...
   used:, 0, 7679, 233K, 1644K, 49K, 185, 24, 11, 41, 0, ...
   peak:, 0, 876K, 1680K, 1686K, 192K, 2668, 1614, 192, 42, 6, ...
   mmap:, 0, 6846, 26K, 52K, 12K, 334, 404, 96, 99, 22, ...
   munmap:, 0, 0, 0, 0, 0, 0, 0, 0, 58, 22, ...

you can see from the *peak* numbers that a lot of 32, 64 and 128 byte
buckets were allocated.  The actual number of those won't change -- we
can't change the user-code -- but what we might tweak is the number of
``mmap`` calls, tens of thousands.

So I looked at asking for, say, 1000 pages at a time so that the
number of ``mmap``\ s would drop to the tens.

That makes almost no difference at all.  Perhaps as you'd expect as
you're only reducing the number of system calls in the overall process
run from the millions (I would presume) by a few thousand.


.. include:: ../commit.rst

