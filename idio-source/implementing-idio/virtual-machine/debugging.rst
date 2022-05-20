.. include:: ../../global.rst

*********
Debugging
*********

.. aside::

   Often, shortly after that, it's a decision to regret.

From time to time it's useful to know what the VM is up to.  Short of
going full-on :lname:`C` debugging with :program:`gdb` we can get some
static and dynamic views, some disassembly and some performance data.

State
=====

What values are being held by the VM?

.. _`idio-thread-state`:

idio-thread-state
-----------------

:ref:`idio-thread-state <ref:idio-thread-state>` dumps out all there
is to know about the current VM *thread*.

Broadly:

* the thread's registers

* a decoded stack

* a tree of frames

* (in debug builds) a view of the frame linkages

* a list of trap handlers (should be visible in the stack listing)

* a list of default condition handlers (if any)

* a list of dynamic variables (if any)

* a list of dynamically allocated environment variables (if any)

  This will not include top-level environment variables.

* a list of ABORTs (should be visible in the stack listing)

* the exit handler

For example, defining a function which calls ``idio-thread-state``
mid-processing and then calling that function:

.. code-block:: idio-console

   Idio> define (foo x y) {
     z := x + 1
     (idio-thread-state)
     z
   }
   #<CLOS foo @165575/0x2/Idio>
   Idio> foo 99 "red balloons"
   vm-debug: vm-thread-state THR 0x7f9fcf416d10
       src="*stdin*:line 3"
	pc=165609
       val=100
      reg1=99
      reg2=#<unspec>
      expr=(idio-thread-state)   "*stdin*:line 3"
      func=#<PRIM idio-thread-state>
       env=#<MOD Idio>
     frame=#<FRAME 0x7f9fcda3ac90 n=2/4 [ 99 "red balloons" #n 100 5318]>
	in=#<H ofr!iF   0:"*stdin*":7:76>
       out=#<H ofw!iF   1:"*stdout*":2:29>
       err=#<H ofw!iF   2:"*stderr*":1:28>
       mod=#<MOD Idio>
     holes=#n
   jmp_buf=0x7f9fcf415040

   vm-decode-thread: thr=0x7f9fcf416d10 sp=  37 pc=165609
   vm-decode-stack: stk=0x7f9fcf416d90 sp=  37
     37    RETURN               165645 
     35    STATE                #n #<MOD Idio> 
     32    ABORT                "ABORT to toplevel (PC 165647)"     next abort @26
     29    RETURN               1 -- FINISH
     27    a handle             #<H ofr!iF   0:"*stdin*":7:76>
     26    ABORT                "ABORT to main => exit (probably badly)" next abort @-1
     23    TRAP                 #<PRIM default-SIGCHLD-handler>     ^rt-signal-SIGCHLD   next t/h @19
     19    TRAP                 #<PRIM default-racse-handler>       ^rt-async-command-status-error next t/h @15
     15    TRAP                 #<PRIM default-rcse-handler>        ^rt-command-status-error next t/h @11
     11    TRAP                 #<PRIM default-condition-handler>   ^condition           next t/h @7
      7    TRAP                 #<PRIM restart-condition-handler>   ^condition           next t/h @3
      3    TRAP                 #<PRIM reset-condition-handler>     ^condition           next t/h @3

     fr  #                   var   val
      0  0p                    x = 99
      0  1p                    y = "red balloons"
      0  2*                    - = #n
      0  3l                    z = 100

	 #p is a parameter
	 #* is the varargs arg - is the name (if no name given)
	 #l is a local var

   vm-thread-state: frame: 0x7f9fcda3ac90 (       0x2)  2/ 4  5318 - (x y #f z)           - (99 "red balloons")

   vm-thread-state: trap: SP  23:  #<PRIM default-SIGCHLD-handler>               ^rt-signal-SIGCHLD
   vm-thread-state: trap: SP  19:  #<PRIM default-racse-handler>                 ^rt-async-command-status-error
   vm-thread-state: trap: SP  15:  #<PRIM default-rcse-handler>                  ^rt-command-status-error
   vm-thread-state: trap: SP  11:  #<PRIM default-condition-handler>             ^condition
   vm-thread-state: trap: SP   7:  #<PRIM restart-condition-handler>             ^condition
   vm-thread-state: trap: SP   3:  #<PRIM reset-condition-handler>               ^condition

   vm-thread-state: abort: SP  32 = (#<K 0x7f9fcda3f390 ss=30 PC=165647> "ABORT to toplevel (PC 165647)")
   vm-thread-state: abort: SP  26 = (#<K 0x7f9fcf1cfd10 ss=24 PC=2> "ABORT to main => exit (probably badly)")

   vm-thread-state: idio_k_exit #<K 0x7f9fcf1cfd10 ss=24 PC=2>
   100

Amongst other things, we can see how ``z`` appears as a fourth "local"
parameter to ``foo``.  The ``100`` at the end is the value returned
from the function call (ie. ``z``) being printed out.

%vm-frame-tree
--------------

:ref:`%vm-frame-tree <ref:%vm-frame-tree>` is just the frame tree from
:ref:`idio-thread-state <idio-thread-state>`, above.

%vm-trap-state
--------------

:ref:`%vm-trap-state <ref:%vm-trap-state>` is just the trap listing
from :ref:`idio-thread-state <idio-thread-state>`, above.

Dynamic Views
=============

%%vm-trace
----------

:samp:`%%vm-trace {depth} [file [mode]]` shows the VM in action.  You
may find the VM doing more processing than you expect -- hence the
ability to write to a :file:`file`.

Using a simple function we can follow the VM up to, say, 5 levels
deep:

.. code-block:: idio-console

   Idio> define (op f l) {
   f l
   }
   #<CLOS op @165614/0x2/Idio>
   Idio> %%vm-trace 5
   #<unspec>
   Idio> op ph '(1 2 3)
   000000000  29240  165688 "*stdin*:line 5"                        >  (op f l) was called as
								       (op #<PRIM ph> (1 2 3))
   000058834  29240  165630 "*stdin*:line 2"                        >>  (ph p) was tail-called as
									(#<PRIM ph> (1 2 3))
   000047852  29240  165631                                         <<  1
   000012963  29240  165689                                         <  1
   1

The columns are:

* a nanosecond time delta

* PID

* *PC*

* source location

* trace depth: calling or returning

* call or value being returned

We can be more circumspect and only go 1 level deep:

.. code-block:: idio-console

   Idio> %%vm-trace 1
   #<unspec>
   Idio> op ph '(1 2 3)
   594986698  29240  165738 "*stdin*:line 7"                        >  (op f l) was called as
								       (op #<PRIM ph> (1 2 3))
   1

Disassembly
===========

There is a useful disassembler.  You might ordinarily see it in action
via the ``--vm-reports`` flag to :program:`idio` which dumps the
entire byte code to :file:`vm-dasm`.

You can run :ref:`%%idio-dasm <ref:%%idio-dasm>` for individual
functions:

.. code-block:: idio-console

   Idio> define (foo x) {
   y := x + 1
   y
   }
   #<CLOS foo @165615/0x2/Idio>
   Idio> %%idio-dasm foo
   idio_vm_dasm: thr 0x7f39e1274a10 pc0 165615 pce 165643
			165615 131: ARITY=2?
			165616 120: LINK-FRAME sci=1455 (x #f)
			165619   1: SHALLOW-ARGUMENT-REF 0
			165620  80: PUSH-VALUE
			165621 143: CONSTANT       1
			165622  82: POP-REG1
			165623  84: SRC-EXPR 11262 "*stdin*":line 2
     (binary-+ x 1)
			165627 163: PRIMITIVE/2 1058 binary-+
			165630  84: SRC-EXPR 11263 "*stdin*":line 2
     (function+ y (binary-+ x 1) (begin y))
			165634 124: EXTEND-FRAME 3 sci=5319 (x #f y)
			165639  14: SHALLOW-ARGUMENT-SET 2
			165641   3: SHALLOW-ARGUMENT-REF 2
			165642  93: RETURN
   #<unspec>

Here the output has:

* the *PC*

* the opcode number

* the opcode name and decoding of any arguments

  For example:

  * 165616 ``LINK-FRAME`` is associated with the signature string ``(x
    #f)`` -- where the ``#f`` indicates the was no varargs name

  * 165630 ``EXTEND-FRAME`` (to 3) is associated with the signature
    string ``(x #f y)`` for the additional "local" parameter ``y``

SRC-EXPR
--------

``SRC-EXPR``\ s only occur for function calls.  The ``#t`` in ``(if #t
...)`` will not generate a ``SRC-EXPR`` whereas the call to the ``gt``
primitive in ``(if (x gt 0) ...)`` will.

Note, though, the ``SRC-EXPR`` occurs *after* the code for calculating
any arguments, that is, immediately before the function call.

.. code-block:: idio-console

   Idio> define (foo x) {
   (x + 1) / (x - 1)
   }
   #<CLOS foo @159805/0x2/Idio>
   Idio> %%idio-dasm foo
   idio_vm_dasm: thr 0x7f23c0d9ca10 pc0 159805 pce 159841
			159805 131: ARITY=2?
			159806 120: LINK-FRAME sci=1455 (x #f)
			159809   1: SHALLOW-ARGUMENT-REF 0
			159810  80: PUSH-VALUE
			159811 143: CONSTANT       1
			159812  82: POP-REG1
			159813  84: SRC-EXPR 9819 "*stdin*":line 2
     (binary-+ x 1)
			159817 163: PRIMITIVE/2 1058 binary-+
			159820  80: PUSH-VALUE
			159821   1: SHALLOW-ARGUMENT-REF 0
			159822  80: PUSH-VALUE
			159823 143: CONSTANT       1
			159824  82: POP-REG1
			159825  84: SRC-EXPR 9820 "*stdin*":line 2
     (binary-- x 1)
			159829 163: PRIMITIVE/2 1059 binary--
			159832  82: POP-REG1
			159833  84: SRC-EXPR 9821 "*stdin*":line 2
     (binary-/ (binary-+ x 1) (binary-- x 1))
			159837 163: PRIMITIVE/2 1061 binary-/
			159840  93: RETURN

   #<unspec>

Performance Data
================

If you run :program:`idio` with ``--vm-reports`` you'll get series of
report files from the VM.

.. code-block:: sh

   .local/bin/idio --vm-reports test

vm-dasm
-------

As described above, a disassembly of the entire byte code.

vm-constants
------------

A dump of the VM's constants table.  References to "constant indexes"
(often abbreviated to ``ci`` or ``mci`` or ``gci`` etc.) should be
found in this table.

vm-values
---------

A dump of the VM's values table.  References to "value indexes" (often
abbreviated to ``vi`` or ``mvi`` or ``gvi`` etc.) should be found in
this table.

vm-modules
----------

A slightly complicated dump of the relationship between the existence
of symbols in modules, whether they are exported and the VM's value
index they map to.  Remember that the symbol ``x`` in my module will
not likely be bound to the same value as the symbol ``x`` in your
module.

vm-src-constants
----------------

This data ought to be in the regular :file:`vm-constants` table but,
by and large, it dwarfs the former.  Part of the reason for this is
that each parenthesised expression becomes tagged with "source
properties" in order that it can be accurately identified later.

In addition, template expansion causes a large increase in the number
of expressions, each of which need to be mapped back to a source
expression in case of error.

The source properties aren't used often -- generally only for an error
or when writing this report -- and so we try to avoid making the VM's
constants table unnecessarily large and worsening memory caching by
using a separate table.

Note that the ``SRC-EXPR`` opcodes are only passing around indexes
into this table.  The expensive lookup and dereferencing is only done
on demand.

gc-stats
--------

Garbage collector stats.

vm-perf.log
-----------

.. note::

   Only for debug builds.

Here, there are timing wrappers around instructions and function
calls.  Take the numbers with a pinch of salt.

.. aside::

   Plus plenty extra from somewhere.

Some mis-attribution occurs, notably with ``load`` which will
accumulate all the time it takes to run the content of the files
loaded.

During execution a periodic report on the number of opcodes per
millisecond is reported but only if certain conditions have been met
(running for long enough, executed enough instructions).  You might
not see anything for short runs.

On shutdown we get:

* a table for the opcodes with per opcode statistics

* as the Garbage Collector frees objects, in this case functions, both
  closures and primitives, we'll get their statistics which means that
  there's no fixed order to the output

  For closures we'll get:

  * *PC*

  * call count

  * name

  * total elapsed call time in seconds.nanoseconds

  * per call elapsed time in nanoseconds

  * scaled per call elapsed time (in ns, us, ms as appropriate)

  * total resource usage time in seconds.microseconds

  For primitives we'll get the same set except *PC* is replaced by the
  primitives :lname:`C` function pointer.

* Some ``IDIO_MALLOC`` bucket stats

.. include:: ../../commit.rst

