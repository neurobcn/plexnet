#!/usr/bin/env python
"""
fieldtree.py - Field Tree Object
Author: Sean B. Palmer, inamidst.com

The FieldTree object is a kind of OrderedDict. The name Field refers
to a key and value pair, or what is usually called an item in Python.

There are two main extra features that a FieldTree provides over an
OrderedDict. The first is that when a field is set, it returns a
Label object. This provides a kind of permanent link to the field.
The second is that there are methods that allow for the access of any
FieldTree objects nested inside a FieldTree.

New FieldTree objects can be constructed without arguments:

   >>> person = FieldTree()

You can add fields and keep the resulting labels:

   >>> a = person.add('gender', 'male')
   >>> b = person.add('name', 'John Smith')
   >>> c = person.add('website', 'example.com')

Or you can add fields and discard the labels:

   >>> person['phone'] = '123-456-7890'
   >>> person['email'] = 'john@example.com'

You can then access fields by label or by key:

   >>> person[b]
   'John Smith'
   >>> person['website']
   'example.com'

The useful thing about labels is that you can use them to access
fields that you might then want to modify, and they'll be available
after those modifications. So if we make a template from a FieldTree:

   >>> def format(person): 
   ...    args = person[b], person[a], person[c]
   ...    return 'Name: %s, Sex: %s, Website: %s' % args

This works in the expected way:

   >>> format(person)
   'Name: John Smith, Sex: male, Website: example.com'

But then even if you start adding and modifying values:

   >>> f = person.before(c, 'company', 'Acme Ltd.')
   >>> person.changekey(a, 'sex')

So that the data has a different key and a new order:

   >>> for field in person.fields(): 
   ...    print field
   ... 
   ('sex', 'male')
   ('name', 'John Smith')
   ('company', 'Acme Ltd.')
   ('website', 'example.com')
   ('phone', '123-456-7890')
   ('email', 'john@example.com')

The template still works!

   >>> format(person)
   'Name: John Smith, Sex: male, Website: example.com'

Now, let's say we want to use a FieldTree structure for the name so
that we can store the forename and surname separately. We'll make
this FieldTree by passing some field arguments:

   >>> name = FieldTree(('forename', 'John'), ('surname', 'Smith'))

And then we can query the new object for its labels:

   >>> g = name.get_label('forename')
   >>> h = name.get_label('surname')

We can then change the existing value of the 'name' key:

   >>> person['name'] = name

And because this is a field tree, we can use the labels we got from
the nested FieldTree to access its values from the parent tree:

   >>> person[g]
   'John'
   >>> person['name'][h]
   'Smith'

But of course, we can't use keys to access nested values:

   >>> person['forename']
   Traceback (most recent call last):
      ...
   KeyError: "no 'forename' key"

Using keys in the regular way does work, though:

   >>> person['name']['forename']
   'John'

Printing out all the fields iterates also over the nested fields, but
it skips any FieldTree values themselves:

   >>> for field in person: 
   ...    print field
   ... 
   ('sex', 'male')
   ('forename', 'John')
   ('surname', 'Smith')
   ('company', 'Acme Ltd.')
   ('website', 'example.com')
   ('phone', '123-456-7890')
   ('email', 'john@example.com')

With FieldTree objects there is a general principle that you can use
keys only on the current FieldTree object, but you can use labels in
a nested way. So for example, you can check whether a FieldTree or
any of its nested FieldTree objects contains a label:

   >>> a in person # gender/sex
   True
   >>> g in person # forename
   True

But you can only check for keys in a non-nested way:

   >>> 'sex' in person
   True
   >>> 'name' in person
   True
   >>> 'forename' in person
   False

You can iterate over all kinds of combinations of fields, keys,
labels, and values using the iteration methods:

   >>> import itertools
   >>> def show(iter, num): 
   ...    return list(itertools.islice(iter, num))

To, for example, note that labels are a subclass of int:

   >>> show(person.labels(), 3)
   [Label(1), Label(2), Label(6)]

And that keys (but not labels) referring to FieldTree object values
are skipped, so that the following doesn't have 'name':

   >>> show(person.tree_keys(), 3)
   ['sex', 'forename', 'surname']

Another feature of FieldTree objects is that you can set values that
don't have any keys. This means that you can only refer to this value
using its label:

   >>> i = person.add('John Smith plays the trumpet')
   >>> person[i]
   'John Smith plays the trumpet'
   >>> person.get_field(i)
   (Empty(), 'John Smith plays the trumpet')

You can also delete values. You can't remove a whole field entirely,
but delete replaces the current value with an Empty() object:

   >>> del person['phone']
   >>> person['phone']
   Empty()

You can remove a field entirely, but it's not really recommended:

   >>> example = FieldTree(('a', 'b'), ('p', 'q'))
   >>> first = example.get_label('a')
   >>> example.remove(first)
   >>> len(example)
   1
   >>> example['a']
   Traceback (most recent call last):
      ...
   KeyError: "no 'a' key"

There are some other convenience functions for looking up various
kinds of fields, labels, keys, and values:

   >>> person.get_field(g)
   ('forename', 'John')
   >>> person.get_key(g)
   'forename'
   >>> person.get_value(g)
   'John'

"""

import itertools

class Label(int): 
   __counter = itertools.count(1)

   def __repr__(self): 
      return 'Label(%s)' % int(self)

   @staticmethod
   def next(): 
      num = Label.__counter.next()
      return Label(num)

class Empty(object): 
   def __repr__(self): 
      return 'Empty()'

class FieldTree(object): 
   def __init__(self, *args): 
      self.__fields = {} # {label: (key, value)}
      self.__values = {} # {key: (label, value)}
      self.__order = [] # [labels]
      self.__trees = set() # [field-tree-values]

      for key, value in args: 
         self[key] = value

   def __repr__(self): 
      return 'FieldTree%s' % (tuple(self.fields()),)

   def __len__(self): 
      return len(self.__order)

   def __contains__(self, obj): 
      if isinstance(obj, Label): 
         return self.has_tree_label(obj)
      else: return self.has_key(obj)

   def has_label(self, label): 
      return self.__fields.has_key(label)

   def has_tree_label(self, label): 
      for tree in [self] + list(self.__trees): 
         if tree.has_label(label): 
            return True
      return False

   def has_key(self, key): 
      return self.__values.has_key(key)

   def __iter__(self): 
      return self.tree_fields()

   def fields(self): 
      for label in self.__order: 
         yield self.__fields[label]

   def tree_fields(self): 
      for label in self.__order: 
         key, value = self.__fields[label]

         if isinstance(value, FieldTree): 
            for field in value.tree_fields(): 
               yield field
         else: yield key, value

   def labels(self): 
      for label in self.__order: 
         yield label

   def tree_labels(self): 
      for label in self.__order: 
         key, value = self.__fields[label]

         if isinstance(value, FieldTree): 
            for vlabel in value.tree_labels(): 
               yield vlabel
            else: yield label

   def keys(self): 
      for key, value in self.fields(): 
         yield key

   def tree_keys(self): 
      for key, value in self.tree_fields(): 
         yield key

   def values(self): 
      for key, value in self.fields(): 
         yield value

   def tree_values(self): 
      for key, value in self.tree_fields(): 
         yield value

   def __getitem__(self, item): 
      return self.get_value(item)

   def get_field(self, label): 
      "label -> field (deep)"
      assert isinstance(label, Label)
      if self.has_label(label): 
         return self.__fields[label]
      for tree in self.__trees: 
         try: return tree.get_field(label)
         except KeyError: continue
      raise KeyError("no %r label" % label)

   def get_label(self, key): 
      "key -> label (shallow)"
      if self.has_key(key): 
         return self.__values[key][0]
      else: raise KeyError("no %r key" % key)

   def get_key(self, label): 
      "label -> key (deep)"
      return self.get_field(label)[0]

   def get_value(self, obj): 
      "label -> value (deep) or key -> value (shallow)"
      if isinstance(obj, Label): 
         return self.get_label_value(obj)
      else: return self.get_key_value(obj)

   def get_label_value(self, label): 
      "label -> value (deep)"
      return self.get_field(label)[1]

   def get_key_value(self, key): 
      "key -> value (shallow)"
      if self.has_key(key): 
         return self.__values[key][1]
      else: raise KeyError("no %r key" % key)

   def __setitem__(self, obj, value): 
      if not (obj in self): 
         self.add(obj, value)
      else: self.changevalue(obj, value)

   def __arguments(self, args): 
      if len(args) == 1: 
         args = Empty(), args[0]
      elif len(args) != 2: 
         raise ValueError("Expected one or two args")

      if any(isinstance(arg, Label) for arg in args): 
         raise ValueError("FieldTrees can't contain Labels")
      return args

   def __set(self, args): 
      key, value = self.__arguments(args)

      if self.has_key(key): 
         label, oldvalue = self.__values[key]
         if isinstance(oldvalue, FieldTree): 
            self.__trees.remove(oldvalue)
      else: label = Label.next()

      self.__fields[label] = (key, value)
      if not isinstance(key, Empty): 
         self.__values[key] = (label, value)
      self.changed(label)
      return label

   def add(self, *args): 
      label = self.__set(args)
      self.__order.append(label)
      return label

   def update(self, args): 
      for key, value in args: 
         self[key] = value

   def before(self, next, *args): 
      if not self.has_label(next): 
         raise KeyError("no %r label" % next)
      label = self.__set(args)

      index = self.__order.index(next)
      self.__order.insert(index, label)
      return label

   def __delitem__(self, obj): 
      self.delete(obj)

   def delete(self, obj): 
      self.changevalue(obj, Empty())

   def remove(self, label): 
      assert isinstance(label, Label)
      key, value = self.get_field(label)
      del self.__fields[label]
      del self.__values[key]
      self.__order.remove(label)
      if isinstance(value, FieldTree): 
         self.__trees.remove(value)
      self.changed(label)

   def changekey(self, label, key): 
      if not self.has_label(label): 
         raise KeyError("no %r label" % label)
      oldkey, value = self.__fields[label]

      self.__fields[label] = (key, value)
      self.__values[key] = (label, value)
      self.changed(label)

   def changevalue(self, obj, value): 
      if isinstance(obj, Label) and self.has_label(obj): 
         label, (key, oldvalue) = obj, self.__fields[obj]
      elif self.has_key(obj): 
         key, (label, oldvalue) = obj, self.__values[obj]
      else: raise KeyError("%r" % obj)

      self.__fields[label] = (key, value)
      self.__values[key] = (label, value)

      if isinstance(oldvalue, FieldTree): 
         self.__trees.remove(oldvalue)
      if isinstance(value, FieldTree): 
         self.__trees.add(value)
      self.changed(label)

   def changefield(self, label, key, value): 
      self.changekey(label, key)
      self.changevalue(label, value)
      self.changed(label)

   def changed(self, *labels): 
      pass

def test(): 
   import doctest
   Documentation = type('Documentation', (object,), {'__doc__': __doc__})
   doctest.run_docstring_examples(Documentation, globals(), verbose=True)

def summary(): 
   import sys, StringIO
   stdout = sys.stdout
   sys.stdout = StringIO.StringIO()
   test()
   buffer = sys.stdout
   sys.stdout = stdout

   buffer.seek(0)
   success, failure = 0, 0
   for line in buffer: 
      if line.startswith('ok'): 
         success += 1
      elif line.startswith('Fail'): 
         failure += 1
   print "%s/%s Tests Passed" % (success, success + failure)

def main(): 
   summary()

if __name__ == '__main__': 
   main()
