from threading import Lock

permissionLock = Lock()
permissionStorage = {}


# def fetchPermission(authHash):
#     # this is a mocked permissions structure, it should connect to the datasource and fetch the permissions
#     # TODO integration with SSO
# 
#     if authHash == "A":
#         return [
#             [
#                 {"key": "_type", "val": "PKI", "type": "string", "op": "eq"},
#                 {"key": "Country", "val": "PL", "type": "string", "op": "eq"}
#             ]
#         ]
#     if authHash == "B":
#         return [
#             [
#                 {"key": "_type", "val": "PKI", "type": "string", "op": "eq"},
#                 {"key": "Country", "val": "DE", "type": "string", "op": "eq"}
#             ]
#         ]
# 
#     # if there is no information about the permissions of the user, allow everything
#     permissions = [[{"key": "_type", "val": "*", "type": "string", "op": "eq"}]]
#     return permissions

def addPermissions(authHash, permissions):
    with permissionLock:
        permissionStorage[authHash] = permissions

def fetchPermissions(authHash):
   raise Exception('No permission found for ' + authHash)

def getPermissions(authHash):
    if authHash not in permissionStorage:
        permissions = fetchPermission(authHash)
        permissionStorage[authHash] = permissions
    else:
        permissions = permissionStorage[authHash]

    return permissions
