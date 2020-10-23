.. include:: ../../global.rst

.. _setters:

*******
Setters
*******

Setters comes from the idea of a :lname:`Scheme` generalised ``set!``
-- described in SRFI-17_.

I've not followed that directly but rustled up something along the
same lines.

The Problem
===========

The basic question is: how do I ``set!`` (assign to!) something that
isn't a simple variable?

An even more basic question might be *why* do you want to assign to
such a thing?  Look, it happens!

In fact, we're going to make it happen.  We allow the idea of
accessing some indexable value, like an array, using the ``.`` or
``value-index`` operator: :samp:`{a}.{i}`.

That is translated into :samp:`value-index {a} {i}` and
``value-index`` will test whether :samp:`{a}` is an array or hash
table or structure instance or a list and then try to use :samp:`{i}`
to access an element of it.

Cool.  Not exactly efficient but cool.

Now, what happens when we want to *assign* to that indexed value?
Sounds innocent enough.  :samp:`{a}.{i} = 3` is going to see a couple
of transformations into:

.. parsed-literal::

   set! (value-index *a* *i*) 3

*Ooh eck!*  That looks like we're trying to assign to the *result* of a
function call!  That's not going to end well.

SRFI-17 has a neat solution.  We won't assign to the result of a
function call -- because that really is madness -- but rather we'll
make a subtle transformation:

.. code-block:: idio

   set! (foo ...) expr

will be transformed into:

.. code-block:: idio

   (setter foo) ... expr

:socrates:`Eh?` We'll separate out the function call name -- this will
only work for named functions -- and the arguments to that
function call then we'll construct a replacement statement which has:

* a call to a function called ``setter`` with the function call name as an argument

* the original arguments to the original function call

* the expression we want assigned

``setter``'s job is to find out what the "setter" of a given function
is.  So :samp:`(setter {foo})` is asking for the "setter of
:samp:`{foo}`", ie. the function that is capable of "setting"
something when we're ostensibly making a call to :samp:`{foo}`.

Let's divert with a quick example.  Suppose I have a pair, ``p``, and
I've created the following:

.. code-block:: idio

   set! (ph p) 3

which we now know is going to be transformed into:

.. code-block:: idio

   (setter ph) p 3

what "setter of ``ph``" can possibly solve that conundrum?  Well,
let's try... *\*shuffles pack\** ... ``set-ph!``.  Let's suppose that
``(setter ph)`` returns ``set-ph!`` (or the value of, anyway).  Let's
try that:

.. code-block:: idio

   set-ph! p 3

Why, wouldn't you just know it?  That works!  That is *exactly* what
we want: ``set-ph!`` expects two arguments, a pair and a value, and
then will make the head of the pair refer to the value.

OK, now that we know it's possible, we simply need to set up a nice
table of setters.  How do I "set the setter of :samp:`{foo}`"?  This
is looking a bit gnarly but if we just lay it out it'll be:

.. code-block:: idio

   set! (setter foo) setter-of-foo

Which we've just suggested is setting the result of a function call
for which we know the formula:

.. code-block:: idio

   (setter setter) foo setter-of-foo

Almost!  What this is saying is that ``setter`` needs a setter whose
job is to set the setter of its first argument.

If we can bootstrap everything with a "setter of setter" then the rest
just falls into place like magic.

Implementation
==============

The implementation uses what might be called property lists but are
little hash tables associated with a value.  So there is a big
"properties" table, indexed by values, which gives you a little hash
table of per-value properties, indexed by some keywords.  An obvious
keyword, here, is ``:setter``.  In :lname:`C` that becomes
``idio_KW_setter``.

We need a hook to get us going.  That's going to be a primitive called
``setter`` whose job is to return the ``:setter`` property for some
procedure, ``p`` -- I'm using "procedure" to mean either a primitive
or a closure:

.. code-block:: c
   :caption: :file:`closure.c`

   IDIO_DEFINE_PRIMITIVE1_DS ("setter", setter, (IDIO p), ...)
   {
       ...

       IDIO setter = idio_get_property (p, idio_KW_setter, IDIO_LIST1 (idio_S_false));

       if (idio_S_false == setter) {
	   idio_error_C ("no setter defined", p, IDIO_C_FUNC_LOCATION ());
       }

       return setter;
   }

Reasonably straightforward.  The fun is in :file:`closure.idio`.

In the first instance, we'll ask for the "keyword table",
``setter-kwt``, for ``setter`` and create one if it doesn't exist.

.. sidebox::

   Weren't you paying attention?

What is ``setter``?  *Really?* We defined it as a primitive a moment
ago.

.. code-block:: idio
   :caption: :file:`closure.idio`

     setter-kwt := %properties setter
     if (null? setter-kwt) {
       setter-kwt = make-keyword-table 4
       %set-properties! setter setter-kwt
     }

(We would *expect* the properties table for ``setter`` to not exist
but it might.  So we're just covering bases, here.)

Now the interesting bit.  The "setter of setter" is a function that is
going to be called with two arguments: a procedure, ``p``, and a
setter, ``s``, for that procedure: :samp:`function (p s) ...`.

This function's job is then to dig out the keyword table for ``p`` and
assign ``s`` to the ``:setter`` keyword in that table.  Something
like:

.. code-block:: idio

   function (p s) {
     p-kwt := %properties p
     if (null? p-kwt) {
       p-kwt = make-keyword-table 4
       %set-properties! proc p-kwt
     }

     keyword-set! p-kwt :setter s
   }



Of course, this function that we're defining wants to be set as the
``:setter`` in the ``setter-kwt`` table -- thus bootstrapping the
whole shenanigans.

In the :lname:`Scheme`-ish way, we'll do it all in one (and use
confusing names in place of ``p`` and ``s``):

.. code-block:: idio
   :caption: :file:`closure.idio`

     keyword-set! setter-kwt :setter (function (proc setter) {
					proc-kwt := %properties proc
					if (null? proc-kwt) {
					  proc-kwt = make-keyword-table 4
					  %set-properties! proc proc-kwt
					}

					keyword-set! proc-kwt :setter setter
     })

Not quite done yet.  Let's fill in some standard setters:

.. code-block:: idio
   :caption: :file:`closure.idio`

   set! (setter ph)				set-ph!
   set! (setter pt)				set-pt!
   set! (setter array-ref)			array-set!
   set! (setter hash-ref)			hash-set!
   set! (setter string-ref)			string-set!
   set! (setter struct-instance-ref)		struct-instance-set!

   set! (setter value-index)			set-value-index!

.. include:: ../../commit.rst

