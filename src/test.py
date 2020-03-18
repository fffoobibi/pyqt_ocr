class A():

    TE = 20

    __slots__ = 'name', 'ls'

    def __init__(self):
        self.name = 'fqk'
        self.ls = self.TE

a=A()
print(a.ls)
a.ls = 30
print(a.ls, A.TE)
        