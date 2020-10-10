.. include:: ../../global.rst

***********
Hash Tables
***********

Traditionally :lname:`Scheme` had no support for hash tables other
than implementation-specific methods.  There are several SRFI_\ s to
bridge that problem, notably SRFI-69_, Basic Hash Tables.

Even SRFI-69 acknowledges that :lname:`Scheme` implementations almost
certainly have some internal hash table functionality if only to
support the notions of an environment (mapping variable names to
values).  Whilst SRFI-69 is not reliant on that -- it uses vectors --
you're left with a sense of "to implement hash tables first implement
hash tables."

In the meanwhile I read around the subject of `hash tables
<https://en.wikipedia.org/wiki/Hash_table>`_ whereon I realised that I
should have paid a bit more attention in school as open and closed
addressing and coalesced hashing and any number of other concepts
appeared before me.

Of course, dizzy with excitement about the prospects, I made a
terrible mistake: *I chose the wrong design*.  I picked on `coalesced
hashing <https://en.wikipedia.org/wiki/Coalesced_hashing>`_ as it
seemed quite neat, which it is.  What I didn't do is read or
internalise the simple sentence under Performance: deletion may be
hard.

I have had no end of trouble with my implementation.  I need to scrap
it and start again with something "better."

In the meanwhile we have a working (-ish) implementation of coalesced
hashing.

Coalesced Hashing
=================

Broadly, instead of having all the values be in a linked list hanging
off the bucket that is your hashed value, the "linked list" is
embedded into the hash buckets in the form of a chain.

Assuming no other entries: the first value to be hashed to bucket H
goes in that bucket.  The second value to be hashed to bucket H can't
go in that bucket (it is occupied) so it goes into the next unused
bucket, say, J, and a "chain link" is put between the first value and
the second, H links to J.  On lookup, once the hash bucket, H, for
either is determined the code needs to walk along the chain links, H
then J, to find which one is "equal to" the value.

Suppose a third value hashes directly to J.  The second value requires
shifting to another free bucket, K, say and the chain link from H now
needs updating to K and then the third value can be placed in J.

Similarly for deletion.  If we delete the first value then we need to
bring the second value in that chain forward from K to H.  If it has
been pointing to another value in the chain, L, say, in turn then that
doesn't need to change as H links to L is fine.

A further refinement is the addition of a cellar (although I decided
to call it an attic) which is a splodge of free buckets, outside of
the normal hashing space dedicated to cross-fire.  If hash values
clash then use the cellar first.

All of it doesn't sound too horrible but it's pretty mucky.  And I've
had a lot of bugs.  It's been a... *learning* experience.

Features
========

Dynamic
-------

Hash tables are, of course, dynamic and will grow (and possibly
shrink) over time.

Sentinel Values
---------------

We need some sentinel values:

* ``#n`` is the not-a-key sentinel value

  In other words you can't use ``#n`` as a key in a hash.

* For a hash table of a given *allocation* :samp:`{size}` then the
  end-of-chain marker is :samp:`{size} + 1`

Hashing and Equivalence
-----------------------

We should (and, indeed, *require*) user-defined hashing and
equivalence functions.

By default the hashing and equivalence functions are written in
:lname:`C`, as you might expect.  Internally, via some :lname:`C`
macros, various hash tables are created with one of:

.. parsed-literal::

   IDIO_HASH_EQP (*size*)
   IDIO_HASH_EQVP (*size*)
   IDIO_HASH_EQUALP (*size*)

which (should!) give the impression of setting the equivalence
function to (the :lname:`C` implementation of) ``eq?``, ``eqv?`` or
``equal?`` and all of them using the default :lname:`C` hashing
function.

You can access those :lname:`C` functions from :lname:`Idio` by
passing the equivalent *symbol* as the equality function when you
create a hash table with :samp:`make-hash [{equiv-func} [{hash-func}
[{size}]]]`.  So :samp:`make-hash 'eq? #n 10` is the :lname:`Idio`
version of :samp:`IDIO_HASH_EQP (10)` in :lname:`C` -- the ``#n`` for
the hashing function means use the :lname:`C` default.

As a slight distraction, :samp:`make-hash eq? #n 10` (ie. the function
value for ``eq?`` is substituted as opposed to the symbol ``'eq?``)
will ultimately perform the same thing except will require the
relatively costly invocation of the :lname:`Idio` primitive ``eq?``
from :lname:`C`

However, for both the hashing and equivalence functions you can pass
your own noting that:

* the hashing function takes a single argument and should return a
  number

* the equivalence function should take two arguments and return ``#f``
  or some other value

String Keys
-----------

Or, rather, :lname:`C` string keys.  This is handy for symbols which
are created from :lname:`C` strings but otherwise are not
:lname:`Idio` values.  We need a special flag to say "don't treat this
as an :lname:`Idio` value."

Weak Keys
---------

This is an important concept to avoid circular loops.  It is also
buggy, I'm sure.

The problem is for the garbage collector.  Under normal circumstances,
the GC iterates over the known root values and ticks off everything it
sees.  Anything left over is no longer referenced by anything in the
program and can be "collected."

However, many subsystems like to keep track of objects they have seen.
For example, there is a properties hash table associating properties
with values -- the signature string associated with a function value,
for example.

To prevent the properties table itself being deleted we need to add it
to the list of known roots and with the key into the properties table
being the function value that means that the function value can never
be collected -- something is always referring to it.

Hence the concept of *weak keys* which are an instruction to the GC to
**not** flag the *key* as having been "seen" from the root.  You can
flag the *value* associated with the key as being seen (otherwise we'd
garbage collect the properties themselves!).

Subsequently, if the function value is still ultimately referred to
from a root value then all is well and if the function value is no
longer referred to from a root value then we don't keep it around
artificially.

This leaves a problem, however, in that the (now garbage collected)
key is still in the properties hash.  We need a special hook in the GC
to remove it from the properties hash at the time of collection (and,
in a later cycle, collect the values previously associated with the
key).

Implementation
--------------

How big a hash table?

We won't be having negative indexes into a hash table so the type is
going to be a ``size_t``.  We'll call it an "idio hash index type" or
``idio_hi_t``.

.. code-block:: c
   :caption: gc.h

   typedef size_t idio_hi_t;

   typedef struct idio_hash_entry_s {
       struct idio_s *k;
       struct idio_s *v;
       idio_hi_t n;		/* next in chain */
   } idio_hash_entry_t;

   #define IDIO_HASH_FLAG_NONE		0
   #define IDIO_HASH_FLAG_STRING_KEYS	(1<<0)
   #define IDIO_HASH_FLAG_WEAK_KEYS	(1<<1)

   typedef struct idio_hash_s {
       struct idio_s *grey;
       idio_hi_t size;
       idio_hi_t mask;			/* bitmask for easy modulo arithmetic */
       idio_hi_t count;			/* (key) count */
       idio_hi_t start;			/* start free search */
       int (*comp_C) (void *k1, void *k2);	/* C equivalence function */
       idio_hi_t (*hash_C) (struct idio_s *h, void *k); /* C hashing function */
       struct idio_s *comp;		/* user-supplied comparator */
       struct idio_s *hash;		/* user-supplied hashing function */
       idio_hash_entry_t *he;		/* a C array */
   } idio_hash_t;

   #define IDIO_HASH_GREY(H)		((H)->u.hash->grey)
   #define IDIO_HASH_SIZE(H)		((H)->u.hash->size)
   #define IDIO_HASH_MASK(H)		((H)->u.hash->mask)
   #define IDIO_HASH_COUNT(H)		((H)->u.hash->count)
   #define IDIO_HASH_START(H)		((H)->u.hash->start)
   #define IDIO_HASH_COMP_C(H)		((H)->u.hash->comp_C)
   #define IDIO_HASH_HASH_C(H)		((H)->u.hash->hash_C)
   #define IDIO_HASH_COMP(H)		((H)->u.hash->comp)
   #define IDIO_HASH_HASH(H)		((H)->u.hash->hash)
   #define IDIO_HASH_HE_KEY(H,i)	((H)->u.hash->he[i].k)
   #define IDIO_HASH_HE_VALUE(H,i)	((H)->u.hash->he[i].v)
   #define IDIO_HASH_HE_NEXT(H,i)	((H)->u.hash->he[i].n)
   #define IDIO_HASH_FLAGS(H)		((H)->tflags)

Here we have:

* ``size`` is the nominal hash size, 2\ :sup:`n`-1, plus the size of
  the attic (since I was added it "on top") which I have made to be an
  eighth of the nominal size

  Given that the nominal size is a power of two then one eighth of
  that is similarly easy to calculate.

* ``mask``

  I wondered about the cost of doing modulo arithmetic and decided
  that I would set the nominal hash table size to be 2\ :sup:`n` for
  some *n*.  The highest nominal index is then 2\ :sup:`n`-1.  This
  means that the modulo arithmetic is simply the hashed value masked
  by a series of low-order ones: 0xf, 0x1f, 0x3f, 0x7f, 0xff, ...

* ``count`` is the number of keys in the hash table

* ``start`` is a pointer into the attic as to where to start looking
  for a free index

  This is obviously a time/space trade-off which is only effective
  when you start to get quite big hash tables with a large attic.
  You're now saving the time spent starting at the top of the attic
  looping over all the used slots you checked last time through.

* ``comp_C`` is the :lname:`C` equivalence function pointer

  It must be ``NULL`` to use an :lname:`Idio` equivalence function

* ``hash_C`` is the :lname:`C` hashing function pointer

  It must be ``NULL`` to use an :lname:`Idio` hashing function

* ``comp`` is the :lname:`Idio` equivalence function

* ``hash`` is the :lname:`Idio` hashing function

Reading
-------

A useful reader format for static hash tables uses the tradition
braces syntax common to many programming languages.

``#{ ... }``

The key-value tuples are read as :ref:`pairs`: :samp:`({key} &
{value})`.

``#{ (#\a & "apple") (#\p & "pear")}``

The *value-index* operator, ``.`` works with hash tables:

.. code-block:: console

   Idio> ht := make-hash #n #n 4

   Idio> ht.#\a = "apple"
   Idio> ht.#\p = "pear"
   Idio> ht
   #{ (#\a & "apple")(#\p & "pear")}

Writing
-------

Hash tables will use the ``#{ ... }`` reader format.

Operations
==========

Above and beyond the normal hash table accessors there is a
:lname:`Scheme`-ish functional feel.

:samp:`hash? {value}`

      is :samp:`{value}` a hash table?

:samp:`make-hash [{equiv-func} [{hash-func} [{size}]]]`

      :samp:`{equiv-func}` defines the equivalence function when
      comparing elements in the hash table and can be one of the
      following:

      #. one of the *symbols*:

	 - ``eq?`` meaning use the :lname:`C` implementation of ``eq?``

	 - ``eqv?`` meaning use the :lname:`C` implementation of
           ``eqv?``

	 - ``equal?`` meaning use the :lname:`C` implementation of
           ``equal?``

      #. ``#n`` meaning use the :lname:`C` implementation of
         ``equal?`` (cf. the symbol ``equal?`` above)

	 ``make-hash #n`` and ``make-hash 'equal?`` are equivalent.

      #. an :lname:`Idio` function which should be binary (ie. takes
         two arguments) and returns ``#f`` or some other value

      :samp:`{hash-func}` defines the hashing function for placing
      elements in the hash table and can be one of the following:

      * ``#n`` meaning use the :lname:`C` default hashing function

      * an :lname:`Idio` function which should be unary (ie. takes one
        argument) and returns an integer

      :samp:`{size}` gives :lname:`Idio` a hint as to the size of the
      allocated internal array.  The actual size is likely to be some
      function of the smallest :samp:`2**n - 1` that is greater than
      or equal to :samp:`{size}`.

:samp:`hash-equivalence-function {hash}`

      return the equivalence function being used for the hash table
      :samp:`{hash}`

:samp:`hash-hash-function {hash}`

      return the hashing function being used for the hash table
      :samp:`{hash}`

      This returns ``#n`` for the :lname:`C` default hashing function.

:samp:`hash-size {hash}`

      return the number of elements in hash :samp:`{hash}`

      There is no function to return the actual allocated size though
      :ref:`idio-dump <idio-dump>` might disclose it.

.. _hash-ref:

:samp:`hash-ref {hash} {key} [{default}]`

      return the value at key :samp:`{key}` of hash :samp:`{hash}` or
      :samp:`{default}` if it is not present

      If no :samp:`{default}` is supplied then if :samp:`{key}` is not
      present the ``^rt-hash-key-not-found`` condition will be raised.

:samp:`hash-set! {hash} {key} {value}`

      set the key :samp:`{key}` of hash :samp:`{hash}` to
      :samp:`{value}`

:samp:`hash-delete! {hash} {key}`

      delete the key :samp:`{key}` from hash :samp:`{hash}`

:samp:`hash-exists? {hash} {key}`

      return ``#t`` if the key :samp:`{key}` exists in hash
      :samp:`{hash}` or ``#f`` otherwise

:samp:`hash-keys {hash}`

      return a list of the keys of :samp:`{hash}`

:samp:`hash-values {hash}`

      return a list of the values of :samp:`{hash}`

:samp:`alist->hash {assoc-list}`

      return a hash table constructed from the entries in the
      :term:`association list` :samp:`{assoc-list}`

:samp:`hash-update! {hash} {key} {func} [{default}]`

      set the key :samp:`{key}` of hash :samp:`{hash}` to the result
      of calling :samp:`{func}` on the *existing value* associated
      with :samp:`{key}` in :samp:`{hash}`

      :samp:`{func}` should be a unary function (takes 1 argument!)

      :samp:`{default}` serves the same purpose as for :ref:`hash-ref
      <hash-ref>`

      It is approximately

      :samp:`hash-set! {hash} {key} ({func} (hash-ref {hash} {key}
      [{default}]))`

:samp:`hash-walk {hash} {func}`

      :samp:`{hash}` will be iterated over in some order and
      :samp:`{func}` will be called with each "key value" tuple

      :samp:`{func}` should be a binary function (takes 2 arguments!)

      :samp:`{func}` may modify or otherwise perturb :samp:`{hash}`

:samp:`hash-fold {hash} {func} {val}`

      :samp:`{hash}` will be iterated over in some order and
      :samp:`{func}` will be called with each "key value *val*" tuple

      :samp:`{func}` should be a ternary function (takes 3 arguments!)

      The result of calling the function is the new :samp:`{val}` for
      the next iteration.

      :samp:`{func}` may modify or otherwise perturb :samp:`{hash}`

      The return value is the result of the final call to
      :samp:`{func}`.

:samp:`copy-hash {hash} [{depth}]`

      copy hash :samp:`{hash}`

      :samp:`{depth}` can be the symbol ``'deep`` or ``'shallow``
      where ``'deep`` will recursively copy the elements of
      :samp:`{hash}` whereas ``'shallow`` will just reference the same
      values as in :samp:`{hash}`

:samp:`merge-hash! {hash1} {hash2}`

      this is a destructive merge of the key-value tuples of
      :samp:`{hash2}` into :samp:`{hash1}`

Conditions
----------

``^rt-hash-error-key-not-found``

