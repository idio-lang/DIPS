.. include:: ../global.rst

******************
Garbage Collection
******************

This is not an academic treatise nor even a very good summary.  It's
what I can remember to say about what I know about `Garbage
Collection`_.

.. sidebox:: I knew someone who created a multi-user chat system as a
             student project.  Impressed, I asked about their use of
             memory allocation.

	     *What's memory allocation?*

	     Oh.  Dear.

The problem is what to do with values that you create during the
processing of your language.  You will be creating values that other
parts of the system are going to reference.  How do you manage the
memory when they stop being referenced?  You are unlikely (see
sidebox) to be creating them with automatic variables so you'll be
allocating them on the :lname:`C` heap and hoping (against hope?) that
someone will remember to free them up.



You *could* not bother freeing stuff up until the process exits but,
er, good luck with scaling that attitude up.

Introduction
============

I'm going to start by suggesting there are two broad categories of
handling memory management: reference counting and garbage collection.
The chapter title probably gives away a clue about where we're headed
but in fact both are used in :lname:`Idio` for reasons that mostly
boil down to, "it seemed a good idea at the time".

Reference counting is like the way files in a Unix filesystem are
handled.  Each time the underlying inode is referenced in a directory
the reference count increments.  Each time a process opens the file
the reference count increments.

Careful analysis of the above reveals the old tea-time trick of
opening a file, unlinking the file name and then writing rubbish into
the file.  The operating system says the disk is full but there is no
large file to be found.  *Ho ho ho!*

In the meanwhile, as the reference counting mechanism is going about
its business, if any of the reference counts drops to zero then it can
free the value.  Easy and *immediate* (which is another bugbear of
garbage collection).

Reference counting was a thing in programming languages but I get the
impression that there is a move towards garbage collection.

Garbage collection is subtly different.  Rather than have a reference
count associated with the value in memory the garbage collector
firstly maintains a list of all known values that have been allocated.
That's as simple as having a pointer in the allocated value which
becomes the linked list of all known values.

Secondly, and this is where the time honoured complaints about garbage
collection come in, every now and again the garbage collector will
decide it's time to tidy up -- during which time user-level processing
effectively stops.  The garbage collector will look at the set of
"root" values which are broadly:

* the list of values declared at top level

* the values currently associated with the current thread of control
  which will include the lexical values in scope

and trot down that list marking them as "seen".  If any of those
values are compound values (pairs, arrays, hashes, etc.) it will
recurse down those too.

.. sidebox:: *\*cough\** maybe more than twice if the implementation
             is really bad *\*cough\**

Eventually (hint: it has to visit every value at least once, possibly
twice so it's not the quickest process ever), it will have traversed
the entire set of "seen" values.  Anything left over is, uh, garbage
and can be collected (whatever that means but you can broadly assume
"freed").

Historically, this "world-stopping" has been considered A Bad Thing™.
If you're writing some real-time or :abbr:`FinTech (Financial
Technology)` "money-time" application then pausing for tens of
milliseconds whilst the garbage collector rummages about deciding
there's not much to do is going to be a problem.

For the rest of us, though, actually it's OK.  It isn't *great* in the
sense that you get non-deterministic pauses in your processing but
certainly for us, a shell, it's OK.

Where it is not OK, or at least where we have to be leery, is that the
garbage collector runs and will therefore free-up values *some time
after* the values were last actively in use.  Most of the time that
isn't a concern but there are occasions when it is.

Consider allocating a value that is associated with some finite
operating system resource like a file descriptor.  Suppose we create a
bunch of files, do our thing, then stop referencing those values which
now leaves us with all our file descriptors "in use".  We can't open
another file because we can't get a file descriptor because they're
all locked away inside values waiting to be freed.  *Oops!*

You might argue that, especially in the case of file descriptors, you
could explicitly :manpage:`close(2)` the file descriptors.  Which is
true but is a clumsy interference in automatic memory management.  You
were happy to allow someone else to manage the
:manpage:`malloc(3)`/:manpage:`free(3)` and you should be happy to
extend that management to other (considerably less finite) system
resources.

The fix, for what it is worth, is that the code that opens a file
needs to be aware that amongst the system errors coming its way are
``EMFILE`` (a per-process limit on the number of open files) and
``ENFILE`` (a system-wide limit on the number of open files) and in
either case pro-actively invoke the garbage collector.  It should do
this in a loop so that if a first attempt to open a file fails with
``EMFILE``/``ENFILE`` it should call the garbage collector and try
again.  Second time round says you're clean out of luck and an
appropriate error message should be raised.

Let's refer (ho ho) to the :abbr:`GC (Garbage Collector)` from now on.

GC Types
--------

You might further divide GCs into two types.  Firstly a copying GC and
then a mark and sweep GC.

A *copying* GC in effect allows you up to half of available memory.
That's because the way it handles "seen" values is to literally copy
them from half A to half B (maintaining a list of moves so that you
can patch up any later references to previously moved values).  You
can then carry on allocating in the remaining space in side B until it
is time to repeat the process from side B back to side A.

This has one very clear advantage in that after every GC the allocated
memory is compacted.

I've not implemented this though it might have some mileage for an
Emacs-style "undump" functionality.

A *mark and sweep* GC works by tagging values with colours, usually
white, grey and black.  Initially all values are tagged white except
the "roots" which are marked grey.  You can then:

- pick a value from the grey list

- mark this value as black

- each white value this value directly references should be moved to
  the grey list

- repeat until the grey list is empty

With the grey list empty, any remaining white values can be cleaned
up.

Here, you might see:

- an iteration over the whole list of values tagging everything as
  white

  (You can mitigate this by alternating the sense of black and white
  so that you roll white-grey-black on one cycle then black-grey-white
  on the next.)

- iterating over all "live" values

- iterating over the whole list of values to identify the values
  to be freed

Hence several iterations over the set of values.

One advantage of the tri-colour method is that it is possibly to
implement it "on the fly" limiting any stop-the-world effects.

GC Variations
-------------

We can now throw some variations into the mix.

.. _`generational GC`:

Generational GCs
^^^^^^^^^^^^^^^^

Here the broad idea is to maintain some idea of the "era" in which the
value was allocated.  In general, the idea goes, recently allocated
values are more likely to be thrown away and therefore you might
restrict the set of values you iterate over during GC to the most
recent era.

Clearly you need some algorithm to include older and older eras in the
GC.

Pools
^^^^^

There are any number of opportunities here to reduce the *number of
calls* to :manpage:`malloc(3)` and friends and reduce the *overhead*
it introduces.  Each :manpage:`malloc(3)` call has a two-pointer
overhead (for its own machinations) which is a touch inefficient when
you're allocating millions of values.

Suppose instead, we allocated a page of memory at a time -- or, wait
for it, several pages of memory at a time.  Many of our values are a
fixed size and we can therefore slot several hundred of that size into
a page and be able to access them like an array.  Similarly for
different sized values with just a different number per page.  Weirdly
sized things -- think strings -- might be handled more
traditionally.

Clearly we'll need to maintain some used/free list within the page but
if we're feeling keen we can then rework our value structure and
re-factor out common parts, like the GC colours, into page-wide
tables, much like the Arenas being discussed in the `LuaJIT GC`_.

Multiple GCs?
^^^^^^^^^^^^^

You probably don't want to as you'll step into a complicated and
time-rich world.  You will quickly result in cross-GC references and
not simply in a newer to older sense.  Take closures, for example.  We
could create a closure in one GC and have it returned to another GC.
That closure, however, has references back to the first GC.  That
partly means that the first GC cannot be removed but also complicates
the algorithm for marking in-use values which now have to be
multi-GC-aware.


.. include:: ../commit.rst

