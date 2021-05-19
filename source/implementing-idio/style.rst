.. include:: ../global.rst

*******************
:lname:`Idio` Style
*******************

I can't say I'm a huge fan of imposing style on other people but we
should probably consider adhering to some *conventions* to make life
easier for everyone approaching a piece of code and looking to make
sense of it.

That said, I notice I am becoming (become?) a creature of habit
resulting in moderately consistent look and feel.  Much of which, I
confess, is the result of either endemic casual errors or repeatedly
having to go back and add debug statements such that I write the code
*expecting* to have to come back to add the debug statement and so put
the infrastructure in place first.

Some of this is a recognition of my own failings which will, of
course, remain in the code until discovered.

Names
=====

We have to create names in the code for which there are many
opportunities to sow confusion not because the name doesn't describe
what the function is doing, say, but because the tense and
passive/active sense of the actors means that we can't tell if someone
else has already solved this problem.  Does ``array-ref`` do the same
as ``ref-array``?  Should we "ref" something or "get" it or something
else entirely?  Does the absence of the one mean the functionality is
covered or that it needs to be written?

I'm going to propose that we have two headline rules (using imperative
verbs):

#. *verb* - *noun*

   Here we are performing some query or imperative action on a value
   -- the whole value, not some sub-part of it:

   .. parsed-literal::

      make-array *size* [*default*]

      copy-array *array*

#. *noun* - *verb* or *attribute* or *element*

   Here we are accessing some part or characteristic of a value -- and
   in particular, not the whole value:

   .. parsed-literal::
     
      array-ref *array* *index*

      array-set! *array* *index* *value*

      array-fill! *array* *value*

      array-length *array*

``array-ref`` with the intention to return the entire array rather
than an element is semi-nonsensical as you would simply pass the array
itself.  Similarly ``array-set!`` with a whole array?  What is the
intention, what are you trying to do?

By way of some possibly confusing examples, on the one hand, if we
want to set a fixed attribute of a compound element then we use the
former variant, eg. ``set-ph!``.  On the other hand, from the
:ref:`C-api`, the likes of ``struct-rlimit-set!`` go the other way
because the function needs to be told which (of several) elements to
set (like setting an array element).

There are, of course, anomalies which could be fixed.  Pairs/lists are
a case in point.  The constructors are ``pair`` & ``list`` (rather
than ``make-pair`` & ``make-list``) and the accessors, nominally,
``pair-head`` and ``pair-tail``, are truncated to ``ph`` and ``pt``
and their derivatives.  These are used *so* often that if you didn't
have some circumscribed name you would simply create it -- hence,
``phht`` etc..

All of the predicates are exceptions though that's because we can use
a question mark in names:

.. parsed-literal::

   array? *array*

On the subject of ``-ref`` vs. ``-get`` I fall into the former camp.
We *are* only making a reference to the underlying value.  We are
**not** in any sense "getting" it and thus removing from the clutches
of another.  There are any number of venerable texts on good English
grammar (whether you think such a thing is an oxymoron or a quixotic
*cri de couer*) which decry the use of "get" and "got".  Here it is
simply not accurate.

There are cases where it is (more) accurate as in
``get-output-string`` (to return the contents of a dynamic output
string).  Here, the string you are given did not exist previously and,
indeed, if you call it again will return a *different* string (albeit
the content is the same).  You might argue that it should be
``return-output-string`` or ``make-output-string`` some other
imperative verb-noun construction but I think the intention is clear
-- and you *are* getting something that no-one else will!

.. rst-class:: center

---

.. sidebox:: The Microsoft equivalent is the registry key
             ``FullSecureChannelProtection=1`` which
             lives... *somewhere*.

I'm also a fan of meaningful user-facing names.  I'm reading that the
magic flag in the Samba_ 4.x release for the Windows AD (actually
Netlogon protocol, hence Samba being affected) ZeroLogon_ bug is
``server schannel = yes`` where ``schannel`` indicates a secure
netlogon channel.  That's really not very obvious, either the nearly
invisible leading ``s`` or that it has anything to do with security or
netlogon.  Text, like whitespace, is free.

Here, we could get into a mess about the semantics of configuration
files, are we defining some set of parameters or making some
(actionable) statement?

.. code-block:: console

   secure netlogon channel = yes

   require secure netlogon channel

Either way, some clarity of intent makes life easier for everybody.

:lname:`C` Naming Convention
----------------------------

:lname:`C` should work under the same regulations with a couple of
important additions which derive some some fanciful idea that
:lname:`Idio` could be embedded in some larger program.  What we need
is for all :lname:`Idio` names to be unique in someone's program.

There's a simple fix for that: prefix everything with ``idio_`` or
``IDIO_``.  *Boom!* Job done.

Actually, that requires a little clarification.

I've made all :lname:`C` preprocessor macros have names in upper case.
That's fairly common.  There are a lot of quite involved macros (for
me) and so if something is a macro it should stand out:

.. code-block:: c

   {
       IDIO_ASSERT (o);

       ...
   }

performs, as you might guess, some basic checks on the internal state
of the value ``o``.  In fact what ``IDIO_ASSERT()`` does varies
depending on how much debugging information is being compiled in.

For local macros you should make the macro name local using the file
name as an additional prefix plus any suitable functional prefix:
``IDIO_READ_CHARACTER_SIMPLE`` is a simple value in :file:`read.c`
used as a flag in the code for inputting characters.

All other :lname:`C` names with external linkage should be prefixed
with ``idio_`` and it should be the case that all :lname:`C` static
names are too.

Hopefully, the only non-:lname:`Idio`-ified name in the code is
``main``.

Lexical names are a bit more problematic.  As a standard lazy
programmer I will use the shortest coherent name that makes sense *in
context*.  Of course, you only discover how effective that has been
when you return to the code some time later to be left scratching your
head as to what some variable represents.

I suspect I am a subconscious subscriber to :term:`initialism`: ``l``
for a list, ``p`` for a pair, ``a`` for an array, ``h``/``ht`` for a
hash (or hash table, depending on mood) etc..  I usually use ``r`` for
the value to be returned (see below).

One variant on that is the surprisingly rare case of passing an
:lname:`Idio` value into a function and extracting the underlying
:lname:`C` value from it.  You have two variables presenting the same
value -- just trussed up in different ways.  This happens with
integers but relatively rarely elsewhere (as :lname:`C` doesn't
support complex types).

Here, we should probably use some pseudo-Hungarian notation where
``x_I`` is the :lname:`Idio` variant and ``x_C`` is the :lname:`C`
variant.  I know, though, that I've used ``Ix`` and ``Cx`` and
elsewhere one variant doesn't use a prefix/suffix and the other does.

I have used ``ci`` for the :lname:`C` value of a "constant index" (or
index into the table of constants) and ``fci`` for the :lname:`Idio`
*fixnum* variant.

*Mea culpa.*

We have to be slightly careful as many :lname:`C` functions are the
*primitive* implementations of :lname:`Idio` functions.  The
:lname:`C` function will take arguments that should be named after the
nominal :lname:`Idio` argument names.  That, of course, precludes any
enforced prefix/suffix notation for both the :lname:`Idio` and
:lname:`C` variants.

Symbols
^^^^^^^

All of the standard :lname:`Idio` symbolic names/values are available
in :lname:`C`.  They are all prefixed ``idio_S_`` with the ``S``
meaning "symbol".

They aren't all quite like-for-like but the majority are:

.. csv-table:: symbols
   :header: "C", "Idio"
   :align: left

   ``idio_S_nil``, ``#n``
   ``idio_S_true``, ``#t``
   ``idio_S_false``, ``#f``
   ``idio_S_if``, ``if``
   ``idio_S_define``, ``define``
   ``idio_S_quote``, ``quote``
   
There are a few other classes of :lname:`Idio` values that are used in
:lname:`C`:

.. csv-table:: classes of values
   :header: "prefix", "usage"
   :align: left

   ``idio_S_``, symbols -- as above
   ``idio_T_``, reader tokens
   ``idio_I_``, intermediate code
   ``idio_KW_``, keywords

You get the idea!
   
:lname:`Idio` Naming Convention
-------------------------------

It would be nice to have some consistency in :lname:`Idio` names.
We've seen hints of a triplet of names associated with a *type*:
:samp:`{type-name}?`, :samp:`{type-name}-ref` and
:samp:`{type-name}-set!`.  That *isn't* consistently applied as we saw
above with pair/list handling functions.

In the :ref:`C-api` and for names in the ``libc`` module I've tried to
use the :lname:`C` names where possible.  This is partly from the
familiarity aspect in that the user doesn't have to second guess how,
say, ``RLIMIT_NPROC`` has been renamed and partly because, in many
cases, you can just cut'n'paste from the man page for the :lname:`C`
function.

Style
=====

I say I'm not a fan of imposing style on other people but, being human
and all, I do get annoyed when someone else's code is formatted
dramatically differently to mine.  I wouldn't say I find it
*unreadable* but I have been known to re-indent code to understand it.
*Ludicrous!*

However, some aspects of style represent completeness or thoroughness.
*Dot the i's and cross the t's.*

Any condition statement should cover all possibilities... including
the "impossible".

In other words, every ``if`` should cover the "else" clause and
:lname:`C`'s ``switch`` should have a ``default`` clause.  Or document
why they don't.

:lname:`C` Indentation Style
----------------------------

My *own* style varies dependent on how enthusiastic I have been about
probing the depths of ``cc-mode.el`` although these days I tend to
find a local minima between laziness, annoyance and satisfaction.  My
:file:`.emacs` has been reduced to setting ``k&r`` mode (whatever
*that* involves) and making the ``c-basic-offset`` to be 4.

Although I'm still slightly annoyed.

``{``
^^^^^

I've noted elsewhere that, other than functions, I usually have any
``{`` on the end of the line of the statement that introduces it:

.. code-block:: c

   if (...) {
       ...
   }

if
^^

``if`` statements *always* use braces -- even if it is simply
``return`` or ``break``.

That harks back to my debugging needs where *inevitably* you need to
identify which of several clauses caused the return so you need to
slip in a ``printf`` statement or some other debug.  I put the
infrastructure in first:

.. code-block:: c

   if (...) {
       /* potential debug with r */
       return r;
   }

switch
^^^^^^

A ``switch`` statement should *always* have a ``default`` clause with
some suitable admonition.  This catches developer coding errors which
will get fixed and the ``default`` clause can go back to wasting space
until the next developer comes along.

A rare exception is something like the printing of :lname:`C` types in
:file:`util.c` where there the outer switch allows :lname:`C` types
into the clause but non inside as the clause is already guarded.

That said, I've managed to fall foul in forgetting to include one of
the :lname:`C` types further in...  So, maybe a ``default`` clause
everywhere?

case
""""

I don't like a ``case`` statement without a ``break`` or a ``return``
-- any "fall-through" code should be visually distinct.

.. code-block:: c

   switch {
   case IDIO_A:
   case IDIO_B:
       ...
       break;

       
   case IDIO_K:
   case IDIO_L:
       ...
       return;

       
   default:
       fprintf (stderr, ...);
       break;
   }

I think it would be beneficial, in general, if all possible ``case``
alternatives are explicitly listed and in the order they are defined
in.

I fairly often have to introduce some lexical parameters on a
per-``case`` basis which also breaks my ``{`` on the end of the line
rule.  Which leads to the following:

.. code-block:: c

   switch {
   case IDIO_A:
       {
           ...
       }
       break;
   default:
       fprintf (stderr, ...);
       break;
   }

structs
^^^^^^^

There's only really one place where it is required but I have tried to
consistently use ``_s`` for struct tag names and ``_t`` for typedef'ed
names resulting in:

.. code-block:: c

   typedef struct idio_foo_s {
       size_t size;
   } idio_foo_t;

(The place it is required is defining compound types which need to
refer to the "Idio" type, ``struct idio_s *``, before it has been
typedef'd.)

Accessors
"""""""""

I have generally created macros to access the elements of the
structures:

.. code-block:: c

   #define IDIO_FOO_SIZE(f)	((f) ... .size)

As I repeatedly change my mind about the contents of ``struct
idio_foo_s`` and whether it is encompassed by or allocated in a wider
data structure and therefore whether the accessor is ``.size`` or
``->size``.

There should be very limited references to the elements of structures
elsewhere in the code.

return
^^^^^^

.. sidebox:: Not a promising admission, I know.

I discovered that I'm not very good at getting things right, either
the first time or several subsequent times.  Consequently almost all
of my return clauses look something like:

.. code-block:: c

   IDIO r = idio_stuff ();
   /* option to print debug with r */
   return r;

I rely on the :lname:`C` compiler being able to optimise ``r`` away.

Non-local returns
^^^^^^^^^^^^^^^^^

The :lname:`C` code will be invoking :manpage:`siglongjmp(3)` but not
everyone washing over the code will be able to spot that so
*especially* where the code will never reach we need to clarify that.

There is a special ``idio_S_notreached`` sentinel value otherwise a
similar comment and a :lname:`C` sentinel value should be returned
(unless the function is ``void``, of course).

.. code-block:: c

   if (...) {
       idio_error_printf (...);

       return idio_S_notreached;
   }

or

.. code-block:: c

   if (...) {
       idio_error_printf (...);

       /* notreached */
       return -1;
   }



:lname:`C` Comparison Style
---------------------------

I have taken to making the left-hand-side of a comparison whichever
value is a *constant* -- the goal to avoid accidental assignments:

.. code-block:: c

   if (IDIO_TYPE_VALUE == s[i]) {

and I think it's probably saved me a couple of times from the ignominy
of:

.. code-block:: c

   if (s[i] = IDIO_TYPE_VALUE) {

It does require a bit of mental effort and it doesn't scan as well: I
always have the sense of comparing something that I've just calculated
to something else which gives the :samp:`{variable} == {constant}`
thought process but is, of course, one character away from
embarrassment.

For some comparisons, notably function calls, I revert to "normal":

.. code-block:: c

   if (system_call (args) == -1) {

:lname:`Idio` Style
-------------------

I've written a putative ``idio-mode.el`` (in :file:`.../utils`) which
broadly does the right thing.

The most prominent feature about being right is that the basic indent
is two spaces.

From what, is another question.

Two spaces, rather than four, because of the
:lname:`Idio`/:lname:`Scheme` nature of more frequent use of
sub-clauses wrapped by parentheses or braces.

Error Messages
==============

Error messages should try to encode some context about the error.
Hopefully, the error-raising code will provide some lexical
information -- and there are a couple of :lname:`C` macros to help
developers -- but the actual message itself may require some
indication of the issue with a particular parameter.

Code Coverage
=============

.. sidebox:: Swahili for: slowly, gently, be calm, ... 

*pole pole*

I'm working through the :lname:`C` code looking at adding two classes
of "tests".

#. we want to be able to provoke each and every error generating
   clause.

   These are generally the ``test-X-errors`` tests.

#. we want to provoke complete code coverage

   These are generally the ``test-X-coverage`` tests.

   "Complete" is impossible as :program:`gcov` always marks the
   closing ``}`` of a function as "not run" because of the ``return``
   statement on the previous line.

These test should be identified in the :lname:`C` code base together
with any explanatory text.

For example, some errors are impossible to generate without breaking
the calling code as they fall in the ``default`` clause of a
``switch`` statement and are in the "impossible" category.  It should
be documented as "impossible" but the error raising code should
remain.  A developer *will* fall into it.

.. include:: ../commit.rst

