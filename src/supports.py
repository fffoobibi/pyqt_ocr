from typing import *
from configparser import ConfigParser
from os.path import exists, join, expanduser, isfile, abspath
from aip import AipOcr
from copy import deepcopy

import json

__all__ = ['DEFAULT_SETTINGS', 'Config', 'Account', 'User']

home = abspath(expanduser('~\\Desktop')) if exists(
    abspath(expanduser('~\\Desktop'))) else abspath(expanduser('~'))

DEFAULT_SETTINGS = {
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

personal_config = deepcopy(DEFAULT_SETTINGS)

ACCOUNT_SETTINGS = {
    'user1': {
        'id': '',
        'key': '',
        'secret': '',
        'platform': 'b',
        'alias': 'user1', 
        'legal': False, 
        'config': personal_config
    },
    'info': {
        'active': 'user1',
        'number': 1,
        'hide': False,
        'basic': 0,
        'hand': 0,
        'accurate': 0,
    },
}


class Config(object):
    @classmethod
    def fromDict(self, dic):
        return Config(from_dict=dic)

    def __init__(self, from_file=True, *, from_dict=False):
        self.__cp = ConfigParser()

        if from_dict:
            self.__cp.read_dict(from_dict)
            self.__from_dict = True
            self.__dict_data = deepcopy(from_dict)
        else:
            self.__from_dict = False
            self._file_path = abspath(join(expanduser('~'), 'ocr_app.cfg'))
            if not exists(self._file_path):
                self.__cp.read_dict(DEFAULT_SETTINGS)
                with open(self._file_path, 'w') as file:
                    self.__cp.write(file)
            else:
                self.__cp.read(self._file_path)

    def to_dict(self) -> dict:
        dic = {}
        for key, section in self.__cp.items():
            if key != 'DEFAULT':
                dic[key] = dict(section)
        return dic

    def options(self):
        return self.__cp.sections()

    def reload(self):
        self.__cp.clear()
        if not self.__from_dict:
            self.__cp.read(self._file_path)
        else:
            self.__cp.read_dict(self.__dict_data)

    def get(self, section: str, key: str) -> str:
        return self.__cp.get(section, key)

    def set(self, section, key, v):
        self.__cp.set(section, key, v)

    def flush(self) -> bool:
        dic = self.to_dict()
        return self.save(dic)

    def save(self, dic) -> bool:
        if not self.__from_dict:
            with open(self.file_path, 'w') as file:
                self.__cp.clear()
                self.__cp.read_dict(dic)
                self.__cp.write(file)
            return True
        return False


DEFAULT_CONFIG = Config.fromDict(DEFAULT_SETTINGS)


class User():
    @classmethod
    def fromDict(self, dic):
        id = dic['id']
        key = dic['key']
        secret = dic['secret']
        platform = dic['platform']
        alias = dic['alias']
        legal = dic['legal']
        config = dic['config']
        return User(id, key, secret, platform, alias, legal, config)

    def __init__(self,
                 id,
                 key,
                 secret,
                 platform='b',
                 alias='user1', 
                 legal=False,
                 config: Config = DEFAULT_CONFIG):
        self.id = id
        self.key = key
        self.secret = secret
        self.platform = platform
        self.config = config
        self.__legal = legal

    @property
    def legal(self) -> bool:
        if self.platform == 'b':
            if self.__legal == False:
                from aip import AipOcr
                img = open('./checkUser.png').read()
                client = AipOcr(self.id, self.key, self.secret)
                res = client.basicGeneral(img)
                if res.get('error_code', None) == 14:
                    self.__legal = False
                else:
                    self.__legal = True
                return self.__legal

    def set_config(self, config: Config):
        self.config = config

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'key': self.key,
            'secret': self.secret,
            'platform': self.platform,
            'config': self.config.to_dict()
        }

    def __repr__(self):
        return f'User<id:{self.id},key:{self.key},secret:{self.secret},plat:{self.platform}>'


class Account():
    def __init__(self):
        self.file_path = abspath(join(expanduser('~'), 'ocr_user.json'))
        if not exists(self.file_path):
            with open(self.file_path, 'w+', encoding='utf8') as file:
                json.dump(ACCOUNT_SETTINGS,
                          file,
                          ensure_ascii=False,
                          indent='  ')

        self.info = json.load(open(self.file_path, 'r', encoding='utf8'))
        self._user_length = len(self.info.keys()) - 1

    def add_user(self, user: User):
        self._user_length += 1
        self.info.update({f'user{self._user_length}': user.to_dict()})

    def save(self):
        with open(self.file_path, 'w+', encoding='utf8') as file:
            json.dump(self.info, file)

    def users(self) -> List[User]:
        lis = []
        for key, value in self.info:
            if key != 'info':
                lis.append(User.fromDict(value))
        return lis

    def active_user(self) -> User:
        active = self.info.get(self.info['info']['active'])
        return User.fromDict(active)

    def set_active_user(self, alias):
        self.info['info']['active'] = alias


