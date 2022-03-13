.. include:: ../../global.rst

******************
Idio Object System
******************

.. aside::

   Well, it's clearly the way *we* are going to go, whether it's the
   right way is another matter entirely.

:lname:`Tiny CLOS`, as described in the previous section, is clearly
the way to go.  There are other real-world implementations that we
can, *\*coughs\**, learn from and re-imagine.

Let's start with trying to visualize the user experience and then ask
how we might implement it.

User Interface
==============

We want a reasonably clean user interface where we want do the heavy
lifting behind the scenes.

I think there's probably only three regular user interfaces:
``define-class``, ``define-method`` and ``make-instance``.

define-class
------------

I can see a few variations on a theme, here:

.. code-block:: idio

   define-class A		; A is implicitly a sub-class of <object>

   define-class B A		; B is a sub-class of A

   define-class C (A)		; C is also a sub-class of A just passed as a list

   define-class D (B C)		; D is a sub-class of both B and C

If we want to pass slot names, they should just appear as a list
tacked on the end.  The only problem was with the definition of ``A``
where we didn't pass a super-class.  We'll have to explicitly pass
``#n`` (or, ``<object>``, I suppose, but best left for the system to
decide):

.. code-block:: idio

   define-class A #n a b c

   define-class B A b c d

   define-class C (A) c d e

   define-class D (B C)	d e f

Here, I've deliberately given some over-lapping slot names.  Slot
names are not special, either by class or order.  They just need to be
distinct.

In this case, ``D``'s slots are ``d e f b c a`` which is more or less
related to ``D``'s CPL, ``D B C A <object> <top>``, but there's
nothing special about that.  ``C``'s slots are ``c d e a b`` which
seems completely different but really doesn't matter.  The point is
that they *have* those slots, not what order they are in.

When we are defining slots we probably want to define or declare some
initial value and/or means for the user to override the initial value.

For the declaration, we might allow the slot to be declared with some
slot options such as :samp:`({name} :initform {func})` where the plain
slot name, as used above, might be equivalent to :samp:`({name}
:initform default-slot-value)` and :ref:`default-slot-value
<object/default-slot-value>` is a primitive returning, say, ``#f``.

When the user comes to create an instance of a class they might want
to override :samp:`{init-expr}`.  Taking the lead from
:lname:`Swindle`, the use of ``:initarg`` is interesting:

.. code-block:: idio

   define-class A #n a (b) (c :initarg :cee)

The slot ``a`` has no ``:initarg``, it will just get the
:ref:`default-slot-value <object/default-slot-value>`.

The slot ``b``, because it was declared in a list, will get an
implicit ``:initarg`` of ``:b`` unless an explicit ``:initarg`` is
supplied, as in the case for slot ``c``.

.. code-block:: idio

   a1 := make-instance A
   b1 := make-instance A :b 2			; slot b is 2
   c1 := make-instance A :cee 3			; slot c is 3

Any slots not explicitly overridden will get the
:ref:`default-slot-value <object/default-slot-value>` value.

define-method
-------------

Generic methods, whilst fundamental to the workings of the object
system, are, in some way, incidental to the usage of the object
system.  The creation of a generic function is exactly the sort of
chore that users will forget to do.

:lname:`STklos` covers that by having a macro (template),
``define-method``, which ensures that the underlying generic function
is created before adding the method to the generic function.  That
seems much more reasonable.

.. aside::

   *Be off with you, administrative guff!*

Users will be reasoning about the behaviour of (their part of) the
object system through the classes they create and the methods
associated with those classes.  Anything else is administrative guff.

So, as seen previously:

.. code-block:: idio

   define-method (foo arg1 (arg2 D) (arg3 B)) {
     ...
   }

implicitly defines the generic function ``foo`` (if ``foo`` is not
already defined as a generic function) and will add a three-argument
method where ``arg1`` has no specializer (therefore defaulting to
``<object>``), ``arg2`` is specialized for class ``D`` and ``arg3`` is
specialized for class ``B``.

From the argument list to ``define-method`` we'll have a function-like
:samp:`(name & formals)` and each formal argument can be
:samp:`({name} {class})` or just :samp:`{name}`.

On the one hand, we can walk around collecting the formal parameter
names for the function to go in the method ``procedure`` slot and on
the other hand walk around collecting the specializer classes
(defaulting to ``<top>``) for the method ``specializers`` slot.

make-instance
-------------

``make-instance`` shouldn't be left to do anything much of interest.

Implementation
==============

Let's try to flesh this out.

One obvious change to :lname:`Tiny CLOS` is to follow in the footsteps
of :lname:`STklos` and put the object system bootstrap in :lname:`C`.

A first pass suggests that ``compute-apply-generic`` is very slow in
pure :lname:`Idio` and, like :lname:`STklos`, could do with a
:lname:`C` variant.

Memory Model
------------

Pure :lname:`Scheme` doesn't have rich data types but :lname:`Idio`
does and collections of named values sounds very much like
:ref:`structs <ref:struct type>`.

In practice, much of the element access can be managed through direct
indexing which :lname:`Idio` structs support.

This will cause us some issues in that we now need to distinguish
between regular struct-instances and a self-describing object system
layered on top.

Structure(s)
^^^^^^^^^^^^

The existing :lname:`C` construction uses a combination of enums which
is partly as a result of experimentation but is also sort of correct.

We have four kinds of instance structure:

#. all instances have a meta-class and an instance proc

   An actual instance (of a class) will have a further ``nfields``
   slots based on its meta-class.

#. class instances (*sigh*, unhelpful name overloading), by which I
   mean things like ``<class>``, then have, in addition to the
   meta-class and instance proc slots, the :lname:`Tint CLOS` slots,
   slightly massaged:

   * ``name`` -- useful for debug if nothing else

   * ``direct-supers``

   * ``direct-slots``

   * ``cpl``

   * ``slots``

   * ``nfields``

   * ``getters-n-setters``

     which will now takes the form: :samp:`(... (name init-function
     getter [setter]) ...)`

     There's a little :lname:`STklos`-trick we can pull here.  Rather
     than the :lname:`Tiny CLOS`-style function-getter -- which
     defaults to, essentially, ``(vector-ref vector index)`` -- we can
     optionally, and by default, put an integer.

     We can then test ``getter`` to see if it is an integer and, if
     so, we can call the :lname:`C` equivalent of
     :ref:`%struct-instance-ref-direct
     <ref:%struct-instance-ref-direct>` ourselves.  If ``getter`` is a
     function then we can invoke it.

#. generic function instances have slots:

   * ``name``

   * ``documentation``

   * ``methods``

#. method instances have slots:

   * ``generic-function``

   * ``specializers``

   * ``procedure``

dump-instance
^^^^^^^^^^^^^

As soon as you have a data structure of any complexity (and a
self-referential one sure fits that description) then you'll want
something to tell you what you have in your hands:

.. code-block:: idio-console

   Idio> dump-instance initialize
   generic of <generic>:
    name:          initialize
    documentation: "...blah blah..."
    methods:       (<method> <top>)
		   (<generic> <top>)
		   (<class> <top>)
		   (<object> <top>)

   Idio> dump-instance <class>
   class <class>:
      class:<class>
     supers:(<object>)
    d-slots:(name direct-supers direct-slots cpl slots nfields getters-n-setters)
	cpl:(<class> <object> <top>)
      slots:(name direct-supers direct-slots cpl slots nfields getters-n-setters)
    nfields:7
	gns:((getters-n-setters #<PRIM default-slot-value> 6) (nfields #<PRIM default-slot-value> 5) (slots #<PRIM default-slot-value> 4) (cpl #<PRIM default-slot-value> 3) (direct-slots #<PRIM default-slot-value> 2) (direct-supers #<PRIM default-slot-value> 1) (name #<PRIM default-slot-value> 0))

.. include:: ../../commit.rst

