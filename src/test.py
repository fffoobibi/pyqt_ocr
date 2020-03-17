import inspect
from types import MethodType
from functools import wraps
import threading


class MetaThreadSafe(type):
    def __new__(cls, class_name, class_base, class_dict):
        class_ = type.__new__(cls, class_name, class_base, class_dict)
        class_._lock = threading.Lock()
        for key in class_dict:
            if inspect.isfunction(class_dict[key]):
                if key != '__init__':
                    method = cls.thread_safe(class_, class_dict[key])
                    setattr(class_, key, method)
        return class_

    def thread_safe(self, func):
        def inner(*args, **kwargs):
            with self._lock:
                print(1111)
                res = func(*args, **kwargs)
                print(2222)
                return res
        return inner

class singlet():

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not hasattr(cls, '_instance'):
                cls._instance = object.__new__(cls)
                cls.__inited__ = False
                cls.__init__ = cls.first_init(cls.__init__)
            return cls._instance
    
    @classmethod
    def first_init(cls, func):
        def inner(*args, **kwargs):
            with cls._lock:
                if cls.__inited__ == False:
                    func(*args, **kwargs)
                    cls.__inited__ = True
        return inner

class A(singlet, metaclass=MetaThreadSafe):

    def __init__(self):
        print('inita')

    def hello(self):
        print('hello')

a = A()
b = A()
a.hello()
b.hello()
print(id(a), id(b))