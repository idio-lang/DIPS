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

I have had no end of trouble with my implementation.  Eventually I
gave up and scrapped it in favour of the traditional bucket and chain
mechanism.

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

Hashing and Equivalence
-----------------------

We should have (and, indeed, *require*) user-defined hashing and
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
  positive integer

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
(read: must) flag the *value* associated with the key as being seen
(otherwise we'd garbage collect the properties themselves!).

Subsequently, if the function value is still ultimately referred to
from a root value then all is well and if the function value is no
longer referred to from a root value then we don't keep it around
artificially.

This leaves a problem, however, in that the (now garbage collected)
key is still in the properties hash.  We need some special trickery in
the GC to remove it from the properties hash at the time of collection
(and, in a later cycle, collect the values previously associated with
the key).

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
       struct idio_hash_entry_s *next;
       struct idio_s *key;
       struct idio_s *value;
   } idio_hash_entry_t;

   #define IDIO_HASH_HE_NEXT(HE)	((HE)->next)
   #define IDIO_HASH_HE_KEY(HE)		((HE)->key)
   #define IDIO_HASH_HE_VALUE(HE)	((HE)->value)

   #define IDIO_HASH_FLAG_NONE		0
   #define IDIO_HASH_FLAG_STRING_KEYS	(1<<0)
   #define IDIO_HASH_FLAG_WEAK_KEYS	(1<<1)

   typedef struct idio_hash_s {
       struct idio_s *grey;
       idio_hi_t size;
       idio_hi_t mask;			/* bitmask for easy modulo arithmetic */
       idio_hi_t count;			/* (key) count */
       int (*comp_C) (void *k1, void *k2);	/* C equivalence function */
       idio_hi_t (*hash_C) (struct idio_s *h, void *k); /* C hashing function */
       struct idio_s *comp;		/* user-supplied comparator */
       struct idio_s *hash;		/* user-supplied hashing function */
       idio_hash_entry_t* *ha;		/* a C array */
   } idio_hash_t;

   #define IDIO_HASH_GREY(H)		((H)->u.hash->grey)
   #define IDIO_HASH_SIZE(H)		((H)->u.hash->size)
   #define IDIO_HASH_MASK(H)		((H)->u.hash->mask)
   #define IDIO_HASH_COUNT(H)		((H)->u.hash->count)
   #define IDIO_HASH_COMP_C(H)		((H)->u.hash->comp_C)
   #define IDIO_HASH_HASH_C(H)		((H)->u.hash->hash_C)
   #define IDIO_HASH_COMP(H)		((H)->u.hash->comp)
   #define IDIO_HASH_HASH(H)		((H)->u.hash->hash)
   #define IDIO_HASH_HA(H,i)		((H)->u.hash->ha[i])
   #define IDIO_HASH_FLAGS(H)		((H)->tflags)

Here we have:

* ``size`` is the nominal hash size, 2\ :sup:`n`

* ``mask``

  I wondered about the cost of doing modulo arithmetic and decided
  that I would set the nominal hash table size to be 2\ :sup:`n` for
  some *n*.  The highest nominal index is then 2\ :sup:`n`-1.  This
  means that the modulo arithmetic is simply the hashed value masked
  by a series of low-order ones: 0xf, 0x1f, 0x3f, 0x7f, 0xff, ...

* ``count`` is the number of keys in the hash table

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

.. code-block:: idio-console

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

.. idio:function:: hash? value

   is `value` a hash table?

.. idio:function:: make-hash [equiv-func [hash-func [size]]]

   `equiv-func` defines the equivalence function when comparing
   elements in the hash table and can be one of the following:

   #. one of the *symbols*:

      - ``eq?`` meaning use the :lname:`C` implementation of ``eq?``

      - ``eqv?`` meaning use the :lname:`C` implementation of ``eqv?``

      - ``equal?`` meaning use the :lname:`C` implementation of
        ``equal?``

   #. ``#n`` meaning use the :lname:`C` implementation of ``equal?``
      (cf. the symbol ``equal?`` above)

      ``make-hash #n`` and ``make-hash 'equal?`` are equivalent.

   #. an :lname:`Idio` function which should be binary (ie. takes two
      arguments) and returns ``#f`` or some other value

   `hash-func` defines the hashing function for placing elements in
   the hash table and can be one of the following:

   * ``#n`` meaning use the :lname:`C` default hashing function

   * an :lname:`Idio` function which should be unary (ie. takes one
     argument) and returns an integer

   `size` gives :lname:`Idio` a hint as to the size of the allocated
   internal array.  The actual size is likely to be some function of
   the smallest `2**n - 1` that is greater than or equal to `size`.

   The ``eqv?`` equivalence function is nearly useless, on reflection.
   The problem is not that ``eqv?`` doesn't work but rather that
   whilst ``1`` and ``1.0`` are equivalent according to ``eqv?`` they
   will be hashed differently because they are different types,
   meaning they will most likely land in different buckets and
   therefore there is unlikely to be anything to be ``eqv?`` against
   in the found chain.

   I'm leaving it in because 1) I can and b) someone might derive a
   hashing function where two numbers that would be ``eqv?`` generate
   the same hash value.

.. idio:function:: hash-equivalence-function hash

   return the equivalence function being used for the hash table
   `hash`

.. idio:function:: hash-hash-function hash

   return the hashing function being used for the hash table `hash`

   This returns ``#n`` for the :lname:`C` default hashing function.

.. idio:function:: hash-size hash

   return the number of elements in hash `hash`

   There is no function to return the actual allocated size though
   :ref:`idio-dump <idio-dump>` might disclose it.

.. _hash-ref:

.. idio:function:: hash-ref hash key [default]

   return the value at key `key` of hash `hash` or `default` if it is
   not present

   If no `default` is supplied then if `key` is not present the
   ``^rt-hash-key-not-found`` condition will be raised.

.. idio:function:: hash-set! hash key value

   set the key `key` of hash `hash` to `value`

.. idio:function:: hash-delete! hash key

   delete the key `key` from hash `hash`

.. idio:function:: hash-exists? hash key

   return ``#t`` if the key `key` exists in hash `hash` or ``#f``
   otherwise

.. idio:function:: hash-keys hash

   return a list of the keys of `hash`

.. idio:function:: hash-values hash

   return a list of the values of `hash`

.. idio:function:: alist->hash assoc-list

   return a hash table constructed from the entries in the
   :term:`association list` `assoc-list`

.. idio:function:: hash-update! hash key func [default]

   set the key `key` of hash `hash` to the result of calling `func` on
   the *existing value* associated with `key` in `hash`

   `func` should be a unary function (takes 1 argument!)

   `default` serves the same purpose as for :ref:`hash-ref
      <hash-ref>`

   It is approximately:

   .. code-block:: idio

      hash-set! hash key (func (hash-ref hash key [default]))

.. idio:function:: hash-walk hash func

   `hash` will be iterated over in some order and `func` will be
   called with each "key value" tuple

   `func` should be a binary function (takes 2 arguments!)

   `func` may modify or otherwise perturb `hash`

.. idio:function:: hash-fold hash func val

   `hash` will be iterated over in some order and `func` will be
   called with each "key value *val*" tuple

   `func` should be a ternary function (takes 3 arguments!)

   The result of calling the function is the new `val` for the next
   iteration.

   `func` may modify or otherwise perturb `hash`

   The return value is the result of the final call to `func`.

.. idio:function:: copy-hash hash [depth]

   copy hash `hash`

   `depth` can be the symbol ``'deep`` or ``'shallow`` where ``'deep``
   will recursively copy the elements of `hash` whereas ``'shallow``
   will just reference the same values as in `hash`

.. idio:function:: merge-hash! hash1 hash2

   this is a destructive merge of the key-value tuples of `hash2` into
   `hash1`

Conditions
----------

.. idio:condition:: ``^rt-hash-error-key-not-found``


.. include:: ../../commit.rst

