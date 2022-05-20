.. include:: ../../global.rst

*******************
The Virtual Machine
*******************

:lname:`Idio` is implemented through a stack-based register-based
virtual machine that uses abstracted opcodes suited to the high level
nature of the language.  We're not quite at the level of ``MOV``,
``JMP`` and ``RET`` from a real-world hardware computer's assembly
language but the transformation from :lname:`Idio`'s high-level forms
may feel like it.

The :lname:`Idio` virtual machine is of our own invention (by which I
mean it is clearly and obviously derived from :ref-title:`LiSP`
:cite:`LiSP`).  It is **not** targeting the JVM_ or any other
pre-existing virtual machine.  If we did then I'm not sure we'd learn
anything about virtual machines and it creates another dependency when
installing :lname:`Idio` on a clean machine.

So long as we can totter along well enough, I think we're good to go.
We can *always* want to go faster and more efficiently.  There will
always be some who actively want to target some other virtual machine
or even have the whole engine translated into :lname:`C`, say, and
compiled directly.

If you follow through :ref-title:`LiSP` there are two clear and
dramatic steps forward:

#. we stop looking variables up

#. we transform the high-level language for byte compilation

Clearly the second is at hand.  The first is, arguably, more dramatic.

.. toctree::
   :maxdepth: 2

   lookups
   register-machine
   debugging

.. include:: ../../commit.rst

