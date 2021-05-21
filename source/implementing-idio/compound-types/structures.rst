.. include:: ../../global.rst

**********
Structures
**********

I created :lname:`Idio`'s structures as a sawn-off version of
:ref-title:`LiSP`'s :ref-title:`MEROONET` object-oriented objects (as
I want to go down the :term:`Tiny-CLOS` route for object-oriented
objects) but before seeing SRFI-9_'s Record Types.

:lname:`Idio` structures are similar to but not the same as
:lname:`Scheme` Records.  Ultimately, what we want is an object that
has named fields which we can access by, er, name.

.. sidebox:: It's a naming mess and I cannot claim to have helped the
             situation in any way.

At this point, the words *object* and *value* become even closer
entwined as these structure values are a reduced form of another
language's object oriented objects.  Indeed, they might even be the
basis of an implementation of Tiny-CLOS' objects.

.. sidebox:: This isn't helping either as we now have to manipulate a
             *structure type* and a *structure instance* in the same
             code block.

	     I often end up with ``st`` and ``si``
	     :term:`initialisms <initialism>`.

I think we've seen the broad idea: we define a structure *type* which
gives the structure and its fields names and then we go onto create
*instances* of that structure type.

For a structure *type*:

.. code-block:: idio

   define-struct bar x y

which creates a structure type called ``bar`` with fields ``x`` and
``y``.  This declaration of which would create a number of structure
manipulation functions such as ``make-bar`` and ``bar?``.

For a structure *instance*:

.. code-block:: idio

   foo := make-bar 1 2

whereon I can access the elements with getters and setters:

.. code-block:: idio

   bar-x foo		; 1
   set-bar-y! foo 10
   bar-y foo		; 10

or the more visually pleasing (but computationally expensive):

.. code-block:: idio

   foo.x		; 1
   foo.y = 10
   foo.y		; 10

Ideally, with some savant *type inference*, we might determine that
``foo`` is an instance of ``bar`` and substitute in the most efficient
structure accessing methods possible.  In the meanwhile
``.``/``value-index`` has to work things out the hard way.

Features
========

One aspect of these structures, due to their provenance, is that
*internally* they support a hierarchy.  This is most visible with
conditions:

.. code-block:: idio-console

   Idio> help ^rt-hash-key-not-found-error
   struct-type: ^rt-hash-key-not-found-error  > ^runtime-error > ^idio-error > ^error > ^condition 

   fields (message location detail key)

Here we're seeing that ``^rt-hash-key-not-found-error`` is derived
from a ``^runtime-error`` which is derived from an ``^idio-error``
which is derived from an ``^error`` which is derived from a
``^condition``.

``^rt-hash-key-not-found-error`` appears to have four fields,
``message``, ``location``, ``detail`` and ``key``, although the first
three are actually defined alongside ``^idio-error`` and all derived
conditions inherit those three fields.
``^rt-hash-key-not-found-error`` has added the ``key`` field which is
relevant to the condition.

We can't use inheritance for :lname:`Idio`-defined structure types
because of an issue with recursing up the inheritance tree to find out
what fields have been previously defined in order that we can define a
complete set of accessors.  (This is partly because we could try to
define a structure type using a parent type that hasn't been defined
yet.)

However, where we can inherit, then, for both the structure type and
the structure instance the array of fields (names or values) is the
collection of all inherited fields.  So, the structure type for
``^rt-hash-key-not-found-error`` will have four field names in its
structure, the combination of the three it has inherited plus the one
defined for itself.  Correspondingly, an instance of that type will
have four values.

Implementation
==============

For structure *types*:

.. code-block:: c
   :caption: gc.h

   typedef struct idio_struct_type_s {
       struct idio_s *grey;
       struct idio_s *name;			/* a symbol */
       struct idio_s *parent;			/* a struct-type */
       size_t size;				/* number of fields *including parents* */
       struct idio_s* *fields;			/* an array of strings */
   } idio_struct_type_t;

   #define IDIO_STRUCT_TYPE_GREY(ST)		((ST)->u.struct_type->grey)
   #define IDIO_STRUCT_TYPE_NAME(ST)		((ST)->u.struct_type->name)
   #define IDIO_STRUCT_TYPE_PARENT(ST)		((ST)->u.struct_type->parent)
   #define IDIO_STRUCT_TYPE_SIZE(ST)		((ST)->u.struct_type->size)
   #define IDIO_STRUCT_TYPE_FIELDS(ST,i)	((ST)->u.struct_type->fields[i])

Where, using the examples above:

* ``name`` is the symbol ``bar`` or ``^error``

* ``parent`` is ``#n`` or ``^condition``

* ``size`` is 2 or 0

* ``fields`` is a :lname:`C` array of :lname:`Idio` strings as we will
  (ultimately) index into them with an integer

For structure *instances*:

.. code-block:: c
   :caption: gc.h

   typedef struct idio_struct_instance_s {
       struct idio_s *grey;
       struct idio_s *type;			/* a struct-type */
       struct idio_s* *fields;			/* an array */
   } idio_struct_instance_t;

   #define IDIO_STRUCT_INSTANCE_GREY(SI)	((SI)->u.struct_instance.grey)
   #define IDIO_STRUCT_INSTANCE_TYPE(SI)	((SI)->u.struct_instance.type)
   #define IDIO_STRUCT_INSTANCE_FIELDS(SI,i)	((SI)->u.struct_instance.fields[i])

   #define IDIO_STRUCT_INSTANCE_SIZE(SI)	(IDIO_STRUCT_TYPE_SIZE(IDIO_STRUCT_INSTANCE_TYPE(SI)))

where:

* ``type`` is a reference to a structure *type* (duh!)

* ``fields`` are a :lname:`C` array of :lname:`Idio` values which we
  can index with an integer

Clearly, the accessor functions can be made to be relatively quick if
we can translate a field name into a field index after which accessing
a structure instance's field value is a simple array index.

Reading
=======

There is no reader input form for either a structure type or a
structure instance.

Writing
=======

In both case we'll use an invalid reader input form, ``#<...>``.

For structure types we want to recurse through the structure
inheritance hierarchy printing out field names as we go:

.. code-block:: idio-console

   Idio> ^idio-error
   #<ST ^idio-error #<ST ^error #<ST ^condition #n>> message location detail>

Note the leading ``ST`` for structure type.  The ``#n`` following
``^condition`` indicates that ``^condition`` does not inherit from
anything else, it is the root of this hierarchy.

For structure instances we want the structure type and the values of
the fields (with their names!):

.. code-block:: idio-console

   Idio> make-condition ^idio-error "msg" "loc" "det"
   #<SI ^idio-error message:"msg" location:"loc" detail:"det">

Note the leading ``SI`` for structure instance.

:lname:`C` / :lname:`Idio` Overlap
==================================

Manipulating structure *types* is complicated because there are
several types which we want to manipulate in both :lname:`C` and
:lname:`Idio` -- conditions are the obvious example: they are
generally raised in :lname:`C` and we want to write handlers for them
in :lname:`Idio`.

The structure type is defined in :lname:`C`, usually, as it is needed
long before the VM gets to run.  :lname:`C` however, can manipulate
the structure elements directly and doesn't need accessors etc..  All
it does need to do is add the structure type's name into the
environment.

That itself is repetitive and mildly complicated, so there are a bunch
of :lname:`C` macros to help.  For conditions:

.. code-block:: c
   :caption: condition.h

   #define IDIO_DEFINE_CONDITION0(v,n,p) ... *stuff*

where

* :samp:`{v}` is the :lname:`C` variable name we want to manipulate
  (which was declared with ``external`` linkage etc.)

* :samp:`{n}` is the :lname:`C` string name -- to be converted to an
  :lname:`Idio` *symbol*

* :samp:`{p}` is the parent type

The ``0`` in the :lname:`C` macro name is indicating that there are
zero fields associated with this condition type.

``IDIO_DEFINE_CONDITION2(v,n,p,f1,f2)`` indicates there are two fields
to be added.

The macros get used in the likes of:

.. code-block:: c
   :caption: ``idio_init_condition()`` in :file:`condition.c`

   IDIO_DEFINE_CONDITION0 (idio_condition_error_type,
			   "^error",
			   idio_condition_condition_type);

.. rst-class:: center

\*

:lname:`Idio`, on the other hand, only needs the accessors -- so long
as the name exists.  However, we can flip things around a bit.  Rather
than having two roughly similar forms we can make ``define-struct`` a
wrapper to what would have been the specialized
``define-struct-accessors-only``.

.. code-block:: idio
   :caption: struct.idio

   define-template (define-struct name & fields) {
     #T{
       ;; define bar (make-struct-type 'bar #n '(x y))
       define $name (make-struct-type '$name #n '$fields)

       define-struct-accessors-only $name $@fields
     }
   }

This requires a :samp:`make-struct-type {name} {parent} {fields}` form
(in :file:`struct.c`) which will return a structure *type* value which
is set in the environment as ``$name`` -- ``define-struct`` is a
template, remember, so ``$name`` expands out to whatever the first
argument to ``define-struct`` was.

Note that the :samp:`{parent}` argument is always ``#n``.

``define-struct-accessors-only`` is now the generic form for
constructing all the accessory methods: :samp:`make-{name}`,
:samp:`{name}?` etc..

``define-struct-accessors-only`` (in :file:`struct.idio`) is quite
complicated as it involves templates generating templates using
constructed and generated symbols.  There's some examples in the
commentary that show the expanded forms which might make it a bit
easier to read.

Now we have ``define-struct-accessors-only`` we can use it for our
conditions (defined in :lname:`C`) ... except -- for reasons I don't
quite recall but I'm sure they were good -- conditions have a similar
but not quite the same system.  So, in fact, we call:

.. code-block:: idio
   :caption: condition.idio

   define-condition-type-accessors-only ^error ^condition error?

which is going to define ``error?`` as a predicate testing that the
value passed is a condition and is an instance of the ``^error``
condition type.  There are no fields so no field accessors are
created.

.. code-block:: idio
   :caption: condition.idio

   define-condition-type-accessors-only ^rt-hash-key-not-found-error ^runtime-error rt-hash-key-not-found-error? \
	(key rt-hash-key-not-found-error-key)

Here, in addition to the ``rt-hash-key-not-found-error?`` predicate we
will define an accessor, ``rt-hash-key-not-found-error-key`` for the
field ``key``.

Arguably we could have derived the accessor name from the condition
type name and the key but this method allows some flexibility in
naming.

Operations
==========

Structure Types
---------------

:samp:`make-struct-type {name} {parent} {fields}`

      create a structure *type* called :samp:`{name}` with inheriting
      from the :samp:`{parent}` structure type and adding
      :samp:`{fields}`

:samp:`struct-type? {value}`

      Is :samp:`{value}` a structure *type*

:samp:`struct-type-name {st}`

      return the structure type's name from :samp:`{st}`

:samp:`struct-type-parent {st}`

      return the structure type's parent from :samp:`{st}`

:samp:`struct-type-fields {st}`

      return the structure type's fields from :samp:`{st}`

:samp:`struct-type-isa {st} {type}`

      return ``#f`` unless the structure type of :samp:`{st}` is
      :samp:`{type}` in which case return ``#t``

:samp:`struct-type-isa {st} {type}`

      return ``#f`` unless the structure type of :samp:`{st}` is
      :samp:`{type}` in which case return ``#t``

Structure Instances
-------------------

:samp:`make-struct-instance {st} {values}`

      create a structure *instance* of structure type :samp:`{st}`
      with values :samp:`{values}`

:samp:`struct-instance? {value}`

      Is :samp:`{value}` a structure *instance*

:samp:`struct-instance-type {si}`

      return the structure instance's structure type from :samp:`{si}`

:samp:`struct-instance-fields {si}`

      return the structure instance's fields from :samp:`{si}`

      This is returning the values of the structure instance.  I guess
      the name could be better...

:samp:`struct-instance-ref {si} {field}`

      return the value of :samp:`{field}` from structure instance
      :samp:`{si}`

      If :samp:`{field}` is not a field of the type of :samp:`{si}`
      then a ``^runtime-error`` condition will be raised.

:samp:`struct-instance-set! {si} {field} {value}`

      set the value of field :samp:`{field}` in structure instance
      :samp:`{si}` to be :samp:`{value}`

      If :samp:`{field}` is not a field of the type of :samp:`{si}`
      then a ``^runtime-error`` condition will be raised.

:samp:`struct-instance-isa {si} {st}`

      return ``#f`` unless the structure instance of :samp:`{si}` is
      :samp:`{st}` in which case return ``#t``


.. include:: ../../commit.rst

