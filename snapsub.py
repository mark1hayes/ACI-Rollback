import requests
import json
import sys
import collections


'''
Notes:

ACI Snapshot Script
Mark Hayes

'''

# Class must be instantiated with APIC IP address, username, and password
# the login method returns the APIC cookies.
class FabLogin(object):
    def __init__(self, apic, user, pword):
        self.apic = apic
        self.user = user
        self.pword = pword

    def login(self):
        # Load login json payload
        payload = '''
        {{
            "aaaUser": {{
                "attributes": {{
                    "name": "{user}",
                    "pwd": "{pword}"
                }}
            }}
        }}
        '''.format(user=self.user, pword=self.pword)
        payload = json.loads(payload,
                             object_pairs_hook=collections.OrderedDict)
        s = requests.Session()
        # Try the request, if exception, exit program w/ error
        try:
            # Verify is disabled as there are issues if it is enabled
            r = s.post('https://{}/api/mo/aaaLogin.json'.format(self.apic),
                       data=json.dumps(payload), verify=False)
            # Capture HTTP status code from the request
            status = r.status_code
            # Capture the APIC cookie for all other future calls
            cookies = r.cookies
            # Log login status/time(?) somewhere
            if status == 400:
                print("Error 400 - Bad Request - ABORT!")
                print("Probably have a bad URL")
                sys.exit()
            if status == 401:
                print("Error 401 - Unauthorized - ABORT!")
                print("Probably have incorrect credentials")
                sys.exit()
            if status == 403:
                print("Error 403 - Forbidden - ABORT!")
                print("Server refuses to handle your request")
                sys.exit()
            if status == 404:
                print("Error 404 - Not Found - ABORT!")
                print("Seems like you're trying to POST to a page that doesn't"
                      " exist.")
                sys.exit()
        except Exception as e:
            print("Something went wrong logging into the APIC - ABORT!")
            # Log exit reason somewhere
            sys.exit(e)
        return cookies

# Class must be instantiated with APIC IP address and cookies
class Query(object):
    def __init__(self, apic, cookies):
        self.apic = apic
        self.cookies = cookies

    # Method must be called with the following data.
    # dn: DN of object you would like to query
    # Returns status code and json payload of query
    def query_dn(self, dn):
        s = requests.Session()
        try:
            r = s.get('https://{}/api/node/mo/{}.json'.format(self.apic, dn),
                      cookies=self.cookies, verify=False)
            status = r.status_code
            payload = json.loads(r.text)
        except Exception as e:
            print("Failed to query DN. Exception: {}".format(e))
            status = 666
        return (status, payload)

    def query_class(self, query_class):
        s = requests.Session()
        try:
            r = s.get('https://{}/api/node/class/{}.json'.format(self.apic,
                      query_class), cookies=self.cookies, verify=False)
            status = r.status_code
            payload = json.loads(r.text)
        except Exception as e:
            print("Failed to query Class. Exception: {}".format(e))
            status = 666
        return (status, payload)


# Class must be instantiated with APIC IP address and cookies
class FabCfgMgmt(object):
    def __init__(self, apic, cookies):
        self.apic = apic
        self.cookies = cookies

    # Method must be called with the following data. Note only supports
    # SCP at this time (could easily add SFTP or FTP if needed though)
    # name = name of the remote location
    # ip = IP of the remote location (note, module does no validation)
    # path = Path on the remote location
    # user = username for remote location
    # pword = password (sent in clear text) for the remote location
    # status = created | created,modified | deleted
    def remote_path(self, name, ip, path, user, pword, status):
        payload = '''
        {{
        "fileRemotePath": {{
            "attributes": {{
                "descr": "",
                "dn": "uni/fabric/path-{name}",
                "host": "{ip}",
                "name": "{name}",
                "protocol": "scp",
                "remotePath": "{path}",
                "remotePort": "22",
                "userName": "ACI",
                "userPasswd": "{pword}",
                "status": "{status}"
            }},
                "children": [
                    {{
                    "fileRsARemoteHostToEpg": {{
                        "attributes": {{
                            "tDn": "uni/tn-mgmt/mgmtp-default/oob-default"
                            }}
                        }}
                    }}
                ]
            }}
        }}
        '''.format(name=name, ip=ip, path=path, user=user, pword=pword,
                   status=status)
        payload = json.loads(payload,
                             object_pairs_hook=collections.OrderedDict)
        s = requests.Session()
        try:
            r = s.post('https://{}/api/node/mo/uni/fabric/path-{}.json'
                       .format(self.apic, name), data=json.dumps(payload),
                       cookies=self.cookies, verify=False)
            status = r.status_code
        except Exception as e:
            print("Failed to create remote location. Exception: {}".format(e))
            status = 666
        return status

    # Method must be called with the following data.
    # name = name of the snapshot itself
    # snapshot = true | false - if true it creates an export policy and
    # takes a snapshot, if false it simply creates an export policy
    # status = created | created,modified | deleted
    # path = (Optional) remote path for export (can be left blank for snapshot)
    def backup(self, name, snapshot, status, path=''):
        payload = '''
        {{
            "configExportP": {{
                "attributes": {{
                    "dn": "uni/fabric/configexp-{name}",
                    "name": "{name}",
                    "format": "json",
                    "snapshot": "{snapshot}",
                    "targetDn": "",
                    "adminSt": "triggered",
                    "status": "{status}"
                }},
                "children": [
                    {{
                        "configRsRemotePath": {{
                            "attributes": {{
                                "tnFileRemotePathName": "{path}"
                            }}
                        }}
                    }}
                ]
            }}
        }}
        '''.format(name=name, snapshot=snapshot, path=path, status=status)
        payload = json.loads(payload,
                             object_pairs_hook=collections.OrderedDict)
        s = requests.Session()
        try:
            r = s.post('https://{}/api/node/mo/uni/fabric/configexp-{}.jso'
                       'n'.format(self.apic, name),
                       data=json.dumps(payload), cookies=self.cookies,
                       verify=False)
            status = r.status_code
        except Exception as e:
            print("Failed to take snapshot. Exception: {}".format(e))
            status = 666
        return status

    # Method must be called with the following data.
    # name = name of the import object itself
    # filename = name of the file to import
    # path = name of the remote path object where the file lives
    def replace(self, name, filename, path):
        payload = '''
        {{
          "configImportP": {{
            "attributes": {{
              "dn": "uni/fabric/configimp-{name}",
              "name": "{name}",
              "fileName": "{filename}",
              "importType": "replace",
              "rn": "configimp-test",
              "adminSt": "triggered",
              "status": "created"
            }},
            "children": [
            {{
              "configRsRemotePath": {{
                "attributes": {{
                  "tnFileRemotePathName": "{path}",
                  "status": "created,modified"
                }},
                "children": []
                }}
              }}
            ]
          }}
        }}
        '''.format(name=name, filename=filename, path=path)
        payload = json.loads(payload,
                             object_pairs_hook=collections.OrderedDict)
        s = requests.Session()
        try:
            r = s.post('https://{}/api/node/mo/uni/fabric/configimp-{}.json'
                       .format(self.apic, name), data=json.dumps(payload),
                       cookies=self.cookies, verify=False)
            status = r.status_code
        except Exception as e:
            print("Failed to import and replace config. Exception: {}"
                  .format(e))
            status = 666
        return status

    # Method must be called with the following data.
    # name = name of the snapshot itself (note you need to put the file
    # extension in yourself)
    def snapback(self, name):
        payload = '''
        {{
            "configImportP": {{
                "attributes": {{
                    "dn": "uni/fabric/configimp-default",
                    "name": "default",
                    "snapshot": "true",
                    "adminSt": "triggered",
                    "fileName": "{name}",
                    "importType": "replace",
                    "importMode": "atomic",
                    "rn": "configimp-default",
                    "status": "created,modified"
                }}
            }}
        }}
        '''.format(name=name)
        payload = json.loads(payload,
                             object_pairs_hook=collections.OrderedDict)
        s = requests.Session()
        try:
            r = s.post('https://{}/api/node/mo/uni/fabric/configimp-default.js'
                       'on'.format(self.apic),
                       data=json.dumps(payload), cookies=self.cookies,
                       verify=False)
            status = r.status_code
        except Exception as e:
            print("Failed to snapback. Exception: {}".format(e))
            status = 666
        return status
