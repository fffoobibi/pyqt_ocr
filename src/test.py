import threading
import time

# class Single(object):

#     _lock = threading.Lock()

#     def __new__(cls, *args, **kwargs):
#         with cls._lock:
#             if not hasattr(cls, '_instance'):
#                 cls._instance = object.__new__(cls)
#                 cls._instance.__inited__ = False
#                 setattr(cls, '__init__', cls.singleinit(cls.__init__))
#         return cls._instance
    
#     @classmethod
#     def singleinit(cls, func):
#         def inner(*args,**kwargs):
#             with cls._lock:
#                 if getattr(cls._instance, '__inited__') == False:
#                     func(*args, **kwargs)
#                     setattr(cls._instance, '__inited__', True)
#         return inner

#     def __init__(self, name):
#         print(1111)
#         self.name = name

from supports import Account, User

def target(i):
    time.sleep(5)
    o = Account()
    print(id(o))

for i in range(4):
    t = threading.Thread(target=target, args=(i, ))
    t.start()

User.happy()


