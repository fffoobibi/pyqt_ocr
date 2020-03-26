from enum import Enum
import json
import inspect


from typing import *
from configparser import ConfigParser
from os.path import exists, join, expanduser, isfile, abspath
from aip import AipOcr
from copy import deepcopy
from functools import wraps
from PyQt5.QtCore import QMutex, QObject, Qt

Size = Tuple[int, int]
Zoom = Tuple[float, float]
RectCoord = List[int]  # [x1,y1,x2,y2]
RectCoords = List[RectCoord]  # [[x1,y1,x2,y2], [x2,y3,x4,y4], ...]
Region = 'x1,y1,x2,y2;...'

__all__ = [
    'DEFAULT_CONFIG', 'Config', 'Account', 'User', 'Size', 'Rotates', 'with_error',
    'Zoom', 'RectCoord', 'RectCoords', 'Region', 'slot', 'home', 'Single', 'NoReturn'
]

home = abspath(expanduser('~\\Desktop')) if exists(
    abspath(expanduser('~\\Desktop'))) else abspath(expanduser('~'))


def slot(signal='', sender='', desc=''):
    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            res = func(*args, **kwargs)
            return res

        return inner

    return outer


def with_error(func):
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
            return res
        except Exception as e:
            print(e)
    return inner


DEFAULT_CFGS = {
    'recognition': {
        'delay': 2,
        'number': -1,
        'type': 0,
    },
    'out': {
        'format': 'txt',
        'directory': home,
        'title': 'none'
    },
    'advanced': {
        'region': 'none',
        'text1': 'none',
        'clean': False
    },
    'parseinfo': {
        'workpath': '',
        'basic': 0,
        'handwriting': 0,
        'accurate': 0,
    }
}

__personal_config = deepcopy(DEFAULT_CFGS)

ACCOUNT_SETTINGS = {
    'user1': {
        'id': '',
        'key': '',
        'secret': '',
        'platform': 'b',
        'alias': 'user1',
        'legal': False,
        'config': __personal_config
    },
    'info': {
        'active': 'user1',
        'date': '',
        'hide': False,
        'basic': 0,
        'hand': 0,
        'accurate': 0,
    },
}


class RotateError(Exception):
    ...


class Rotates(Enum):
    ZERO_CLOCK = 0
    TRE_CLOCK = 1
    SIX_CLOCK = 2
    NIE_CLOCK = 3

    @classmethod
    def convert(cls, angle: int):
        if angle % 90 > 0:
            raise RotateError('Must be an integer multiple of 90')
        if (angle / 90 % 4 == 0) or (angle / 90 % 4 == 2):
            return cls.ZERO_CLOCK
        elif (angle / 90 % 4 == 1) or (angle / 90 % 4 == 3):
            return cls.TRE_CLOCK


class Config(object):
    @classmethod
    def fromDict(self, dic):
        return Config(from_dict=dic)

    def __init__(self, from_file=True, *, from_dict=False):
        cp = ConfigParser()
        if from_dict:
            self.info = from_dict
        else:
            self.__from_dict = False
            self._file_path = abspath(join(expanduser('~'), 'ocr_app.cfg'))
            if not exists(self._file_path):
                dft = DEFAULT_CFGS.copy()
                self.info = dft
                with open(self._file_path, 'w') as file:
                    cp.write(file)
            else:
                dic = {}
                for key, section in cp.items():
                    if key != 'DEFAULT':
                        dic[key] = dict(section)
                self.info = dic

    def to_dict(self) -> dict:
        return self.info

    def update_from_dict(self, dic):
        self.info.update(dic)

    def pop(self, section):
        self.info.pop(section, None)

    def get(self, section: str, key: str, parse=str) -> str:
        return self.info[section][key] if parse is None else parse(
            self.info[section][key])

    def set(self, section, key, v):
        self.info[section][key] = v

    def flush(self) -> bool:
        dic = self.to_dict()
        return self.__save(dic)

    def __save(self, dic) -> bool:
        if not self.__from_dict:
            cp = ConfigParser()
            with open(self._file_path, 'w') as file:
                cp.read_dict(self.info)
                cp.write(file)
            return True
        return False

    def __repr__(self):
        return self.to_dict()


DEFAULT_CONFIG = Config.fromDict(DEFAULT_CFGS)


class Single(object):

    _lock = QMutex()

    def __new__(cls, *args, **kwargs):
        cls._lock.lock()
        if not hasattr(cls, '_instance'):
            cls._instance = object.__new__(cls)
            cls._instance.__inited__ = False
            cls.__init__ = cls.singleinit(cls.__init__)
        cls._lock.unlock()
        return cls._instance

    @classmethod
    def singleinit(cls, func):
        def inner(*args, **kwargs):
            cls._lock.lock()
            if getattr(cls._instance, '__inited__') == False:
                func(*args, **kwargs)
                cls._instance.__inited__ = True
            cls._lock.unlock()

        return inner


class MetaThreadSafe(type):
    def __new__(cls, class_name, class_base, class_dict):
        class_ = type.__new__(cls, class_name, class_base, class_dict)
        # class_._lock = QMutex(QMutex.Recursive)
        for key in class_dict:
            if inspect.isfunction(class_dict[key]):
                if key != '__init__':
                    method = cls.thread_safe(class_, class_dict[key])
                    setattr(class_, key, method)
        return class_

    def thread_safe(self, func):
        def inner(*args, **kwargs):
            try:
                self._lock.lock()
                res = func(*args, **kwargs)
                return res
            finally:
                self._lock.unlock()
        return inner


class Account(Single, metaclass=MetaThreadSafe):

    _lock = QMutex(QMutex.Recursive)

    def __init__(self):
        super().__init__()
        self.file_path = abspath(join(expanduser('~'), 'ocr_user.json'))
        self.reload()

    def reload(self) -> NoReturn:
        if not exists(self.file_path):
            with open(self.file_path, 'w+', encoding='utf8') as file:
                json.dump(ACCOUNT_SETTINGS,
                          file,
                          ensure_ascii=False,
                          indent='  ')
        self.info = json.load(open(self.file_path, 'r', encoding='utf8'))

    def add_user(self, user: 'User') -> NoReturn:
        if user.alias in self.info.keys():
            di = {user.alias: user.to_dict()}
            self.info.update(di)
        else:
            self.info.update({f'{user.alias}': user.to_dict()})

    def users(self) -> List['User']:
        lis = []
        for key, value in self.info.items():
            if key != 'info':
                lis.append(User.fromDict(value))
        return lis

    def alias(self) -> List[str]:
        return [key for key in self.info if key != 'info']

    def active_alias(self) -> str:
        return self.info['info']['active']

    def active_user(self) -> 'User':
        user = User.fromDict(self.info[self.active_alias()])
        return user

    def active_config(self) -> Config:
        user = self.active_user()
        return user.config

    def set_active_user(self, alias):
        self.info['info']['active'] = alias

    def get_user(self, alias) -> 'User':
        user_info = self.info.get(alias, None)
        if user_info is None:
            raise TypeError
        else:
            return User.fromDict(user_info)

    def flush(self) -> NoReturn:
        with open(self.file_path, 'w+', encoding='utf8') as file:
            json.dump(self.info, file, ensure_ascii=False, indent='  ')


class User(Single, metaclass=MetaThreadSafe):

    _lock = QMutex(QMutex.Recursive)
    __users__ = []

    @classmethod
    def fromDict(cls, dic) -> 'User':
        id = dic['id']
        key = dic['key']
        secret = dic['secret']
        platform = dic['platform']
        alias = dic['alias']
        try:
            cls._lock.lock()
            for user in cls.__users__:
                if all([
                        id == user.id, key == user.key, secret == user.key,
                        platform == user.platform, alias == user.alias
                ]):
                    return user
            else:
                legal = dic['legal']
                config = Config.fromDict(dic['config'])
            return User(id, key, secret, alias, platform, legal, config)
        finally:
            cls._lock.unlock()

    def __init__(self,
                 id,
                 key,
                 secret,
                 alias,
                 platform='b',
                 legal=False,
                 config: Config = DEFAULT_CONFIG):
        self.id = id
        self.key = key
        self.secret = secret
        self.alias = alias
        self.platform = platform
        self.config = config
        self.__legal = legal
        self.__users__.append(self)

    @property
    def legal(self) -> bool:
        if self.platform == 'b':
            if self.__legal == False:
                from aip import AipOcr
                img = open('./sources/checkUser.png').read()
                client = AipOcr(self.id, self.key, self.secret)
                res = client.basicGeneral(img)
                if res.get('error_code', None) == 14:
                    self.__legal = False
                else:
                    self.__legal = True
            return self.__legal

    def set_config(self, config: Config):
        self.config = config

    def sync(self, account: Account):
        account.add_user(self)

    def to_dict(self) -> Dict:
        config = self.config.to_dict()
        return {
            'id': self.id,
            'key': self.key,
            'secret': self.secret,
            'alias': self.alias,
            'platform': self.platform,
            'legal': self.__legal,
            'config': config
        }

    def __repr__(self):
        return f'User<alias:{self.alias}, ...>'


def mainTest():

    a = Account()
    b = Account()
    c = Account()

    print(id(a), id(b), id(c))

    u = Account().active_user()
    u.config.info['parseinfo']['basic'] += 1
    u.config.info['parseinfo']['basic'] += 1
    print(u.config.info)
    u.sync(Account())
    print('-'*20)
    print(Account().active_user().config.info)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import *
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *

    class Qthread1(QThread):

        def __init__(self, *args, **kwargs):
            user = kwargs.pop('user')
            super().__init__(*args, **kwargs)
            self.user = user

        def run(self):
            print('b1')
            account = Account()
            # u = account.active_user()
            u = self.user
            u.config.info['parseinfo']['basic'] += 1
            print(Account().active_user().config.info)
            print('b1 done\n')

    class Qthread2(QThread):

        def run(self):
            print('b2')

            print(Account().active_user().config.info)
            print('b2 done\n')

    class Widget(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            layout = QHBoxLayout(self)
            self.account = Account()
            self.user = self.account.active_user()
            self.b1 = QPushButton('b1', self)
            self.b2 = QPushButton('b2', self)
            self.b1.setObjectName('b1')
            self.b2.setObjectName('b2')
            self.thread1 = Qthread1(user=self.user)
            self.thread2 = Qthread2()
            layout.addWidget(self.b1)
            layout.addWidget(self.b2)
            QMetaObject.connectSlotsByName(self)

        @pyqtSlot(bool)
        def on_b1_clicked(self, flag):
            self.thread1.start()

        @pyqtSlot()
        def on_b2_clicked(self):
            self.thread2.start()

    app = QApplication(sys.argv)
    win = Widget()
    win.show()
    sys.exit(app.exec_())
