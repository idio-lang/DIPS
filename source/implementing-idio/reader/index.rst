.. include:: ../../global.rst

**********
The Reader
**********

The reader's role is to consume the textual source code and construct
an internal representation of the source code such that the evaluator
can interpret its meaning.

The read can create :lname:`Idio` values from the various constructors
(integers and strings, say, as we normally think of them in textual
form: 12 and "twelve") and it has a few limited rights to alter the
form of the constructed representation.

In :lname:`Idio` you can define and add your own *operators* to the
set of representation-altering features.

.. toctree::
   :maxdepth: 2

   reading

.. include:: ../../commit.rst

