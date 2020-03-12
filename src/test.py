from supports import Account, User, Config
dic = {'id': '17223708', 'key': 'U50TQUrUMMb1NdRcwuX8844f', 'secret': 'ZNSQzaRIVKZsgSxVppsFeIjoNo40hlCB', 'alias': 'user2', 'platform': 'b', 'legal': True, 'config': {'recognition': {'delay': '2', 'number': 2, 'type': 0}, 'out': {'format': 'txt', 'directory': 'C:\\Users\\fqk12\\Desktop', 'title': 'none'}, 'advanced': {'region': 'none', 'text1': 'none', 'clean': 'false'}, 'parseinfo': {'workpath': '', 'basic': 0, 'handwriting': 0, 'accurate': 0}}}
account = Account()
print(account.info)
print(account.users())

# dic = {
#     'id': '17223708',
#     'alias': 'user3',
#     'config': {
#         'recognition': {
#             'delay': '2',
#             'number': 2,
#             'type': 0
#         }
#     }
# }

# dic2 = {
#     'id': '111',
#     'alias': 'user3',
#     'config': {
#         'recognition': {
#             'delay': '2',
#             'number': 20000,
#             'type': -1
#         }
#     }
# }

# dic.update(dic2)
# print(dic)
