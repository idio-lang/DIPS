.. include:: ../global.rst

********************
The :lname:`Idio` GC
********************

Once you have a GC, everything looks like it can be allocated!  Which
is broadly true albeit for a slightly different reason.

One thing I try to bear in mind is that the underlying :lname:`C`
implementation is something of a bootstrap.  Ideally, we should be
able to implement the entire :lname:`Idio` engine in, er,
:lname:`Idio` which requires that the values being manipulated by the
:lname:`C` engine are able to be manipulated by the putative
:lname:`Idio` engine as and when the replacement engine takes over.

Hmm, that rather circular description was meant to say that we should
not be implementing, say, linked lists internally in a funny way in
:lname:`C` but rather use the same data structures as :lname:`Idio`
uses, ie. pairs.

This then extends to all values that a putative :lname:`Idio` engine
might need to use, lexical frames, threads, continuations etc., such
that they are manageable by :lname:`Idio` itself.

That requires a little expansion.  Like with pairs, it doesn't mean
that :lname:`Idio` needs to understand or even be able to directly
access the nitty gritty of what are, obviously, :lname:`C` values on
the heap but rather that it has the ability to create and manipulate
them enough that it can do whatever is necessary for its job.  In the
case of pairs, it has ``ph`` and ``pt`` (and ``set-ph!`` and
``set-pt!``) -- but it doesn't know what the implementation of those
look like in :lname:`C`.

(Nor do we, yet!)

Not *everything* is allocated through the garbage collector.  We will
be implementing a byte compiler and virtual machine for which a long
stream of bytes are required acting as The Program.  Generating those
bytes does sometimes involve a little complexity for which I decided
to use some simple reference counting system as I couldn't see an
:lname:`Idio` implementation of an :lname:`Idio` engine requiring
access and the simpler the data structure the quicker the access for
the virtual machine.

The basic rules are:

#. special case the VM's program

#. one-off entities, eg. the GC itself are handled manually

#. everything else is garbage collected

.. rst-class:: paragraph-header

Values & Objects

When discussing :lname:`Idio` entities I'm going to try to use *value*
everywhere to mean a construction in :lname:`C` memory.  I want to try
to avoid using the word *object* because of its overloaded association
with :abbr:`OOP (Object Oriented Programming)` -- which we won't be
doing either.

I expect I will fail.  There are no objects, only values.

Caveats
=======

Before diving in we should be aware of some interesting/annoying
behaviours with our :lname:`C` hats on.

We will be creating :lname:`Idio` values in :lname:`C` -- obviously,
because that's the only place that *can* create :lname:`Idio` values.
However, the GC operates using a list of roots which are established
somewhere but not obviously in our little lexical :lname:`C` snippet.

A lot of the time that isn't going to be an issue as our :lname:`C`
snippet is "in and out" and there's no chance of the GC running.
However, there are several occasions when we will call some
functionality that will in turn invoke some :lname:`Idio` code and
once the :lname:`Idio` VM starts running it is free to call the GC at
any time it chooses.

If the GC is run, it will walk down the list of roots (and recurse
etc.) but at no time will it find our :lname:`C` lexical variable.  So
the value will be freed-up underneath the feet of the :lname:`C`
function.  When the code eventually unwinds back to the :lname:`C`
function, it will be none-the-wiser that the lexical variable is now
invalid and some entertaining debugging can begin.

That's partly the reason for ``IDIO_ASSERT()`` being plastered
everywhere!

We have a couple of choices to protect ourselves during this period:

* we can add anything we want to keep to the list of roots

  In one sense this is pretty obvious but breaks down when you have "a
  lot" of lexical variables and/or a nested tree of functions with
  lexical variables.

  This isn't ideal, though, as if the code raises an error and
  :manpage:`siglongjmp(3)`\ s then our :lname:`C` function won't be
  resumed to take the value off the list of roots.

  Hence, the second option:

* we can "pause" the GC until we return here

There's a slight qualifier to pausing the GC.  If the invoked code
raises an error and the :lname:`C` code :manpage:`siglongjmp(3)`\ s
then we'll never return to the :lname:`C` function which is patiently
waiting to "unpause" the GC.  So long as the :manpage:`sigsetjmp(3)`
code is expecting that (and can "reset" the paused-ness of the GC to
some previously safe state) then we're good to go.

The GC
======

The GC object itself is a data structure which keeps track of:

* ``used`` - the list of values

* ``roots`` - the list of root values

* ``grey`` - the grey list used during a collection -- should be
  ``NULL`` at other times

* ``pause``

  This gives us the ability to block "critical sections" from having
  the collector run during them.

  It is an integer allowing nested parties to "pause" and "unpause"
  the GC reasonably sensibly.  *Most* of the time we emerge back into
  a "not being paused" state....

  The danger of over-pausing is that there will be a build up of
  values waiting to be collected resulting in a longer collection.

* flags

  Only two at the moment:

  #. ``IDIO_GC_FLAG_REQUEST`` -- a collection has been requested but
     is subject to ``pause``

  #. ``IDIO_GC_FLAG_FINISH`` -- we've started shutting down so don't
     engage in superfluous debugging *\*grr!\**

* stats

As a partial defence against appalling efficiency I added:

* ``free`` - a list of previously ``used`` values which have not yet
  been :manpage:`free(3)`\ d and are available for re-use.

The operation of the GC is the tri-colour algorithm described
previously.

Back in the real world, there is plenty of work being done with
garbage collectors and many projects use the `Boehm GC`_.  OpenJDK_ is
now using the `Shenandoah GC`_.

GC Code-base
------------

:file:`src/gc.h` defines all the value types and their accessors and
flags and ....  It also defines the ``IDIO`` type itself which is a
pointer to an ``idio_t``/``struct idio_s``:

.. code-block:: c

   typedef unsigned char idio_type_e;
   typedef unsigned char IDIO_FLAGS_T;


   struct idio_s {
       idio_type_e type;	/* up to 255 types */
       IDIO_FLAGS_T gc_flags;	/* GC colours etc. */
       IDIO_FLAGS_T flags;	/* 8 generic type flags: const, etc. */
       IDIO_FLAGS_T tflags;	/* 8 type-specific flags */

       union idio_s_u {
	   idio_foo_t	foo;
	   idio_bar_t	bar;
           ...
       } u;
   };

   typedef struct idio_s idio_t;
   typedef idio_t* IDIO;


``IDIO``
^^^^^^^^

That last line is key: an ``IDIO``, a pointer to an
``idio_t``/``struct idio_s`` is our stock :lname:`Idio` type.

Everything passed around in :lname:`C` is an ``IDIO`` which, as it is
a pointer, gives rise to the notion that we are always referring to a
value.  We never pass a value *per se*.

(Numbers and Constants will break that notion but let's roll with it.)

gc.c
^^^^

:file:`src/gc.c` concerns itself with allocating memory, accounting,
garbage collection.  It *does not* perform value initialisation.

Individual value constructors will ask for a base value from the GC
(which might be allocated from the heap or returned from the free
list) and initialise them themselves.  They will allocate any more
memory required (through the GC for accounting purposes) -- think of
the extra memory required for a string.

When a value can be freed, the GC will call a value-specific free-ing
function -- which can free, say, the extra memory required for the
string, updating the stats -- before the GC will chose whether to add
the value to the free list or actually :manpage:`free(3)` it.

Finalisers
^^^^^^^^^^

For a class of values you might want to run some code to tidy up,
usually, finite system resources.

The classic example is Unix file descriptors.  With a GC, we might
create a value with the opened file descriptor somewhere inside it but
the nature of a garbage-collected language means we don't
:manpage:`close(2)` the file descriptor explicitly in user-code -- as
we don't know who is still referencing the value until a GC sweep
reveals it has been orphaned.

When we do come to collect the value which, to the GC, means to
:manpage:`free(3)` it, we need to interject because we need to perform
some final actions which affect something *other* than the GC.  For
the file descriptor, that is to call :manpage:`close(2)`.

We *could* put the :manpage:`close(2)` call in the nominal
``idio_free_file_handle()`` code but it is more generic to associate
the value with a *finaliser* function and have the GC invoke the
finaliser with the value.

If we were feeling particularly keen that could be an
:lname:`Idio`-level user-defined function -- but we're not, so this is
a :lname:`C`-level functionality.

Value Code-base and Life-cycle
------------------------------

That description gives the following broad code structure and value
life-cycle for some putative "foo" type.

Take note of the consistency of the naming, generally:

#. ``idio_`` (or ``IDIO_`` -- you'll get the picture)

#. *functional area* which might be

   * ``TYPE_`` for the GC or

   * ``foo_`` for matters related to our "foo" value

#. *differentiator* which might be

   * ``FOO`` as the distinguishing type name for the GC

   * ``free()`` for the GC-related function

gc.h
^^^^

There are three sections of interest:

#. defining a unique type number
   
   .. code-block:: c

      #define IDIO_TYPE_FOO	99

   ``IDIO_TYPE_FOO`` will be used throughout the code-base.  There
   will be large ``switch`` statements handling each possible
   :lname:`Idio` type.  The usual culprits are:

   * :file:`src/gc.c` to handle GC

   * :file:`src/util.c` to handle both equality and printing

#. defining the :lname:`C` struct and accessors for the value, say:

   .. code-block:: c

      typedef struct idio_foo_s {
          int i;
      } idio_foo_t;

      #define IDIO_FOO_I(S)	((S)->u.foo.i)

   There is room for 8 bits of type-specific flags.  For example,
   *handles* have read and write flags:

   .. code-block:: c

      #define IDIO_FOO_FLAG_NONE		0
      #define IDIO_FOO_FLAG_THIS		(1<<0)
      #define IDIO_FOO_FLAG_THAT		(1<<1)

      typedef struct idio_foo_s {
          int i;
      } idio_foo_t;

      #define IDIO_FOO_I(F)	((F)->u.foo.i)
      #define IDIO_FOO_FLAGS(F)	((F)->tflags)

#. adding the value to the ``IDIO`` ``struct``'s ``union``

   .. code-block:: c

      struct idio_s {
          ...
	  union idio_s_u {
              ...
              idio_foo_t          foo;
              ...
	  } u;
      };

If your value can refer to or "contain" other Idio values then you
must have a ``grey`` pointer for the garbage collector to use -- and
we see the requirement to use the "not defined yet" ``struct idio_s
*``, aka. ``IDIO``:

.. code-block:: c

   #define IDIO_TYPE_BAR	100

   typedef struct idio_bar_s {
       struct idio_s *grey;
       struct idio_s *ref;
       int j;
   } idio_bar_t;

   #define IDIO_BAR_GREY(B)	((B)->u.bar.grey)
   #define IDIO_BAR_REF(B)	((B)->u.bar.ref)
   #define IDIO_BAR_J(B)	((B)->u.bar.j)

If your value structure is "large" (probably more than three
pointers-worth but see the commentary in ``struct idio_s`` for
specifics) then your entry in the ``struct idio_s`` ``union`` should
be a pointer and your accessor macros must reflect that:

.. code-block:: c

   #define IDIO_TYPE_BAZ	101

   typedef struct idio_baz_s {
       struct idio_s *grey;
       struct idio_s *ref;
       ...
       int k;
   } idio_baz_t;

   #define IDIO_BAZ_GREY(B)	((B)->u.baz->grey)
   #define IDIO_BAZ_REF(B)	((B)->u.baz->ref)
   #define IDIO_BAZ_K(B)	((B)->u.baz->k)


   
   struct idio_s {
       ...
       union idio_s_u {
           ...
           idio_baz_t          *baz;	/* now a pointer */
           ...
       } u;
   };

foo.c
^^^^^

Most ``foo`` related functionality exists in :file:`foo.c` and
:file:`foo.h`.

Everything should be fairly formulaic.

A value constructor is ``idio_foo`` and returns an ``IDIO``.

It will be passed any relevant arguments although what form those take
and whether they relate to the fields of the ``struct`` are
value-dependent.  For example, a string value is quite likely to be
created from a :lname:`C` string or possibly from an existing
:lname:`Idio` string -- that means there isn't an ``idio_string()``
function but rather two variants.

In this example, we're being passed an ``IDIO`` initialiser for ``i``
although we don't see how that value is converted into the :lname:`C`
``int`` of the ``struct``:

.. code-block:: c

   IDIO idio_foo (IDIO i)
   {
       IDIO_ASSERT (i);

       IDIO f = idio_gc_get (IDIO_TYPE_FOO);

       IDIO_FOO_I (f) = ...;

       return f;
   }

A predicate, ``idio_isa_foo``, (and rather than ``idio_foop`` because
of type and inheritance complications):

.. code-block:: c

   int idio_isa_foo (IDIO o)
   {
       IDIO_ASSERT (o);

       return idio_isa (o, IDIO_TYPE_FOO);
   }

The :lname:`Idio`-level predicate, ``foo?``, will call this and return
a boolean.

The :lname:`C` macro, :samp:`IDIO_TYPE_ASSERT({type}, {value})` is
simply a call to :samp:`idio_isa_{type} ({value})`.

(I notice that ``o`` is representative of "object".  *\*sigh\**)

A value destructor is ``idio_free_foo``:

.. code-block:: c

   void idio_free_foo (IDIO f)
   {
       IDIO_ASSERT (f);
       IDIO_TYPE_ASSERT (foo, f);

       /* nothing to do for a foo */
   }

You'll then have a bunch of accessors and other "foo"-related
functions.

Finally some generic housekeeping:

.. code-block:: c

   void idio_init_foo ();
   void idio_foo_add_primitives ();
   void idio_final_foo ();

where:

* ``idio_init_foo()`` is called early on to allow you to perform any
  basic initialisation.  You might need to be careful of the ordering
  in ``idio_init()`` in :file:`src/idio.c`.

* ``idio_foo_add_primitives()`` is a mechanism to add your primitive
  functions to :lname:`Idio`.  This is called after all the
  ``idio_init_X`` functions have been called.

* ``idio_final_foo()`` is called late on to let you clean up any
  objects you created in ``idio_init_foo()``

  We like to keep a tidy ship!


bar.c
^^^^^

The ``bar`` type was a little more interesting in that we have to
remember to set ``IDIO_BAR_GREY`` to ``NULL``.  The grey pointer has
to be set to ``NULL`` by someone, we could have had yet another switch
statement in the GC but I've settled for here in the value
initialisation code:

.. code-block:: c

   IDIO idio_bar (IDIO ref, IDIO j)
   {
       IDIO_ASSERT (ref);
       IDIO_ASSERT (j);

       IDIO b = idio_gc_get (IDIO_TYPE_BAR);

       IDIO_BAR_GREY (b) = NULL;
       IDIO_BAR_REF (b) = ref;
       IDIO_BAR_J (b) = ...;

       return b;
   }

baz.c
^^^^^

The ``baz`` type was more interesting still in that we have to
allocate some more memory for the ``baz`` field in the ``idio_t``
``union``:

.. code-block:: c

   IDIO idio_baz (IDIO ref, ..., IDIO k)
   {
       IDIO_ASSERT (ref);
       IDIO_ASSERT (k);

       /* this is just the idio_t part */
       IDIO b = idio_gc_get (IDIO_TYPE_BAZ);

       /* now allocate the space for baz_t */
       IDIO_GC_ALLOC (b->u.baz, sizeof (idio_baz_t));

       /* now these macros make sense */
       IDIO_BAZ_GREY (b) = NULL;
       IDIO_BAZ_REF (b) = ref;
       IDIO_BAZ_K (b) = ...;

       return b;
   }

Remember to de-allocate the memory in ``idio_free_baz``:

.. code-block:: c

   void idio_free_baz (IDIO f)
   {
       IDIO_ASSERT (f);
       IDIO_TYPE_ASSERT (baz, f);

       /* book-keeping! */
       idio_gc_stats_free (sizeof (idio_baz_t));

       free (b->u.baz);
   }

gc.c
^^^^

We saw a couple of calls into the allocator part of the GC:

.. code-block:: c

   IDIO idio_gc_get (idio_type_e type)
   {
       IDIO_C_ASSERT (type);

       IDIO o = /* check free list or allocate */;

       /* reset flags etc. */

       /* push onto used list */

       return o;
   }

and ``IDIO_GC_ALLOC`` is a simple macro:

.. code-block:: c

   #define IDIO_GC_ALLOC(p,s)	(idio_gc_alloc ((void **)&(p), s))

and ``idio_gc_alloc`` handles stats for ``idio_alloc`` which calls
:manpage:`malloc(3)` and handles errors (and does some
:manpage:`memset(3)` in debug mode).

Scale
=====

The GC does some work.  At the time of writing just to start up and
shut down I see that it grinds through, amongst other things, 1.5
*million* ``pair``\ s.  Only 131 thousand of those were still "in use"
as the GC shut down.  I say, only, but what are *they* being used for?

.. include:: ../commit.rst

